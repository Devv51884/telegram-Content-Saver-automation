from __future__ import annotations

import threading
import time
import traceback

from pyrogram import idle

from app import run_web, set_runtime_state
from bot import app, ensure_background_workers_started
from storage import initialize_storage, sync_local_persistent_data_to_supabase


BOT_STARTUP_MODE = "web+bot"


def start_bot():
    print("🤖 Starting Code Devil Bot  ")
    set_runtime_state(False, username="unknown", mode=BOT_STARTUP_MODE)

    try:
        initialize_storage()
        app.start()
        app.loop.run_until_complete(ensure_background_workers_started(app))
        try:
            sync_info = sync_local_persistent_data_to_supabase()
            if sync_info.get("enabled"):
                synced = ", ".join(sync_info.get("synced") or [])
                print(f"☁️ Startup Supabase sync: {synced or 'no local maps'}")
        except Exception as sync_exc:
            print(f"⚠️ Startup Supabase sync skipped: {sync_exc}")

        me = app.get_me()
        username = me.username if me else "unknown"

        print(f"✅ Bot Started as @{username}")
        set_runtime_state(True, username=username, mode=BOT_STARTUP_MODE)

        idle()
    except KeyboardInterrupt:
        print("⏹ Bot shutdown requested by keyboard interrupt.")
    except Exception as exc:
        err = f"{type(exc).__name__}: {exc}"
        print("❌ Bot startup/runtime error:")
        traceback.print_exc()
        set_runtime_state(False, error=err, mode=BOT_STARTUP_MODE)
        raise
    finally:
        try:
            app.stop()
            print("🛑 Bot stopped.")
        except Exception:
            pass
        set_runtime_state(False, mode=BOT_STARTUP_MODE)


def start_web():
    try:
        run_web()
    except Exception:
        print("❌ Web server failed to start:")
        traceback.print_exc()
        raise


if __name__ == "__main__":
    print("🚀 Starting Code Devil Restricted Saver ")

    web_thread = threading.Thread(target=start_web, daemon=True, name="web-server")
    web_thread.start()

    time.sleep(0.8)
    start_bot()
