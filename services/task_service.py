from __future__ import annotations

from runtime_context import *

def ensure_task_not_cancelled(task_id: str):
    task = get_task(task_id) or {}
    if str(task.get("status", "")).strip().lower() == "cancelled":
        raise RuntimeError("Task cancelled by user")
    user_id = int(task.get("user_id") or 0)
    batch_key = str(task.get("batch_key") or "").strip()
    if user_id and batch_key:
        board = _get_batch_board(user_id)
        if board and board.get("batch_key") == batch_key and bool(board.get("cancel_all_requested")):
            touch_task(task_id, {"status": "cancelled", "current_stage": "cancelled", "error": "Batch cancelled by user", "is_visible": True})
            raise RuntimeError("Task cancelled by user")


def touch_task(task_id: str, payload: dict):
    payload = dict(payload or {})
    payload["updated_at"] = now_iso()
    set_task(task_id, payload)


def build_settings_home_markup(user_id: int):
    marks = get_settings_marks(user_id)
    has_session = has_user_session(user_id)
    settings = get_user_settings(user_id)
    upload_mode = settings.get("telegram_upload_mode", settings.get("upload_mode", "media"))
    storage_mode = settings.get("storage_mode", "telegram")
    return settings_home_buttons(
        marks,
        has_session,
        upload_mode,
        is_admin(user_id),
        is_premium_user(user_id),
        storage_mode,
    )


def build_start_markup(user_id: int):
    return start_buttons(
        has_user_session(user_id),
        is_admin(user_id),
        is_premium_user(user_id),
    )


def build_upload_mode_message(user_id: int):
    return upload_mode_text(user_id)


TELEGRAM_ONLY_SETTINGS_CALLBACKS = {
    "show_upload_mode",
    "show_telegram_upload_mode",
    "toggle_upload_mode",
    "toggle_upload_mode_legacy",
    "show_thumbnail",
    "toggle_thumbnail_enabled",
    "set_thumbnail_photo",
    "remove_thumbnail",
    "show_destination",
    "set_destination",
    "remove_destination",
    "clear_destination",
    "show_topic_id",
    "set_topic_id",
    "remove_topic_id",
    "clear_topic_id",
}
TELEGRAM_ONLY_SETTINGS_PREFIXES = ("set_upload_mode:",)


def is_telegram_only_settings_callback(data: str) -> bool:
    data = str(data or "").strip()
    if data in TELEGRAM_ONLY_SETTINGS_CALLBACKS:
        return True
    return any(data.startswith(prefix) for prefix in TELEGRAM_ONLY_SETTINGS_PREFIXES)


def build_storage_mode_locked_callback_text(storage_mode: str) -> str:
    storage_mode = normalize_storage_mode(storage_mode)
    if storage_mode == "gdrive":
        return "Google Drive mode me ye Telegram-only setting apply nahi hoti. Token, Folder ID, Auto Rename aur Replace Rules use karo."
    if storage_mode == "rclone":
        return "Rclone mode me ye Telegram-only setting apply nahi hoti. Rclone Config, Path, Auto Rename aur Replace Rules use karo."
    return "Ye setting abhi current storage mode me apply nahi hoti."


def _task_stage_label_for_batch(task: dict) -> str:
    stage = str((task or {}).get("current_stage") or (task or {}).get("status") or "checking").strip().lower()
    mapping = {
        "checking": "Checking",
        "queued": "Checking",
        "processing": "Checking",
        "fetching": "Checking",
        "downloading": "Downloading",
        "uploading": "Uploading",
        "copying": "Copying",
        "completed": "Completed",
        "failed": "Failed",
        "cancelled": "Cancelled",
    }
    return mapping.get(stage, stage.title())


def _get_batch_board(user_id: int) -> dict:
    board = get_login_temp(user_id, "batch_board", {})
    return board if isinstance(board, dict) else {}


def _save_batch_board(user_id: int, board: dict):
    set_login_temp(user_id, "batch_board", dict(board or {}))


def _clear_batch_board(user_id: int):
    clear_login_temp(user_id, "batch_board")


def _batch_counts_from_tasks(board: dict):
    tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
    queued = running = completed = failed = 0
    for row in tasks.values():
        status = str((row or {}).get("status") or "").strip().lower()
        if status == "completed":
            completed += 1
        elif status in {"failed", "cancelled"}:
            failed += 1
        elif status in {"downloading", "uploading", "copying"}:
            running += 1
        else:
            queued += 1
    return queued, running, completed, failed


async def _try_pin_message(client, chat_id, message_id):
    try:
        await client.pin_chat_message(chat_id, message_id, disable_notification=True)
        return True
    except Exception:
        return False


async def _try_unpin_message(client, chat_id, message_id):
    try:
        await client.unpin_chat_message(chat_id, message_id)
        return True
    except Exception:
        return False


def _elapsed_for_batch(board: dict) -> str:
    started = float(board.get("started_ts", 0) or 0)
    if not started:
        return ""
    return human_eta(max(0, time.time() - started))


async def _open_batch_board(client, message, user_id: int, total: int, note: str = "", batch_name: str = "Batch Job"):
    batch_key = uuid.uuid4().hex[:10]
    board = {
        "batch_key": batch_key,
        "user_id": user_id,
        "status": "Preparing",
        "total": int(total or 0),
        "queued": 0,
        "running": 0,
        "completed": 0,
        "failed": 0,
        "current_index": 0,
        "current_source": "",
        "current_stage": "",
        "progress_percent": 0.0,
        "progress_bar_text": "",
        "processed_text": "",
        "speed_text": "",
        "eta_text": "",
        "elapsed_text": "",
        "note": str(note or ""),
        "tasks": {},
        "started_ts": time.time(),
        "done": False,
        "chat_id": 0,
        "message_id": 0,
        "pinned": False,
        "current_task_id": "",
        "batch_name": str(batch_name or "Batch Job"),
        "cancel_all_requested": False,
    }
    sent = await message.reply_text(
        batch_live_board_text(board),
        reply_markup=batch_live_board_buttons(batch_key, done=False, current_task_id=str(board.get("current_task_id", "") or ""), status=str(board.get("status") or "")),
        disable_web_page_preview=True,
    )
    board["chat_id"] = sent.chat.id
    board["message_id"] = sent.id
    board["pinned"] = await _try_pin_message(client, sent.chat.id, sent.id)
    _save_batch_board(user_id, board)
    return board


async def _refresh_batch_board_message(client, user_id: int, force_done: bool = False):
    board = _get_batch_board(user_id)
    if not board:
        return
    chat_id = board.get("chat_id")
    message_id = board.get("message_id")
    batch_key = board.get("batch_key", "")
    if not chat_id or not message_id:
        return

    queued, running, completed, failed = _batch_counts_from_tasks(board)
    board["queued"] = queued
    board["running"] = running
    board["completed"] = completed
    board["failed"] = failed
    board["elapsed_text"] = _elapsed_for_batch(board)

    done = force_done or (completed + failed >= int(board.get("total") or 0) and int(board.get("total") or 0) > 0)
    board["done"] = bool(done)
    if done:
        final_status = str(board.get("status") or "Completed").strip() or "Completed"
        if final_status.lower() not in {"completed", "cancelled"}:
            final_status = "Completed"
        board["status"] = final_status
        board["current_stage"] = final_status
        board["current_task_id"] = ""
        if final_status.lower() == "cancelled":
            text = batch_live_board_text(board)
        else:
            text = batch_completed_board_text(board)
        markup = batch_live_board_buttons(batch_key, done=True, current_task_id=str(board.get("current_task_id", "") or ""), status=final_status)
    else:
        text = batch_live_board_text(board)
        markup = batch_live_board_buttons(batch_key, done=False, current_task_id=str(board.get("current_task_id", "") or ""), status=str(board.get("status") or ""))

    try:
        await asyncio.sleep(0)
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=markup,
            disable_web_page_preview=True,
        )
    except Exception:
        pass

    if done and board.get("pinned"):
        await _try_unpin_message(client, chat_id, message_id)
        board["pinned"] = False

    _save_batch_board(user_id, board)


def _register_task_to_batch_board(user_id: int, task_id: str, batch_key: str, batch_index: int, batch_total: int, source: str):
    board = _get_batch_board(user_id)
    if not board or board.get("batch_key") != batch_key:
        return
    tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
    tasks[str(task_id)] = {
        "index": int(batch_index or 0),
        "source": str(source or ""),
        "status": "checking",
    }
    board["tasks"] = tasks
    board["total"] = max(int(board.get("total") or 0), int(batch_total or 0))
    board["current_index"] = int(batch_index or 0)
    board["current_source"] = str(source or "")
    board["current_stage"] = "Checking"
    board["status"] = "Running"
    board["current_task_id"] = str(task_id)
    _save_batch_board(user_id, board)


async def _sync_batch_board_from_task(client, task: dict):
    if not isinstance(task, dict):
        return
    if str(task.get("mode", "")).strip().lower() != "batch":
        return

    user_id = int(task.get("user_id") or 0)
    batch_key = str(task.get("batch_key") or "").strip()
    if not user_id or not batch_key:
        return

    board = _get_batch_board(user_id)
    if not board or board.get("batch_key") != batch_key:
        return

    tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
    task_id = str(task.get("id") or "")
    item = tasks.get(task_id, {})
    item.update({
        "index": int(task.get("batch_index") or item.get("index") or 0),
        "source": str(task.get("source") or item.get("source") or ""),
        "status": str(task.get("status") or "checking").strip().lower(),
    })
    tasks[task_id] = item
    board["tasks"] = tasks
    board["status"] = "Running"
    board["current_index"] = int(item.get("index") or 0)
    board["current_source"] = str(item.get("source") or "")
    board["current_stage"] = _task_stage_label_for_batch(task)
    board["current_task_id"] = task_id
    board["progress_bar_text"] = str(task.get("progress_bar_text") or "")
    board["progress_percent"] = task.get("progress_percent", task.get("progress", 0.0))
    if task.get("total_bytes"):
        board["processed_text"] = f"{human_bytes(task.get('current_bytes', 0))} / {human_bytes(task.get('total_bytes', 0))}"
    elif task.get("current_bytes"):
        board["processed_text"] = human_bytes(task.get("current_bytes", 0))
    else:
        board["processed_text"] = ""
    board["speed_text"] = human_speed(task.get("speed_bps", 0)) if task.get("speed_bps") else ""
    board["eta_text"] = human_eta(task.get("eta_seconds", 0)) if task.get("eta_seconds") else ""
    board["elapsed_text"] = _elapsed_for_batch(board)

    if task.get("status") == "completed":
        board["note"] = f"Last done: item {board['current_index']}"
    elif task.get("status") in {"failed", "cancelled"}:
        board["note"] = f"Last failed: item {board['current_index']}"

    _save_batch_board(user_id, board)
    try:
        await _refresh_batch_board_message(client, user_id)
    except Exception:
        pass


async def _close_batch_board(client, user_id: int):
    board = _get_batch_board(user_id)
    if not board:
        return
    chat_id = board.get("chat_id")
    message_id = board.get("message_id")
    if board.get("pinned") and chat_id and message_id:
        await _try_unpin_message(client, chat_id, message_id)
    try:
        if chat_id and message_id:
            await client.delete_messages(chat_id, message_id)
    except Exception:
        pass
    _clear_batch_board(user_id)


def _cancel_task_record(task_id: str, reason: str = "Cancelled by user") -> bool:
    task = get_task(task_id)
    if not task:
        return False
    status = str(task.get("status") or "").strip().lower()
    if status in {"completed", "failed", "cancelled"}:
        return False
    touch_task(task_id, {"status": "cancelled", "current_stage": "cancelled", "error": reason, "is_visible": True})
    return True


def _cancel_batch_tasks(user_id: int, batch_key: str, only_current: bool = False, return_task_ids: bool = False):
    batch_key = str(batch_key or "").strip()
    if not batch_key:
        return [] if return_task_ids else 0

    board = _get_batch_board(user_id)
    task_ids = []
    if board and board.get("batch_key") == batch_key:
        current_task_id = str(board.get("current_task_id") or "").strip()
        if only_current:
            board["status"] = "Running"
            if current_task_id:
                task_ids.append(current_task_id)
        else:
            board["status"] = "Cancelled"
            board["current_stage"] = "Cancelled"
            board["cancel_all_requested"] = True
            board["note"] = "Batch cancelled by user"
            board["done"] = True
            if current_task_id:
                task_ids.append(current_task_id)
            tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
            task_ids.extend(str(tid) for tid in tasks.keys())
    else:
        for task in get_user_tasks(user_id, limit=2000):
            if str(task.get("batch_key") or "").strip() == batch_key:
                task_ids.append(str(task.get("id") or ""))

    cancelled_ids = []
    seen = set()
    for task_id in task_ids:
        task_id = str(task_id or "").strip()
        if not task_id or task_id in seen:
            continue
        seen.add(task_id)
        if _cancel_task_record(task_id, reason="Batch cancelled by user" if not only_current else "Current task cancelled"):
            cancelled_ids.append(task_id)

    if board and board.get("batch_key") == batch_key:
        tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
        for task_id in cancelled_ids:
            row = dict(tasks.get(task_id) or {})
            row["status"] = "cancelled"
            tasks[task_id] = row
        board["tasks"] = tasks
        if only_current:
            board["current_stage"] = "Cancelled"
            board["current_task_id"] = ""
        else:
            board["cancel_all_requested"] = True
            board["status"] = "Cancelled"
            board["current_stage"] = "Cancelled"
            board["note"] = "Batch cancelled by user"
            board["done"] = True
            board["current_task_id"] = ""
        _save_batch_board(user_id, board)

    return cancelled_ids if return_task_ids else len(cancelled_ids)


def _cancel_active_tasks_for_user(user_id: int, limit: int = 1, return_task_ids: bool = False):
    cancelled_ids = []
    for task in get_user_tasks(user_id, limit=2000):
        status = str(task.get("status") or "").strip().lower()
        if status in {"completed", "failed", "cancelled"}:
            continue
        if _cancel_task_record(str(task.get("id") or "")):
            cancelled_ids.append(str(task.get("id") or ""))
        if len(cancelled_ids) >= max(1, int(limit or 1)):
            break
    return cancelled_ids if return_task_ids else len(cancelled_ids)


def debug_log(msg: str):
    if ENABLE_TASK_DEBUG:
        print(f"[TASK-DEBUG] {msg}")


_PROGRESS_LAST_UPDATE_AT: dict[str, float] = {}


async def progress_callback(current: int, total: int, client, task_id: str, stage: str = "processing"):
    task_id = str(task_id or "").strip()
    if not task_id:
        return
    now_ts = time.time()
    last_ts = float(_PROGRESS_LAST_UPDATE_AT.get(task_id, 0.0) or 0.0)
    min_interval = max(0.2, float(PROGRESS_UPDATE_INTERVAL or 1.0))
    if total > 0 and current < total and (now_ts - last_ts) < min_interval:
        return
    _PROGRESS_LAST_UPDATE_AT[task_id] = now_ts

    total_value = max(0, int(total or 0))
    current_value = max(0, int(current or 0))
    percent = 0.0
    if total_value > 0:
        percent = min(100.0, max(0.0, (current_value * 100.0) / float(total_value)))

    payload = {
        "current_stage": str(stage or "processing"),
        "progress": percent,
        "progress_percent": percent,
        "current_bytes": current_value,
        "total_bytes": total_value,
    }
    if SHOW_PROGRESS_BAR:
        payload["progress_bar_text"] = progress_bar(percent, PROGRESS_BAR_LENGTH)
    if SHOW_REALTIME_SPEED and last_ts > 0 and (now_ts - last_ts) > 0:
        payload["speed_bps"] = max(0, int((current_value - int((get_task(task_id) or {}).get("current_bytes", 0) or 0)) / (now_ts - last_ts)))
    touch_task(task_id, payload)
    await update_task_status_message(client, task_id, done=False)


async def safe_delete_message(message_obj):
    if not message_obj:
        return
    try:
        await message_obj.delete()
    except Exception as e:
        debug_log(f"Failed to delete temporary message: {e}")


async def edit_or_reply(message, text: str, info_message=None):
    try:
        if info_message:
            return await info_message.edit_text(text, disable_web_page_preview=True)
    except Exception:
        pass
    try:
        return await message.reply_text(text, disable_web_page_preview=True)
    except Exception:
        return None


async def update_checking_message(client, task_id: str, text: str | None = None):
    task = get_task(task_id) or {}
    chat_id = task.get("checking_chat_id")
    message_id = task.get("checking_message_id")
    if not chat_id or not message_id:
        return
    try:
        await asyncio.sleep(0)
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text or checking_text(task.get("source", "")),
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def ensure_task_card_visible(client, task_id: str):
    task = get_task(task_id) or {}
    if task.get("status_chat_id") and task.get("status_message_id"):
        return True

    checking_chat_id = task.get("checking_chat_id")
    checking_message_id = task.get("checking_message_id")
    if not checking_chat_id or not checking_message_id:
        return False

    try:
        await asyncio.sleep(0)
        await client.edit_message_text(
            chat_id=checking_chat_id,
            message_id=checking_message_id,
            text=task_running_text(task),
            reply_markup=task_buttons(task_id, done=False, status=task.get("status", "")),
            disable_web_page_preview=True,
        )
        touch_task(task_id, {
            "status_chat_id": checking_chat_id,
            "status_message_id": checking_message_id,
            "checking_chat_id": 0,
            "checking_message_id": 0,
            "pinned_ui": True,
            "is_visible": True,
        })
        return True
    except Exception as e:
        debug_log(f"ensure_task_card_visible failed for {task_id}: {e}")
        return False


def should_show_processing_card(task: dict) -> bool:
    if not isinstance(task, dict):
        return False
    stage = str(task.get("current_stage") or task.get("status") or "").strip().lower()
    return stage in {
        "checking",
        "queued",
        "fetching",
        "processing",
        "validating",
        "retrying",
        "downloading",
        "uploading",
        "copying",
        "completed",
        "failed",
        "cancelled",
    }


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
            reply_markup=task_buttons(task_id, done=done, status=task.get("status", "")),
            disable_web_page_preview=True,
        )

        if done and task.get("status") in {"completed", "failed", "cancelled"}:
            asyncio.create_task(hide_task_card_later(client, task_id))
    except Exception as e:
        debug_log(f"Failed to update task card {task_id}: {e}")


async def create_task_status_message(message, task_id: str, checking_message=None):
    task = get_task(task_id)
    if not task:
        return None

    sent = checking_message
    reply_markup = task_buttons(task_id, done=False, status=task.get("status", ""))
    waiting_text = task_running_text(task)

    try:
        if sent is None:
            sent = await message.reply_text(
                waiting_text,
                reply_markup=reply_markup,
                disable_web_page_preview=True,
            )
        else:
            await sent.edit_text(waiting_text, reply_markup=reply_markup, disable_web_page_preview=True)
    except Exception:
        try:
            sent = await message.reply_text(waiting_text, disable_web_page_preview=True)
        except Exception:
            sent = None

    if sent:
        touch_task(task_id, {
            "status_chat_id": getattr(getattr(sent, "chat", None), "id", 0),
            "status_message_id": getattr(sent, "id", 0),
            "checking_chat_id": 0,
            "checking_message_id": 0,
            "pinned_ui": True,
            "is_visible": True,
        })
    return sent


async def ask_login_for_private_link(message, info_message=None):
    text = (
        "ðŸ”🔒 Private channel/group link detect hui hai.\n\n"
        "Is content ko save karne ke liye pehle /login karke apna Telegram account authorize karo."
    )
    await edit_or_reply(message, text, info_message)


async def ask_set_destination(message, info_message=None, settings: dict | None = None):
    text = build_missing_storage_target_text(settings)
    await edit_or_reply(message, text, info_message)

def _get_force_sub_cached_block_state(user_id: int):
    cached = FORCE_SUB_STATUS_CACHE.get(int(user_id or 0))
    if not cached:
        return None
    if float(cached.get("expires_at", 0.0) or 0.0) <= time.time():
        FORCE_SUB_STATUS_CACHE.pop(int(user_id or 0), None)
        return None
    return bool(cached.get("blocked", False))


def _cache_force_sub_block_state(user_id: int, blocked: bool):
    ttl = FORCE_SUB_BLOCKED_CACHE_TTL_SECONDS if blocked else FORCE_SUB_CACHE_TTL_SECONDS
    FORCE_SUB_STATUS_CACHE[int(user_id or 0)] = {
        "blocked": bool(blocked),
        "expires_at": time.time() + ttl,
    }


async def check_force_sub(client, message, *, user_id: int | None = None, force_refresh: bool = False):
    if not FORCE_SUB:
        return False

    target_user_id = int(user_id or getattr(getattr(message, "from_user", None), "id", 0) or 0)
    if target_user_id <= 0:
        return False

    if not force_refresh:
        cached_blocked = _get_force_sub_cached_block_state(target_user_id)
        if cached_blocked is False:
            return False
        if cached_blocked is True:
            await message.reply_text(
                "🚫 Required channel join kiye bina bot use nahi kar sakte.\n\nPehle channel join karo, phir /start bhejo.",
                reply_markup=join_required_buttons(),
            )
            return True

    try:
        await client.get_chat_member(FORCE_SUB, target_user_id)
        _cache_force_sub_block_state(target_user_id, False)
        return False
    except UserNotParticipant:
        _cache_force_sub_block_state(target_user_id, True)
        await message.reply_text(
            "🚫 Required channel join kiye bina bot use nahi kar sakte.\n\nPehle channel join karo, phir /start bhejo.",
            reply_markup=join_required_buttons(),
        )
        return True
    except Exception as e:
        if not FORCE_SUB_STRICT:
            return False
        await message.reply_text(f"⚠️ Join check me issue aa gaya:\n{e}\n\n/start dubara bhejo.")
        return True
