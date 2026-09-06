from __future__ import annotations

import threading
import time
import traceback
import sys
import socket
import atexit
import signal
import os
import config as cfg

try:
    import uvloop
    uvloop.install()
except Exception:
    pass

from pyrogram import idle

from app import run_web, set_runtime_state
from bot import app, ensure_background_workers_started
from storage import initialize_storage, sync_local_persistent_data_to_supabase, flush_all_storage_caches


BOT_STARTUP_MODE = "web+bot"
_INSTANCE_LOCK_SOCKET = None


def _configure_console_streams():
    for stream_name in ("stdout", "stderr"):
        stream = getattr(sys, stream_name, None)
        if stream is None:
            continue
        reconfigure = getattr(stream, "reconfigure", None)
        if callable(reconfigure):
            try:
                reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
            except Exception:
                pass


def _release_single_instance_lock():
    global _INSTANCE_LOCK_SOCKET
    if _INSTANCE_LOCK_SOCKET is None:
        return
    try:
        _INSTANCE_LOCK_SOCKET.close()
    except Exception:
        pass
    _INSTANCE_LOCK_SOCKET = None


def _acquire_single_instance_lock():
    global _INSTANCE_LOCK_SOCKET
    if _INSTANCE_LOCK_SOCKET is not None:
        return

    port = int(os.environ.get("SINGLE_INSTANCE_LOCK_PORT", "47291") or 47291)
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.bind(("127.0.0.1", port))
        sock.listen(1)
    except OSError as exc:
        try:
            sock.close()
        except Exception:
            pass
        raise RuntimeError(
            f"Another Code Devil instance is already running on this machine (lock port {port}). "
            "Old local process ko stop karo, phir bot restart karo."
        ) from exc

    _INSTANCE_LOCK_SOCKET = sock
    atexit.register(_release_single_instance_lock)


def _handle_shutdown_signal(signum, frame):
    print(f"[app] Received signal {signum}, flushing storage caches...")
    try:
        flush_all_storage_caches()
    except Exception:
        pass
    _release_single_instance_lock()
    sys.exit(0)


for _sig in (getattr(signal, "SIGTERM", None), getattr(signal, "SIGINT", None)):
    if _sig is not None:
        try:
            signal.signal(_sig, _handle_shutdown_signal)
        except Exception:
            pass


def start_bot():
    print("[bot] Starting Code Devil Bot")
    set_runtime_state(False, username="unknown", mode=BOT_STARTUP_MODE)

    try:
        initialize_storage()
        app.start()
        time.sleep(0.1)
        app.loop.create_task(
            ensure_background_workers_started(app)
        )
        try:
            sync_info = {"enabled": False, "synced": [], "details": {}}
            if bool(getattr(cfg, "SYNC_LOCAL_TO_SUPABASE", False)):
                sync_info = sync_local_persistent_data_to_supabase(force=True, prune_missing=False) or sync_info
            if sync_info.get("enabled"):
                details = sync_info.get("details") if isinstance(sync_info.get("details"), dict) else {}
                summary_bits = []
                for label in sync_info.get("synced") or []:
                    row = details.get(label, {}) if isinstance(details.get(label), dict) else {}
                    summary_bits.append(f"{label}={int(row.get('synced', 0) or 0)}")
                print(f"[supabase] Startup sync: {', '.join(summary_bits) or 'no local maps'}")
                errors = sync_info.get("errors") or []
                if errors:
                    print(f"[supabase] Startup sync errors: {' | '.join(errors[:5])}")
            else:
                print("[supabase] Startup sync disabled (set SYNC_LOCAL_TO_SUPABASE=true to enable)")
        except Exception as sync_exc:
            print(f"[supabase] Startup sync skipped: {sync_exc}")

        time.sleep(0.05)
        me = app.get_me()
        username = me.username if me else "unknown"

        print(f"[bot] Started as @{username}")
        set_runtime_state(True, username=username, mode=BOT_STARTUP_MODE)

        app.loop.run_until_complete(idle())
    except KeyboardInterrupt:
        print("[bot] Shutdown requested by keyboard interrupt.")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print("[bot] Startup/runtime error:")
        traceback.print_exc()
        set_runtime_state(False, error=err, mode=BOT_STARTUP_MODE)
        raise
    finally:
        try:
            flush_all_storage_caches()
            print("[storage] All storage caches safely flushed to disk.")
        except Exception:
            pass
        try:
            app.stop()
            print("[bot] Stopped.")
        except Exception:
            pass
        set_runtime_state(False, mode=BOT_STARTUP_MODE)


def start_web():
    try:
        run_web()
    except Exception:
        print("[web] Failed to start:")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    _configure_console_streams()
    _acquire_single_instance_lock()
    print("[app] Starting Optimized Code Devil Restricted Saver")

    web_thread = threading.Thread(target=start_web, daemon=True, name="render-web-server")
    web_thread.start()

    time.sleep(0.05)
    start_bot()
