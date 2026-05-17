from __future__ import annotations

from runtime_context import *
from services.task_service import *

async def ensure_background_workers_started(client):
    global TASK_WORKERS_STARTED, TASK_WORKER_LOCK, STORAGE_MAINTENANCE_TASK
    if TASK_WORKERS_STARTED:
        return

    if TASK_WORKER_LOCK is None:
        TASK_WORKER_LOCK = asyncio.Lock()

    async with TASK_WORKER_LOCK:
        if TASK_WORKERS_STARTED:
            return

        worker_count = max(1, min(int(getattr(cfg, "MAX_CONCURRENT_DOWNLOADS", 2) or 2), 4))
        for idx in range(worker_count):
            worker = asyncio.create_task(task_worker(client, idx + 1))
            TASK_WORKERS.append(worker)
        if bool(getattr(cfg, "ENABLE_STORAGE_MAINTENANCE", True)) and STORAGE_MAINTENANCE_TASK is None:
            STORAGE_MAINTENANCE_TASK = asyncio.create_task(storage_maintenance_worker())
        TASK_WORKERS_STARTED = True
        print(f"ðŸ§µ Task workers started: {worker_count}")


async def storage_maintenance_worker():
    interval = max(60.0, float(getattr(cfg, "STORAGE_MAINTENANCE_INTERVAL_SECONDS", 900) or 900))
    while True:
        try:
            cleanup_info = cleanup_runtime_artifacts()
            if any(cleanup_info.values()):
                debug_log(f"Storage maintenance: {cleanup_info}")
        except Exception as exc:
            debug_log(f"Storage maintenance failed: {exc}")
        await asyncio.sleep(interval)


async def task_worker(client, worker_id: int):
    print(f"ðŸ§µ Worker-{worker_id} online")
    while True:
        item = await TASK_QUEUE.get()
        task_id = item["task_id"]
        try:
            task = get_task(task_id) or {}
            if task.get("status") == "cancelled":
                debug_log(f"Worker-{worker_id} skipping cancelled task {task_id}")
                continue

            touch_task(task_id, {
                "status": "processing",
                "current_stage": "processing",
                "progress_text": "",
                "queue_position": 0,
                "worker_id": worker_id,
                "is_visible": False,
            })
            await update_task_status_message(client, task_id, done=False)
            await _run_task_attempts(client, item)
        except Exception as e:
            touch_task(task_id, {"status": "failed", "current_stage": "failed", "error": f"Worker crash: {e}", "is_visible": True})
            await update_task_status_message(client, task_id, done=True)
            debug_log(f"Worker-{worker_id} crashed on {task_id}: {e}")
        finally:
            TASK_QUEUE.task_done()


async def _run_task_attempts(client, item: dict):
    user_id = item["user_id"]
    message = item["message"]
    link_text = item["link_text"]
    task_id = item["task_id"]
    settings = item["settings"]
    destination = item["destination"]

    for attempt in range(MAX_RETRY_ATTEMPTS + 1):
        try:
            ensure_task_not_cancelled(task_id)
            if attempt > 0:
                touch_task(task_id, {
                    "retry_count": attempt,
                    "status": "processing",
                    "progress_text": f"Retry {attempt}/{MAX_RETRY_ATTEMPTS}...",
                })
                await update_task_status_message(client, task_id)

            source_message = item.get("source_message")
            if source_message is not None:
                await process_source_message_transfer(
                    client,
                    user_id,
                    message,
                    source_message,
                    task_id,
                    settings,
                    destination,
                    f"direct:{getattr(source_message, 'id', 0)}",
                    info={"link_type": "direct_message"},
                    user_client=None,
                    fetch_mode="bot",
                    disconnect_user_client=False,
                )
            else:
                await _perform_transfer(client, user_id, message, link_text, task_id, settings, destination)
            return True

        except FloodWait as e:
            touch_task(task_id, {"status": "failed", "current_stage": "failed", "error": f"FloodWait: wait {e.value}s", "is_visible": True})
            await update_task_status_message(client, task_id, done=True)
            if str((get_task(task_id) or {}).get("mode", "")).strip().lower() != "batch":
                await message.reply_text(f"âŒ FloodWait: {e.value}s wait karo.")
            return False

        except Exception as e:
            error_text = str(e or "")
            lowered_error = error_text.lower()

            if "task cancelled by user" in lowered_error or "cancelled by user" in lowered_error:
                touch_task(task_id, {"status": "cancelled", "current_stage": "cancelled", "error": "Cancelled by user", "is_visible": True})
                await update_task_status_message(client, task_id, done=True)
                return False

            retryable_tokens = (
                "timeout",
                "timed out",
                "network",
                "connection reset",
                "server disconnected",
                "temporarily unavailable",
                "internal server error",
            )
            should_retry = (
                AUTO_RETRY_FAILED_TASKS
                and attempt < MAX_RETRY_ATTEMPTS
                and any(token in lowered_error for token in retryable_tokens)
            )
            if should_retry:
                await asyncio.sleep(RETRY_DELAY_SECONDS)
                continue

            touch_task(task_id, {"status": "failed", "current_stage": "failed", "error": error_text, "is_visible": True})
            await update_task_status_message(client, task_id, done=True)
            if str((get_task(task_id) or {}).get("mode", "")).strip().lower() != "batch":
                await message.reply_text(f"âŒ Task failed:\n{e}")
            return False

    return False


async def hide_task_card_later(client, task_id: str, delay: int = TASK_CARD_HIDE_DELAY):
    if delay <= 0:
        return
    await asyncio.sleep(delay)
    task = get_task(task_id) or {}
    if task.get("status") not in {"completed", "failed", "cancelled"}:
        return
    chat_id = task.get("status_chat_id")
    message_id = task.get("status_message_id")
    if not chat_id or not message_id:
        return
    try:
        await client.delete_messages(chat_id, message_id)
    except Exception as e:
        debug_log(f"Failed to update task card {task_id}: {e}")


async def update_task_status_message(client, task_id: str, done: bool = False):
    task = get_task(task_id)
    if not task:
        return
    if str(task.get("mode", "")).strip().lower() == "batch":
        await _sync_batch_board_from_task(client, task)
        return

    if not done and not should_show_processing_card(task):
        await update_checking_message(client, task_id)
        return

    visible = await ensure_task_card_visible(client, task_id)
    if not visible:
        return

    task = get_task(task_id) or {}
    chat_id = task.get("status_chat_id")
    message_id = task.get("status_message_id")
    if not chat_id or not message_id:
        return

    try:
        if done and task.get("status") == "completed":
            text = task_completed_text(task)
        elif done and task.get("status") in {"failed", "cancelled"}:
            text = task_failed_text(task)
        else:
            text = task_running_text(task)

        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=task_buttons(task_id, done=done, status=task.get('status', '')),
            disable_web_page_preview=True,
        )

        if done and task.get("status") in {"completed", "failed", "cancelled"}:
            asyncio.create_task(hide_task_card_later(client, task_id))
    except Exception as e:
        debug_log(f"Failed to update task card {task_id}: {e}")


async def create_task_status_message(message, task_id: str, checking_message=None):
    task = get_task(task_id)
    if not task:
        return

    sent = checking_message
    reply_markup = task_buttons(task_id, done=False, status=task.get("status", ""))

    if sent:
        try:
            await sent.edit_text(
                task_running_text(task),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception:
            pass
    else:
        try:
            sent = await message.reply_text(
                task_running_text(task),
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        except Exception:
            return

    touch_task(task_id, {
        "status_chat_id": sent.chat.id,
        "status_message_id": sent.id,
        "checking_chat_id": 0,
        "checking_message_id": 0,
        "pinned_ui": True,
        "is_visible": True,
    })


async def throttled_progress_update(client, task_id: str):
    task = get_task(task_id)
    if not task:
        return

    now = time.time()
    last = float(task.get("last_ui_update", 0) or 0)
    if now - last < PROGRESS_UPDATE_INTERVAL:
        return

    touch_task(task_id, {"last_ui_update": now})
    await update_task_status_message(client, task_id, done=False)


async def progress_callback(current, total, client, task_id: str, stage: str):
    ensure_task_not_cancelled(task_id)

    task = get_task(task_id) or {}
    now = time.time()
    started_key = f"{stage}_started_at"

    if not task.get(started_key):
        touch_task(task_id, {started_key: now})
        task = get_task(task_id) or {}

    started_at = float(task.get(started_key, now) or now)
    elapsed = max(now - started_at, 0.001)
    percent = round((current / total) * 100, 2) if total else 0.0
    speed = current / elapsed if elapsed > 0 else 0.0
    remaining = max((total - current), 0) if total else 0
    eta = (remaining / speed) if speed > 0 and total else 0.0
    bar = progress_bar(percent, PROGRESS_BAR_LENGTH)

    compact_parts = []
    if SHOW_TRANSFERRED_SIZE and total:
        compact_parts.append(f"{human_bytes(current)} / {human_bytes(total)}")
    if SHOW_REALTIME_SPEED and speed > 0:
        compact_parts.append(f"{human_speed(speed)}")
    if SHOW_REALTIME_ETA and total and speed > 0:
        compact_parts.append(f"ETA {human_eta(eta)}")

    touch_task(task_id, {
        "status": stage,
        "current_stage": stage,
        "current_bytes": int(current or 0),
        "total_bytes": int(total or 0),
        "progress": percent,
        "progress_percent": percent,
        "progress_bar_text": bar,
        "speed_bps": float(speed or 0.0),
        "eta_seconds": float(eta or 0.0),
        "elapsed_seconds": float(elapsed or 0.0),
        "progress_text": " â€¢ ".join(compact_parts),
        "is_visible": True,
    })
    await throttled_progress_update(client, task_id)

