from __future__ import annotations

from runtime_context import *
from services.storage_service import *
from services.task_service import *
from services.worker_service import *
from services.link_service import *

__all__ = [
    "process_link_task_impl",
    "process_link_task",
    "enqueue_direct_message_task_impl",
    "enqueue_direct_message_task",
]


def _build_task_payload(
    task_id: str,
    user_id: int,
    source: str,
    destination,
    settings: dict,
    storage_mode: str,
    queue_position: int,
    *,
    mode: str,
    pinned_ui: bool,
    batch_key: str = "",
    batch_index: int = 0,
    batch_total: int = 0,
):
    return {
        "task_id": task_id,
        "user_id": user_id,
        "source": source,
        "destination": str(destination or ""),
        "user_destination": str(destination or ""),
        "status": "checking",
        "current_stage": "checking",
        "progress": 0.0,
        "progress_percent": 0.0,
        "progress_text": "",
        "error": "",
        "retry_count": 0,
        "created_at": now_iso(),
        "mode": mode,
        "upload_mode": settings.get("telegram_upload_mode", settings.get("upload_mode", "media")),
        "storage_mode": storage_mode,
        "topic_id": str(settings.get("topic_id", "") or ""),
        "queue_position": queue_position,
        "status_chat_id": 0,
        "status_message_id": 0,
        "checking_chat_id": 0,
        "checking_message_id": 0,
        "pinned_ui": pinned_ui,
        "is_visible": False,
        "batch_key": str(batch_key or ""),
        "batch_index": int(batch_index or 0),
        "batch_total": int(batch_total or 0),
    }


async def process_link_task_impl(client, user_id: int, message, link_text: str, batch_mode: bool = False, batch_key: str = "", batch_index: int = 0, batch_total: int = 0):
    info = extract_telegram_link_info(link_text)
    settings = get_user_settings(user_id)
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    destination = get_configured_storage_destination(settings)

    if not destination:
        if batch_mode:
            return False
        await ask_set_destination(message, settings=settings)
        return False

    try:
        ensure_storage_runtime_ready(settings, ensure_shared_user_site_packages)
    except Exception as exc:
        if batch_mode:
            return False
        await edit_or_reply(message, f"Ã¢ÂÅ’ {exc}")
        return False

    if info and str(info.get("link_type") or "").lower() in {"private", "private_topic"} and not has_user_session(user_id):
        if batch_mode:
            return False
        await ask_login_for_private_link(message)
        return False

    cleanup_stale_active_tasks()
    user_task_limit = get_user_task_limit(user_id)
    running_now = count_running_tasks(user_id)
    queue_now = TASK_QUEUE.qsize()

    if running_now >= user_task_limit:
        if batch_mode:
            return False
        warn = f"Ã¢Å¡Â Ã¯Â¸Â Ek time par max {user_task_limit} running tasks allowed hain."
        await edit_or_reply(message, warn)
        return False

    if (running_now + queue_now) >= GLOBAL_MAX_RUNNING_TASKS:
        if batch_mode:
            return False
        warn = "Ã¢Å¡Â Ã¯Â¸Â Queue full hai. Thodi der baad try karo."
        await edit_or_reply(message, warn)
        return False

    task_id = make_task_id()
    queue_position = TASK_QUEUE.qsize() + 1
    payload = _build_task_payload(
        task_id=task_id,
        user_id=user_id,
        source=link_text.strip(),
        destination=destination,
        settings=settings,
        storage_mode=storage_mode,
        queue_position=queue_position,
        mode="batch" if batch_mode else "single",
        pinned_ui=not batch_mode,
        batch_key=batch_key,
        batch_index=batch_index,
        batch_total=batch_total,
    )
    touch_task(task_id, payload)

    if batch_mode:
        _register_task_to_batch_board(user_id, task_id, batch_key, batch_index, batch_total, link_text.strip())
        await _refresh_batch_board_message(client, user_id)
        return task_id

    await create_task_status_message(message, task_id)
    try:
        await ensure_background_workers_started(client)
    except Exception as exc:
        touch_task(task_id, {
            "status": "failed",
            "current_stage": "failed",
            "error": f"Worker startup failed: {exc}",
            "is_visible": True,
        })
        await update_task_status_message(client, task_id, done=True)
        return False

    await TASK_QUEUE.put({
        "task_id": task_id,
        "user_id": user_id,
        "message": message,
        "link_text": link_text,
        "settings": settings,
        "destination": destination,
        "batch_mode": batch_mode,
    })
    debug_log(f"Queued task {task_id} for user {user_id}")
    return task_id


async def process_link_task(client, user_id: int, message, link_text: str, batch_mode: bool = False, batch_key: str = "", batch_index: int = 0, batch_total: int = 0):
    return await process_link_task_impl(
        client,
        user_id,
        message,
        link_text,
        batch_mode=batch_mode,
        batch_key=batch_key,
        batch_index=batch_index,
        batch_total=batch_total,
    )


async def enqueue_direct_message_task_impl(client, user_id: int, message):
    active_state = get_user_state(user_id)
    if active_state == "set_thumbnail_photo":
        if getattr(message, "photo", None):
            update_user_settings(user_id, {"thumbnail_file_id": message.photo.file_id, "thumbnail_enabled": True})
            clear_user_state(user_id)
            await message.reply_text("Ã¢Å“â€¦ Custom thumbnail save ho gaya.\n\n/settings bhejo dekhne ke liye.")
            return False
        await message.reply_text("Ã¢ÂÅ’ Thumbnail ke liye photo bhejna zaroori hai. /cancel bhej kar cancel kar sakte ho.")
        return False

    settings = get_user_settings(user_id)
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    destination = get_configured_storage_destination(settings)

    if not destination:
        await ask_set_destination(message, settings=settings)
        return False

    try:
        ensure_storage_runtime_ready(settings, ensure_shared_user_site_packages)
    except Exception as exc:
        await message.reply_text(f"Ã¢ÂÅ’ {exc}")
        return False

    cleanup_stale_active_tasks()
    user_task_limit = get_user_task_limit(user_id)
    running_now = count_running_tasks(user_id)
    queue_now = TASK_QUEUE.qsize()

    if running_now >= user_task_limit:
        await message.reply_text(f"Ã¢Å¡Â Ã¯Â¸Â Ek time par max {user_task_limit} running tasks allowed hain.")
        return False

    if (running_now + queue_now) >= GLOBAL_MAX_RUNNING_TASKS:
        await message.reply_text("Ã¢Å¡Â Ã¯Â¸Â Queue full hai. Thodi der baad try karo.")
        return False

    task_id = make_task_id()
    queue_position = TASK_QUEUE.qsize() + 1
    source_label = f"direct:{message.id}"
    payload = _build_task_payload(
        task_id=task_id,
        user_id=user_id,
        source=source_label,
        destination=destination,
        settings=settings,
        storage_mode=storage_mode,
        queue_position=queue_position,
        mode="single",
        pinned_ui=True,
    )
    touch_task(task_id, payload)

    await create_task_status_message(message, task_id)
    try:
        await ensure_background_workers_started(client)
    except Exception as exc:
        touch_task(task_id, {
            "status": "failed",
            "current_stage": "failed",
            "error": f"Worker startup failed: {exc}",
            "is_visible": True,
        })
        await update_task_status_message(client, task_id, done=True)
        return False

    await TASK_QUEUE.put({
        "task_id": task_id,
        "user_id": user_id,
        "message": message,
        "link_text": source_label,
        "source_message": message,
        "settings": settings,
        "destination": destination,
        "batch_mode": False,
    })
    debug_log(f"Queued direct message task {task_id} for user {user_id}")
    return task_id


async def enqueue_direct_message_task(client, user_id: int, message):
    return await enqueue_direct_message_task_impl(client, user_id, message)
