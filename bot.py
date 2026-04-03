from __future__ import annotations

import os
import re
import uuid
import time
import asyncio
import config as cfg

from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from pyrogram.errors import (
    UserNotParticipant,
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PasswordHashInvalid,
    PhoneNumberInvalid,
    FloodWait,
)

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    SESSION_NAME,
    FORCE_SUB,
    OWNER_ID,
    ADMIN_IDS,
    LOG_CHANNEL,
    TEMP_DIR,
    MAX_TASKS_PER_USER,
    MAX_BATCH_LINKS,
    BATCH_DELAY,
    DEFAULT_DESTINATION,
    ENABLE_DIRECT_PUBLIC_COPY,
    ENABLE_DIRECT_PRIVATE_COPY,
    ENABLE_LOG_FROM_DESTINATION,
    AUTO_RETRY_FAILED_TASKS,
    MAX_RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS,
)

from keyboards import (
    join_required_buttons,
    start_buttons,
    settings_home_buttons,
    submenu_nav,
    thumbnail_buttons,
    caption_buttons,
    caption_index_buttons,
    simple_set_buttons,
    metadata_buttons,
    metadata_field_buttons,
    index_buttons,
    login_buttons,
    task_buttons,
    my_tasks_buttons,
    auto_rename_buttons,
    filename_index_buttons,
    batch_buttons,
    batch_live_board_buttons,
    admin_panel_buttons,
    premium_info_buttons,
)

from texts import (
    start_text,
    help_text,
    plan_text,
    terms_text,
    settings_home_text,
    upload_mode_text,
    thumbnail_text,
    caption_text,
    prefix_text,
    suffix_text,
    auto_rename_text,
    destination_text,
    topic_id_text,
    replace_words_text,
    metadata_home_text,
    metadata_field_text,
    batch_text,
    unknown_text,
    index_started_text,
    index_stopped_text,
    index_stats_text,
    index_info_text,
    login_intro_text,
    ask_phone_text,
    ask_code_text,
    ask_password_text,
    login_success_text,
    login_failed_text,
    login_status_text,
    logout_success_text,
    logout_missing_text,
    checking_text,
    task_running_text,
    task_completed_text,
    task_failed_text,
    my_tasks_text,
    batch_live_board_text,
    batch_completed_board_text,
    auto_index_completed_text,
    premium_info_text,
    admin_panel_text,
    admin_premium_help_text,
)

from storage import (
    WAITING_KEYS,
    add_index_entry,
    ban_user,
    banned_count,
    clear_user_state,
    get_recent_users,
    get_user_settings,
    get_user_state,
    increase_index_user_count,
    is_banned,
    is_index_mode,
    register_user,
    reset_user_settings,
    set_index_mode,
    set_user_state,
    unban_user,
    update_user_settings,
    user_count,
    save_user_session,
    get_user_session_string,
    has_user_session,
    delete_user_session,
    set_login_temp,
    get_login_temp,
    clear_login_temp,
    set_task,
    get_task,
    get_user_tasks,
    count_running_tasks,
    format_index_number,
    get_settings_marks,
    reset_user_index_counter,
    get_next_user_index,
    set_batch_mode,
    is_batch_mode,
    save_batch_input,
    get_batch_input,
    parse_batch_links,
    is_premium_user,
    get_user_batch_limit,
    get_user_task_limit,
    add_premium,
    remove_premium,
    get_premium_expiry_text,
    cleanup_expired_premium_users,
    cleanup_stale_active_tasks,
    delete_task,
)

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

TEMP_LOGIN_CLIENTS = {}

GLOBAL_MAX_RUNNING_TASKS = int(getattr(cfg, "GLOBAL_MAX_RUNNING_TASKS", 20) or 20)
QUEUE_POLL_INTERVAL = float(getattr(cfg, "QUEUE_POLL_INTERVAL", 1.0) or 1.0)
ENABLE_TASK_DEBUG = bool(getattr(cfg, "ENABLE_TASK_DEBUG", False))
TASK_CARD_HIDE_DELAY = int(getattr(cfg, "TASK_CARD_HIDE_DELAY", 8) or 8)
PROGRESS_UPDATE_INTERVAL = float(getattr(cfg, "PROGRESS_UPDATE_INTERVAL", 2.0) or 2.0)
PROGRESS_BAR_LENGTH = int(getattr(cfg, "PROGRESS_BAR_LENGTH", 10) or 10)
SHOW_PROGRESS_BAR = bool(getattr(cfg, "SHOW_PROGRESS_BAR", True))
SHOW_REALTIME_SPEED = bool(getattr(cfg, "SHOW_REALTIME_SPEED", True))
SHOW_REALTIME_ETA = bool(getattr(cfg, "SHOW_REALTIME_ETA", True))
SHOW_TRANSFERRED_SIZE = bool(getattr(cfg, "SHOW_TRANSFERRED_SIZE", True))

TASK_QUEUE: asyncio.Queue = asyncio.Queue()
TASK_WORKERS = []
TASK_WORKERS_STARTED = False
TASK_WORKER_LOCK = None


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ADMIN_IDS


def normalize_target(target: str):
    target = (target or "").strip()
    if not target:
        return None
    if target.lstrip("-").isdigit():
        return int(target)
    return target


def safe_topic_id(value: str):
    value = (value or "").strip()
    if value.lstrip("-").isdigit():
        return int(value)
    return None


def make_task_id() -> str:
    return uuid.uuid4().hex[:12]


def sanitize_filename(name: str) -> str:
    if not name:
        return "file"
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, ' ')
    return ' '.join(name.split()).strip() or "file"


def split_filename_ext(filename: str):
    filename = filename or ""
    if "." in filename:
        return os.path.splitext(filename)
    return filename, ""


def apply_replace_rules(value: str, rules: str) -> str:
    value = value or ""
    rules = (rules or "").strip()
    if not rules:
        return value

    for part in rules.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            old, new = part.split(":", 1)
            value = value.replace(old.strip(), new.strip())
        else:
            value = value.replace(part, "")
    return " ".join(value.split()).strip()


def get_message_file_name(source_msg) -> str:
    if source_msg.document and getattr(source_msg.document, "file_name", None):
        return source_msg.document.file_name
    if source_msg.video and getattr(source_msg.video, "file_name", None):
        return source_msg.video.file_name
    if source_msg.audio and getattr(source_msg.audio, "file_name", None):
        return source_msg.audio.file_name
    if source_msg.animation and getattr(source_msg.animation, "file_name", None):
        return source_msg.animation.file_name
    if source_msg.photo:
        return "photo.jpg"
    if source_msg.voice:
        return "voice.ogg"
    return "file"


def get_message_file_size(source_msg) -> int:
    for media in ("document", "video", "audio", "photo", "voice", "animation"):
        obj = getattr(source_msg, media, None)
        if obj and getattr(obj, "file_size", None):
            return int(getattr(obj, "file_size", 0) or 0)
    return 0


def get_message_duration(source_msg) -> str:
    for media in ("video", "audio", "voice", "animation"):
        obj = getattr(source_msg, media, None)
        if obj and getattr(obj, "duration", None):
            return str(getattr(obj, "duration", "") or "")
    return ""


def is_media_message(source_msg) -> bool:
    if not source_msg:
        return False

    direct_media = (
        getattr(source_msg, "photo", None)
        or getattr(source_msg, "video", None)
        or getattr(source_msg, "document", None)
        or getattr(source_msg, "audio", None)
        or getattr(source_msg, "voice", None)
        or getattr(source_msg, "animation", None)
    )
    if direct_media:
        return True

    media_name = str(getattr(source_msg, "media", "") or "").lower()
    return media_name in {
        "message_media_type.photo",
        "message_media_type.video",
        "message_media_type.document",
        "message_media_type.audio",
        "message_media_type.voice",
        "message_media_type.animation",
        "photo",
        "video",
        "document",
        "audio",
        "voice",
        "animation",
    }


def is_media_like_message(source_msg) -> bool:
    if is_media_message(source_msg):
        return True
    media_name = str(getattr(source_msg, "media", "") or "").lower()
    return any(token in media_name for token in ["photo", "video", "document", "audio", "voice", "animation"])


def build_template_context(source_msg, settings: dict, index_no: int = 0):
    filename = sanitize_filename(get_message_file_name(source_msg))
    filename = apply_replace_rules(filename, settings.get("replace_words", ""))

    caption_padding = int(settings.get("caption_index_padding", 2) or 2)
    caption_start = int(settings.get("caption_index_start", 1) or 1)
    filename_padding = int(settings.get("filename_index_padding", 2) or 2)
    filename_start = int(settings.get("filename_index_start", 1) or 1)

    caption_index_value = format_index_number(max(0, caption_start + max(0, index_no - 1)), caption_padding)
    filename_index_value = format_index_number(max(0, filename_start + max(0, index_no - 1)), filename_padding)

    return {
        "filename": filename,
        "size": str(get_message_file_size(source_msg) or ""),
        "duration": get_message_duration(source_msg),
        "quality": "",
        "language": "",
        "subtitle": "",
        "index": caption_index_value,
        "fileindex": filename_index_value,
    }


def render_template(template: str, context: dict) -> str:
    result = template or ""
    for key, value in context.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def get_parse_mode(value: str | None):
    value = str(value or "").strip().lower()
    if value == "markdown":
        return ParseMode.MARKDOWN
    if value in {"disabled", "none", "off", "text"}:
        return None
    return ParseMode.HTML


def ensure_non_empty_text(value: str | None) -> str:
    value = str(value or "")
    return value if value.strip() else "⁣"


def resolve_downloaded_path(requested_path: str | None, download_result) -> str:
    candidates = []
    if isinstance(download_result, str):
        candidates.append(download_result)
    if isinstance(requested_path, str):
        candidates.append(requested_path)
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return str(download_result or requested_path or "")


def ensure_valid_downloaded_file(file_path: str):
    if not file_path or not os.path.exists(file_path):
        raise RuntimeError("Download complete hone ke baad file temp me nahi mili.")
    try:
        size = os.path.getsize(file_path)
    except Exception:
        size = 0
    if size <= 0:
        raise RuntimeError("Downloaded file ka size 0 B aaya. Source restricted/protected ho sakta hai ya download corrupt hua hai.")
    return file_path


def build_final_caption(source_msg, settings: dict, index_no: int = 0):
    context = build_template_context(source_msg, settings, index_no=index_no)
    caption = source_msg.caption or ""

    if settings.get("caption_enabled") and settings.get("caption_text"):
        caption = render_template(settings.get("caption_text", ""), context)

    caption = apply_replace_rules(caption, settings.get("replace_words", ""))

    prefix = (settings.get("prefix") or "").strip()
    suffix = (settings.get("suffix") or "").strip()

    if caption:
        if prefix:
            caption = f"{prefix} {caption}".strip()
        if suffix:
            caption = f"{caption} {suffix}".strip()

    return caption


def build_final_text(text: str, source_msg, settings: dict, index_no: int = 0):
    context = build_template_context(source_msg, settings, index_no=index_no)
    value = text or ""

    if settings.get("caption_enabled") and settings.get("caption_text"):
        value = render_template(settings.get("caption_text", value), context)

    value = apply_replace_rules(value, settings.get("replace_words", ""))

    prefix = (settings.get("prefix") or "").strip()
    suffix = (settings.get("suffix") or "").strip()

    if prefix:
        value = f"{prefix} {value}".strip()
    if suffix:
        value = f"{value} {suffix}".strip()

    return value or " "


def build_final_filename(original_filename: str, settings: dict, index_no: int = 0):
    original_filename = sanitize_filename(original_filename or "file")
    original_filename = apply_replace_rules(original_filename, settings.get("replace_words", ""))

    base, ext = split_filename_ext(original_filename)
    filename_padding = int(settings.get("filename_index_padding", 2) or 2)
    filename_start = int(settings.get("filename_index_start", 1) or 1)
    filename_index_value = format_index_number(max(0, filename_start + max(0, index_no - 1)), filename_padding)

    context = {"filename": base, "index": filename_index_value}
    rename_template = (settings.get("rename_template") or "").strip()
    auto_rename = (settings.get("auto_rename") or "").strip()
    new_base = base

    if rename_template:
        new_base = render_template(rename_template, context).strip()
    elif settings.get("auto_rename_enabled") and auto_rename:
        if "{filename}" in auto_rename or "{index}" in auto_rename:
            new_base = render_template(auto_rename, context).strip()
        else:
            new_base = auto_rename.strip()

    if settings.get("filename_index_enabled") and "{index}" not in new_base:
        new_base = f"{filename_index_value}_{new_base}".strip("_ ")

    file_prefix = (settings.get("filename_prefix") or "").strip()
    file_suffix = (settings.get("filename_suffix") or "").strip()

    if file_prefix:
        new_base = f"{file_prefix} {new_base}".strip()
    if file_suffix:
        new_base = f"{new_base} {file_suffix}".strip()

    new_base = apply_replace_rules(new_base, settings.get("replace_words", ""))
    new_base = sanitize_filename(new_base)
    return f"{new_base}{ext}"


def touch_task(task_id: str, payload: dict):
    payload = dict(payload or {})
    payload["updated_at"] = now_iso()
    set_task(task_id, payload)


def ensure_task_not_cancelled(task_id: str):
    task = get_task(task_id) or {}
    if task.get("status") == "cancelled":
        raise RuntimeError("Task cancelled by user")


def human_bytes(value: float) -> str:
    try:
        value = float(value)
    except Exception:
        value = 0.0

    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.2f} {units[idx]}"


def human_speed(bytes_per_sec: float) -> str:
    return f"{human_bytes(bytes_per_sec)}/s"


def human_eta(seconds: float) -> str:
    try:
        seconds = int(max(0, seconds))
    except Exception:
        seconds = 0

    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def progress_bar(percent: float, length: int = 10) -> str:
    try:
        percent = max(0.0, min(100.0, float(percent)))
    except Exception:
        percent = 0.0
    filled = int(round((percent / 100.0) * length))
    return "█" * filled + "░" * (length - filled)


def has_transforming_settings(settings: dict) -> bool:
    settings = settings or {}
    return bool(
        settings.get("thumbnail_enabled")
        or (settings.get("caption_enabled") and settings.get("caption_text"))
        or settings.get("prefix")
        or settings.get("suffix")
        or settings.get("replace_words")
        or settings.get("auto_rename_enabled")
        or settings.get("rename_template")
        or settings.get("auto_rename")
        or settings.get("filename_prefix")
        or settings.get("filename_suffix")
        or settings.get("filename_index_enabled")
        or settings.get("metadata_enabled")
    )


def derive_batch_name(raw_text: str, links: list[str] | None = None) -> str:
    raw_text = str(raw_text or "").strip()
    links = links or []
    for line in raw_text.splitlines():
        value = str(line or "").strip()
        if not value:
            continue
        if not value.startswith("http://") and not value.startswith("https://"):
            return value[:80]
    if links:
        first = str(links[0]).strip()
        if "/c/" in first:
            return "Private Channel Batch"
        return "Telegram Batch Job"
    return "Batch Job"


async def try_direct_forward_with_user_client(user_client, source_msg, target, settings: dict):
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    try:
        result = await user_client.copy_message(
            chat_id=target,
            from_chat_id=source_msg.chat.id,
            message_id=source_msg.id,
            message_thread_id=topic_id if topic_id else None,
        )
        if result:
            return result
    except Exception:
        pass

    try:
        return await user_client.forward_messages(
            chat_id=target,
            from_chat_id=source_msg.chat.id,
            message_ids=source_msg.id,
            message_thread_id=topic_id if topic_id else None,
            drop_author=False,
        )
    except Exception:
        return None


def build_settings_home_markup(user_id: int):
    marks = get_settings_marks(user_id)
    has_session = has_user_session(user_id)
    upload_mode = get_user_settings(user_id).get("upload_mode", "media")
    return settings_home_buttons(
        marks,
        has_session,
        upload_mode,
        is_admin(user_id),
        is_premium_user(user_id),
    )


def build_start_markup(user_id: int):
    return start_buttons(
        has_user_session(user_id),
        is_admin(user_id),
        is_premium_user(user_id),
    )


def build_upload_mode_message(user_id: int):
    return upload_mode_text(user_id)


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
    }
    sent = await message.reply_text(
        batch_live_board_text(board),
        reply_markup=batch_live_board_buttons(batch_key, done=False, current_task_id=str(board.get("current_task_id", "") or "")),
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
        board["status"] = "Completed"
        board["current_stage"] = "Completed"
        board["current_task_id"] = ""
        text = batch_completed_board_text(board)
        markup = batch_live_board_buttons(batch_key, done=True, current_task_id=str(board.get("current_task_id", "") or ""))
    else:
        text = batch_live_board_text(board)
        markup = batch_live_board_buttons(batch_key, done=False, current_task_id=str(board.get("current_task_id", "") or ""))

    try:
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
    await _refresh_batch_board_message(client, user_id)


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



def debug_log(msg: str):
    if ENABLE_TASK_DEBUG:
        print(f"[TASK-DEBUG] {msg}")


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
    return stage in {"downloading", "uploading", "copying", "completed", "failed", "cancelled"}


async def ask_login_for_private_link(message, info_message=None):
    text = (
        "🔐 Private channel/group link detect hui hai.\n\n"
        "Is content ko save karne ke liye pehle /login karke apna Telegram account authorize karo."
    )
    await edit_or_reply(message, text, info_message)


async def ask_set_destination(message, info_message=None):
    text = (
        "📍 Pehle apna destination set karo.\n\n"
        "/settings → Destination me chat id ya @channelusername set karo, tabhi content save hoga."
    )
    await edit_or_reply(message, text, info_message)


async def ensure_background_workers_started(client):
    global TASK_WORKERS_STARTED, TASK_WORKER_LOCK
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
        TASK_WORKERS_STARTED = True
        print(f"🧵 Task workers started: {worker_count}")


async def task_worker(client, worker_id: int):
    print(f"🧵 Worker-{worker_id} online")
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
                await message.reply_text(f"❌ FloodWait: {e.value}s wait karo.")
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
                await message.reply_text(f"❌ Task failed:\n{e}")
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

    if checking_message:
        touch_task(task_id, {
            "checking_chat_id": checking_message.chat.id,
            "checking_message_id": checking_message.id,
            "pinned_ui": True,
            "is_visible": False,
        })
        await update_checking_message(message._client, task_id)
        return

    sent = await message.reply_text(
        checking_text(task.get("source", "")),
        disable_web_page_preview=True,
    )
    touch_task(task_id, {
        "checking_chat_id": sent.chat.id,
        "checking_message_id": sent.id,
        "pinned_ui": True,
        "is_visible": False,
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
        "progress_text": " • ".join(compact_parts),
        "is_visible": True,
    })
    await throttled_progress_update(client, task_id)


async def check_force_sub(client, message):
    if not FORCE_SUB:
        return False

    try:
        await client.get_chat_member(FORCE_SUB, message.from_user.id)
        return False
    except UserNotParticipant:
        await message.reply_text(
            "❌ Required channel join kiye bina bot use nahi kar sakte.\n\nPehle channel join karo, phir /start bhejo.",
            reply_markup=join_required_buttons(),
        )
        return True
    except Exception as e:
        await message.reply_text(f"⚠️ Join check me issue aa gaya:\n{e}\n\n/start dubara bhejo.")
        return True


@app.on_callback_query(filters.regex("check_join_again"))
async def check_join_again(client, callback_query):
    blocked = await check_force_sub(client, callback_query.message)
    if not blocked:
        await callback_query.message.reply_text("✅ Join verify ho gaya.\nAb /start bhejo aur bot use karo.")
    await callback_query.answer()


def extract_telegram_link_info(text: str):
    if not text:
        return None

    text = str(text).strip()
    text = text.split("?", 1)[0].split("#", 1)[0].rstrip("/")

    private_topic_match = re.search(r"https?://(?:t|telegram)\.me/c/(\d+)/(\d+)/(\d+)$", text)
    private_match = re.search(r"https?://(?:t|telegram)\.me/c/(\d+)/(\d+)$", text)
    public_topic_match = re.search(r"https?://(?:t|telegram)\.me/([A-Za-z0-9_]+)/(\d+)/(\d+)$", text)
    public_match = re.search(r"https?://(?:t|telegram)\.me/([A-Za-z0-9_]+)/(\d+)$", text)

    if private_topic_match:
        raw_chat_id = private_topic_match.group(1)
        topic_id = int(private_topic_match.group(2))
        msg_id = int(private_topic_match.group(3))
        chat_id = int(f"-100{raw_chat_id}")
        return {"chat_id": chat_id, "message_id": msg_id, "topic_id": topic_id, "link_type": "private_topic"}

    if private_match:
        raw_chat_id = private_match.group(1)
        msg_id = int(private_match.group(2))
        chat_id = int(f"-100{raw_chat_id}")
        return {"chat_id": chat_id, "message_id": msg_id, "link_type": "private"}

    if public_topic_match:
        username = public_topic_match.group(1)
        topic_id = int(public_topic_match.group(2))
        msg_id = int(public_topic_match.group(3))
        if username.lower() != "c":
            return {"chat_id": username, "message_id": msg_id, "topic_id": topic_id, "link_type": "public_topic"}

    if public_match:
        username = public_match.group(1)
        msg_id = int(public_match.group(2))
        if username.lower() != "c":
            return {"chat_id": username, "message_id": msg_id, "link_type": "public"}

    return None

    text = str(text).strip()
    text = text.split("?", 1)[0].split("#", 1)[0]

    private_match = re.search(r"https?://(?:t|telegram)\.me/c/(\d+)/(\d+)", text)
    public_match = re.search(r"https?://(?:t|telegram)\.me/([A-Za-z0-9_]+)/(\d+)", text)

    if private_match:
        raw_chat_id = private_match.group(1)
        msg_id = int(private_match.group(2))
        chat_id = int(f"-100{raw_chat_id}")
        return {"chat_id": chat_id, "message_id": msg_id, "link_type": "private"}

    if public_match:
        username = public_match.group(1)
        msg_id = int(public_match.group(2))
        if username.lower() != "c":
            return {"chat_id": username, "message_id": msg_id, "link_type": "public"}

    return None


def get_temp_download_path(source_msg):
    os.makedirs(TEMP_DIR, exist_ok=True)
    unique = uuid.uuid4().hex[:8]
    base_name = f"cd_{int(time.time())}_{source_msg.id}_{unique}"

    if source_msg.document and getattr(source_msg.document, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.document.file_name)}")
    if source_msg.video and getattr(source_msg.video, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.video.file_name)}")
    if source_msg.audio and getattr(source_msg.audio, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.audio.file_name)}")
    if source_msg.animation and getattr(source_msg.animation, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.animation.file_name)}")
    if source_msg.photo:
        return os.path.join(TEMP_DIR, f"{base_name}.jpg")
    if source_msg.voice:
        return os.path.join(TEMP_DIR, f"{base_name}.ogg")
    return os.path.join(TEMP_DIR, f"{base_name}.bin")


def rename_downloaded_file(file_path: str, source_msg, settings: dict, index_no: int = 0):
    if not file_path or not os.path.exists(file_path):
        return file_path

    original_name = get_message_file_name(source_msg) or os.path.basename(file_path)
    final_name = build_final_filename(original_name, settings, index_no=index_no)
    final_path = os.path.join(os.path.dirname(file_path), final_name)

    if final_path == file_path:
        return file_path

    try:
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(file_path, final_path)
        return final_path
    except Exception:
        return file_path


async def get_authorized_client_for_user(user_id: int):
    session_string = get_user_session_string(user_id)
    if not session_string:
        return None

    client = Client(
        name=f"user_session_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True,
    )
    await client.connect()
    return client


async def fetch_message_via_best_client(bot_client, user_id: int, link_text: str):
    info = extract_telegram_link_info(link_text)
    if not info:
        return None, None, None, "bot"

    try:
        msg = await bot_client.get_messages(info["chat_id"], info["message_id"])
        if msg and not getattr(msg, "empty", False):
            return msg, info, None, "bot"
    except Exception:
        pass

    if has_user_session(user_id):
        user_client = await get_authorized_client_for_user(user_id)
        try:
            msg = await user_client.get_messages(info["chat_id"], info["message_id"])
            if msg and not getattr(msg, "empty", False):
                return msg, info, user_client, "user"
        except Exception:
            await user_client.disconnect()
            raise

    return None, info, None, "bot"


def can_direct_copy(source_msg, settings: dict, fetch_mode: str = "bot") -> bool:
    if not is_media_message(source_msg):
        return False
    if has_transforming_settings(settings):
        return False
    if fetch_mode == "bot":
        return bool(ENABLE_DIRECT_PUBLIC_COPY and cfg.PREFER_COPY_OVER_DOWNLOAD)
    # Private/user-session sources ko bot client se direct copy nahi karna chahiye.
    # Unke liye alag user-client fast path use hota hai.
    return False


def has_transferable_content(source_msg) -> bool:
    if not source_msg:
        return False
    if is_media_message(source_msg):
        return True
    if str(getattr(source_msg, "text", "") or "").strip():
        return True
    if str(getattr(source_msg, "caption", "") or "").strip():
        return True
    media_name = str(getattr(source_msg, "media", "") or "").strip().lower()
    if media_name and media_name not in {"none", "0", "messagemediatype.empty", "empty"}:
        return True
    return False


def get_transfer_validation_error(source_msg) -> str | None:
    if not source_msg:
        return "Source post fetch nahi hua. Link invalid ho sakti hai ya access missing hai."
    if getattr(source_msg, "empty", False):
        return "Source post empty/not found mili. Shayad link par post exist nahi karti."
    if getattr(source_msg, "service", None):
        return "Ye service/system message hai, isliye save nahi ki ja sakti."
    if not has_transferable_content(source_msg):
        return "Is link par transferable post content nahi mila. Post deleted, invalid, ya unsupported ho sakti hai."
    return None


async def try_direct_copy(client, source_msg, target, settings: dict):
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    result = await client.copy_message(
        chat_id=target,
        from_chat_id=source_msg.chat.id,
        message_id=source_msg.id,
        message_thread_id=topic_id if topic_id else None,
    )
    if not result:
        raise RuntimeError(f"Direct copy failed for destination {target}")
    return result


async def get_thumbnail_temp_path(client, settings: dict, task_id: str = ""):
    thumb_file_id = (settings.get("thumbnail_file_id") or "").strip()
    if not settings.get("thumbnail_enabled") or not thumb_file_id:
        return None

    os.makedirs(TEMP_DIR, exist_ok=True)
    thumb_path = os.path.join(TEMP_DIR, f"thumb_{task_id or uuid.uuid4().hex[:8]}.jpg")

    try:
        result = await client.download_media(thumb_file_id, file_name=thumb_path)
        if result and os.path.exists(result):
            return result
    except Exception:
        pass
    return None


async def upload_file_to_target(client, task_id: str, target, file_path: str, source_msg, settings: dict, index_no: int = 0):
    ensure_task_not_cancelled(task_id)
    caption = build_final_caption(source_msg, settings, index_no=index_no)
    caption = caption if str(caption or "").strip() else None
    caption_parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html")) if caption else None
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    thumb_path = None

    try:
        upload_mode = str(settings.get("upload_mode", "media") or "media").strip().lower()

        if source_msg.video or source_msg.document or source_msg.audio or source_msg.animation:
            thumb_path = await get_thumbnail_temp_path(client, settings, task_id=task_id)

        if upload_mode == "document":
            result = await client.send_document(
                chat_id=target,
                document=file_path,
                caption=caption,
                parse_mode=caption_parse_mode,
                thumb=thumb_path if thumb_path else None,
                message_thread_id=topic_id if topic_id else None,
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
            )
            if not result:
                raise RuntimeError(f"Document upload failed for {target}")
            return result

        if source_msg.photo:
            result = await client.send_photo(
                chat_id=target,
                photo=file_path,
                caption=caption,
                parse_mode=caption_parse_mode,
                message_thread_id=topic_id if topic_id else None,
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
            )
            if not result:
                raise RuntimeError(f"Photo upload failed for {target}")
            return result

        if source_msg.video or source_msg.animation:
            result = await client.send_video(
                chat_id=target,
                video=file_path,
                caption=caption,
                parse_mode=caption_parse_mode,
                thumb=thumb_path if thumb_path else None,
                message_thread_id=topic_id if topic_id else None,
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
            )
            if not result:
                raise RuntimeError(f"Video upload failed for {target}")
            return result

        if source_msg.audio:
            result = await client.send_audio(
                chat_id=target,
                audio=file_path,
                caption=caption,
                parse_mode=caption_parse_mode,
                thumb=thumb_path if thumb_path else None,
                message_thread_id=topic_id if topic_id else None,
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
            )
            if not result:
                raise RuntimeError(f"Audio upload failed for {target}")
            return result

        if source_msg.voice:
            result = await client.send_voice(
                chat_id=target,
                voice=file_path,
                caption=caption,
                parse_mode=caption_parse_mode,
                message_thread_id=topic_id if topic_id else None,
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
            )
            if not result:
                raise RuntimeError(f"Voice upload failed for {target}")
            return result

        result = await client.send_document(
            chat_id=target,
            document=file_path,
            caption=caption,
            parse_mode=caption_parse_mode,
            thumb=thumb_path if thumb_path else None,
            message_thread_id=topic_id if topic_id else None,
            progress=progress_callback,
            progress_args=(client, task_id, "uploading"),
        )
        if not result:
            raise RuntimeError(f"Fallback document upload failed for {target}")
        return result
    finally:
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass


async def send_text_to_target(client, target, source_msg, settings: dict, index_no: int = 0):
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    raw_text = build_final_text(source_msg.text or source_msg.caption or "", source_msg, settings, index_no=index_no)
    final_text = ensure_non_empty_text(raw_text)
    parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html")) if str(raw_text or "").strip() else None
    result = await client.send_message(
        chat_id=target,
        text=final_text,
        parse_mode=parse_mode,
        message_thread_id=topic_id if topic_id else None,
        disable_web_page_preview=True,
    )
    if not result:
        raise RuntimeError(f"Text send failed for {target}")
    return result


def build_index_entry(user_id: int, source_msg, link_text: str, info):
    content_type = (
        "photo" if source_msg.photo else
        "video" if source_msg.video else
        "document" if source_msg.document else
        "audio" if source_msg.audio else
        "voice" if source_msg.voice else
        "animation" if source_msg.animation else
        "sticker" if source_msg.sticker else
        "text"
    )
    file_obj = (
        source_msg.photo if source_msg.photo else
        source_msg.video if source_msg.video else
        source_msg.document if source_msg.document else
        source_msg.audio if source_msg.audio else
        source_msg.voice if source_msg.voice else
        source_msg.animation if source_msg.animation else
        source_msg.sticker if source_msg.sticker else
        None
    )

    return {
        "user_id": user_id,
        "chat_id": getattr(source_msg.chat, "id", 0) if getattr(source_msg, "chat", None) else 0,
        "message_id": source_msg.id,
        "content_type": content_type,
        "text": source_msg.text or "",
        "caption": source_msg.caption or "",
        "file_id": getattr(file_obj, "file_id", "") if file_obj else "",
        "file_name": get_message_file_name(source_msg) if is_media_message(source_msg) else "",
        "file_size": get_message_file_size(source_msg),
        "source_link": (link_text or "").strip(),
        "link_type": info.get("link_type") if info else "",
        "created_at": now_iso(),
    }


async def copy_result_to_log_channel(client, delivered_message, settings: dict):
    if not LOG_CHANNEL or not delivered_message:
        return None
    try:
        topic_id = safe_topic_id(settings.get("topic_id", ""))
        return await client.copy_message(
            chat_id=LOG_CHANNEL,
            from_chat_id=delivered_message.chat.id,
            message_id=delivered_message.id,
            message_thread_id=topic_id if topic_id else None,
        )
    except Exception:
        return None


async def deliver_primary_then_log(client, task_id: str, source_msg, settings: dict, destination, download_path=None, index_no: int = 0):
    if not destination and not LOG_CHANNEL:
        raise RuntimeError("No destination configured. Destination aur log channel dono blank hain.")

    delivered_to = []
    delivery_errors = []
    primary_result = None

    if destination:
        try:
            primary_result = await deliver_one_target(client, task_id, source_msg, settings, destination, download_path, index_no=index_no)
            if primary_result:
                delivered_to.append(str(destination))
            else:
                delivery_errors.append(f"{destination}: send returned empty response")
        except Exception as e:
            delivery_errors.append(f"{destination}: {e}")

    if LOG_CHANNEL:
        if destination and str(LOG_CHANNEL) == str(destination):
            pass
        elif primary_result and ENABLE_LOG_FROM_DESTINATION:
            copied = await copy_result_to_log_channel(client, primary_result, settings)
            if copied:
                delivered_to.append(str(LOG_CHANNEL))
            else:
                delivery_errors.append(f"{LOG_CHANNEL}: copy from destination failed")
        else:
            try:
                log_result = await deliver_one_target(client, task_id, source_msg, settings, LOG_CHANNEL, download_path, index_no=index_no)
                if log_result:
                    delivered_to.append(str(LOG_CHANNEL))
                else:
                    delivery_errors.append(f"{LOG_CHANNEL}: send returned empty response")
            except Exception as e:
                delivery_errors.append(f"{LOG_CHANNEL}: {e}")

    if not delivered_to:
        raise RuntimeError("Delivery failed: " + " | ".join(delivery_errors))

    return delivered_to, delivery_errors


async def deliver_one_target(client, task_id: str, source_msg, settings: dict, target, download_path=None, index_no: int = 0):
    if download_path:
        return await upload_file_to_target(client, task_id, target, download_path, source_msg, settings, index_no=index_no)
    if is_media_message(source_msg):
        return await try_direct_copy(client, source_msg, target, settings)
    return await send_text_to_target(client, target, source_msg, settings, index_no=index_no)


async def deliver_to_destinations(client, task_id: str, source_msg, settings: dict, destination, download_path=None, index_no: int = 0):
    targets = []
    if destination:
        targets.append(destination)
    if LOG_CHANNEL and str(LOG_CHANNEL) != str(destination):
        targets.append(LOG_CHANNEL)

    if not targets:
        raise RuntimeError("No destination configured. Destination aur log channel dono blank hain.")

    delivered_to = []
    delivery_errors = []

    for target in targets:
        try:
            result = await deliver_one_target(client, task_id, source_msg, settings, target, download_path, index_no=index_no)
            if result:
                delivered_to.append(str(target))
            else:
                delivery_errors.append(f"{target}: send returned empty response")
        except Exception as e:
            delivery_errors.append(f"{target}: {e}")

    if not delivered_to:
        raise RuntimeError("Delivery failed: " + " | ".join(delivery_errors))

    return delivered_to, delivery_errors


async def process_source_message_transfer(client, user_id: int, message, source_msg, task_id: str, settings: dict, destination, source_label: str, info: dict | None = None, user_client=None, fetch_mode: str = "bot", disconnect_user_client: bool = False):
    download_path = None
    delivered_to = []
    delivery_errors = []

    try:
        validation_error = get_transfer_validation_error(source_msg)
        if validation_error:
            raise RuntimeError(validation_error)

        entry = build_index_entry(user_id, source_msg, source_label, info)
        idx_no = add_index_entry(entry)
        user_count_now = increase_index_user_count(user_id)
        user_index_no = get_next_user_index(user_id) - 1 or 1

        direct_copy_allowed = can_direct_copy(source_msg, settings, fetch_mode=fetch_mode)
        direct_forward_allowed = bool(
            fetch_mode == "user"
            and user_client
            and is_media_message(source_msg)
            and cfg.ALLOW_FORWARD_AS_FALLBACK
            and not has_transforming_settings(settings)
        )

        if not is_media_message(source_msg):
            if is_media_like_message(source_msg):
                raise RuntimeError("Source post media-like hai but media object resolve nahi hua. Authorized login se dubara try karo.")
            touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": "", "is_visible": True})
            await update_task_status_message(client, task_id)
            delivered_to, delivery_errors = await deliver_primary_then_log(client, task_id, source_msg, settings, destination, None, index_no=user_index_no)
        else:
            fallback_download = True

            if direct_forward_allowed and user_client:
                touch_task(task_id, {"status": "copying", "current_stage": "copying", "progress_text": "Direct save path", "is_visible": True})
                await update_task_status_message(client, task_id)

                delivered_to, delivery_errors = [], []
                direct_result = None

                if destination:
                    direct_result = await try_direct_forward_with_user_client(user_client, source_msg, destination, settings)
                    if direct_result:
                        delivered_to.append(str(destination))
                    else:
                        delivery_errors.append(f"{destination}: direct save not allowed")

                if LOG_CHANNEL and str(LOG_CHANNEL) != str(destination):
                    if direct_result and ENABLE_LOG_FROM_DESTINATION:
                        copied = await copy_result_to_log_channel(client, direct_result, settings)
                        if copied:
                            delivered_to.append(str(LOG_CHANNEL))
                        else:
                            log_result = await try_direct_forward_with_user_client(user_client, source_msg, LOG_CHANNEL, settings)
                            if log_result:
                                delivered_to.append(str(LOG_CHANNEL))
                            else:
                                delivery_errors.append(f"{LOG_CHANNEL}: copy from destination failed")
                    else:
                        log_result = await try_direct_forward_with_user_client(user_client, source_msg, LOG_CHANNEL, settings)
                        if log_result:
                            delivered_to.append(str(LOG_CHANNEL))
                        else:
                            delivery_errors.append(f"{LOG_CHANNEL}: direct save not allowed")

                fallback_download = not delivered_to

            elif direct_copy_allowed:
                touch_task(task_id, {"status": "copying", "current_stage": "copying", "progress_text": "Direct save path", "is_visible": True})
                await update_task_status_message(client, task_id)
                try:
                    delivered_to, delivery_errors = await deliver_primary_then_log(client, task_id, source_msg, settings, destination, None, index_no=user_index_no)
                    fallback_download = not delivered_to
                except Exception as copy_error:
                    delivered_to, delivery_errors = [], [str(copy_error)]
                    fallback_download = True


            if fallback_download:
                touch_task(task_id, {"status": "downloading", "current_stage": "downloading", "progress_text": "Fallback download path" if delivery_errors else "", "is_visible": True})
                await update_task_status_message(client, task_id)

                download_hint = get_temp_download_path(source_msg)
                source_client = user_client if user_client else client
                download_result = await source_client.download_media(
                    source_msg,
                    file_name=download_hint,
                    progress=progress_callback,
                    progress_args=(client, task_id, "downloading"),
                )
                download_path = resolve_downloaded_path(download_hint, download_result)
                ensure_valid_downloaded_file(download_path)
                download_path = rename_downloaded_file(download_path, source_msg, settings, index_no=user_index_no)
                ensure_valid_downloaded_file(download_path)

                touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": "", "is_visible": True})
                await update_task_status_message(client, task_id)

                delivered_to, delivery_errors = await deliver_primary_then_log(
                    client, task_id, source_msg, settings, destination, download_path, index_no=user_index_no
                )

        result_note = f"Index {idx_no} | Count {user_count_now}"
        if delivery_errors:
            result_note += " | Partial: " + " ; ".join(delivery_errors[:2])

        touch_task(task_id, {
            "status": "completed",
            "current_stage": "completed",
            "is_visible": True,
            "index_id": idx_no,
            "user_index_no": user_index_no,
            "progress_text": result_note,
            "delivered_to": delivered_to,
            "delivery_errors": delivery_errors,
            "error": "",
        })
        await update_task_status_message(client, task_id, done=True)

        user_destination_text = str(destination or settings.get("upload_destination") or "Not Set")
        is_batch_task = str((get_task(task_id) or {}).get("mode", "")).strip().lower() == "batch"
        if not is_batch_task:
            await message.reply_text(
                auto_index_completed_text({
                    "batch_name": entry.get("file_name") or entry.get("content_type") or "Single Link Job",
                    "valid_links": 1,
                    "success": 1,
                    "failed": 0,
                    "destination": user_destination_text,
                    "index_no": idx_no,
                    "user_index_no": user_index_no,
                    "link_type": entry.get("link_type") or "unknown",
                }),
                disable_web_page_preview=True,
            )

        if delivery_errors and not is_batch_task:
            await message.reply_text("⚠️ Kuch targets par send fail hua:\n" + "\n".join(delivery_errors[:5]))

    finally:
        if disconnect_user_client and user_client:
            try:
                await user_client.disconnect()
            except Exception:
                pass
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except Exception:
                pass


async def _perform_transfer(client, user_id: int, message, link_text: str, task_id: str, settings: dict, destination):
    touch_task(task_id, {"status": "fetching", "current_stage": "fetching", "progress_text": "", "is_visible": False})
    await update_task_status_message(client, task_id)

    ensure_task_not_cancelled(task_id)
    source_msg, info, user_client, fetch_mode = await fetch_message_via_best_client(client, user_id, link_text)

    if not source_msg:
        raise RuntimeError("Source message fetch nahi ho paya. Public access ya authorized login required.")

    await process_source_message_transfer(
        client,
        user_id,
        message,
        source_msg,
        task_id,
        settings,
        destination,
        link_text,
        info=info,
        user_client=user_client,
        fetch_mode=fetch_mode,
        disconnect_user_client=True,
    )


async def process_link_task(client, user_id: int, message, link_text: str, batch_mode: bool = False, batch_key: str = "", batch_index: int = 0, batch_total: int = 0):
    await ensure_background_workers_started(client)

    info = extract_telegram_link_info(link_text)
    settings = get_user_settings(user_id)
    destination = normalize_target(settings.get("upload_destination", "")) or DEFAULT_DESTINATION or None

    checking_message = None
    if not batch_mode:
        try:
            checking_message = await message.reply_text(
                checking_text(link_text.strip()),
                disable_web_page_preview=True,
            )
        except Exception:
            checking_message = None

    if not destination:
        if batch_mode:
            return False
        await ask_set_destination(message, checking_message)
        return False

    if info and str(info.get("link_type") or "").lower() in {"private", "private_topic"} and not has_user_session(user_id):
        if batch_mode:
            return False
        await ask_login_for_private_link(message, checking_message)
        return False

    cleanup_stale_active_tasks()
    user_task_limit = get_user_task_limit(user_id)
    running_now = count_running_tasks(user_id)
    queue_now = TASK_QUEUE.qsize()

    if running_now >= user_task_limit:
        if batch_mode:
            return False
        warn = f"⚠️ Ek time par max {user_task_limit} running tasks allowed hain."
        await edit_or_reply(message, warn, checking_message)
        return False

    if (running_now + queue_now) >= GLOBAL_MAX_RUNNING_TASKS:
        if batch_mode:
            return False
        warn = "⚠️ Queue full hai. Thodi der baad try karo."
        await edit_or_reply(message, warn, checking_message)
        return False

    task_id = make_task_id()
    queue_position = TASK_QUEUE.qsize() + 1

    touch_task(task_id, {
        "task_id": task_id,
        "user_id": user_id,
        "source": link_text.strip(),
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
        "mode": "batch" if batch_mode else "single",
        "upload_mode": settings.get("upload_mode", "document"),
        "topic_id": str(settings.get("topic_id", "") or ""),
        "queue_position": queue_position,
        "status_chat_id": 0,
        "status_message_id": 0,
        "checking_chat_id": 0,
        "checking_message_id": 0,
        "pinned_ui": not batch_mode,
        "is_visible": False,
        "batch_key": str(batch_key or ""),
        "batch_index": int(batch_index or 0),
        "batch_total": int(batch_total or 0),
    })

    if batch_mode:
        _register_task_to_batch_board(user_id, task_id, batch_key, batch_index, batch_total, link_text.strip())
        await _refresh_batch_board_message(client, user_id)
        return task_id

    await create_task_status_message(message, task_id, checking_message=checking_message)

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


async def enqueue_direct_message_task(client, user_id: int, message):
    await ensure_background_workers_started(client)

    settings = get_user_settings(user_id)
    destination = normalize_target(settings.get("upload_destination", "")) or DEFAULT_DESTINATION or None

    if not destination:
        await ask_set_destination(message)
        return False

    cleanup_stale_active_tasks()
    user_task_limit = get_user_task_limit(user_id)
    running_now = count_running_tasks(user_id)
    queue_now = TASK_QUEUE.qsize()

    if running_now >= user_task_limit:
        await message.reply_text(f"⚠️ Ek time par max {user_task_limit} running tasks allowed hain.")
        return False

    if (running_now + queue_now) >= GLOBAL_MAX_RUNNING_TASKS:
        await message.reply_text("⚠️ Queue full hai. Thodi der baad try karo.")
        return False

    task_id = make_task_id()
    queue_position = TASK_QUEUE.qsize() + 1
    source_label = f"direct:{message.id}"

    touch_task(task_id, {
        "task_id": task_id,
        "user_id": user_id,
        "source": source_label,
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
        "mode": "single",
        "upload_mode": settings.get("upload_mode", "document"),
        "topic_id": str(settings.get("topic_id", "") or ""),
        "queue_position": queue_position,
        "status_chat_id": 0,
        "status_message_id": 0,
        "checking_chat_id": 0,
        "checking_message_id": 0,
        "pinned_ui": True,
        "is_visible": False,
        "batch_key": "",
        "batch_index": 0,
        "batch_total": 0,
    })

    checking_message = await message.reply_text(
        checking_text("Direct file received"),
        disable_web_page_preview=True,
    )
    await create_task_status_message(message, task_id, checking_message=checking_message)

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


async def process_batch_links(client, user_id: int, message, raw_text: str):
    links = parse_batch_links(raw_text)
    if not links:
        await message.reply_text("❌ Batch me koi valid Telegram links nahi mile.")
        return

    save_batch_input(user_id, raw_text)
    user_batch_limit = get_user_batch_limit(user_id)
    if len(links) > user_batch_limit:
        links = links[:user_batch_limit]

    board = await _open_batch_board(client, message, user_id, len(links), note="", batch_name=derive_batch_name(raw_text, links))
    batch_key = board.get("batch_key", "")

    success = 0
    failed = 0

    for idx, link in enumerate(links, start=1):
        task_id = await process_link_task(
            client,
            user_id,
            message,
            link,
            batch_mode=True,
            batch_key=batch_key,
            batch_index=idx,
            batch_total=len(links),
        )

        if not task_id:
            failed += 1
            await _refresh_batch_board_message(client, user_id, force_done=(idx == len(links) and success == 0))
            continue

        item = {
            "task_id": task_id,
            "user_id": user_id,
            "message": message,
            "link_text": link,
            "settings": get_user_settings(user_id),
            "destination": normalize_target(get_user_settings(user_id).get("upload_destination", "")) or DEFAULT_DESTINATION or None,
            "batch_mode": True,
        }

        touch_task(task_id, {
            "status": "processing",
            "current_stage": "processing",
            "progress_text": "",
            "queue_position": 0,
            "worker_id": 0,
            "is_visible": False,
        })
        await update_task_status_message(client, task_id, done=False)

        ok = await _run_task_attempts(client, item)
        if ok:
            success += 1
        else:
            failed += 1

        board = _get_batch_board(user_id)
        if board:
            board["current_index"] = idx
            board["current_task_id"] = ""
            _save_batch_board(user_id, board)
            await _refresh_batch_board_message(client, user_id, force_done=(idx == len(links)))

        if BATCH_DELAY > 0 and idx < len(links):
            await asyncio.sleep(BATCH_DELAY)

    board = _get_batch_board(user_id)
    if board:
        board["status"] = "Completed"
        board["current_task_id"] = ""
        _save_batch_board(user_id, board)
        await _refresh_batch_board_message(client, user_id, force_done=True)


async def start_login_client(user_id: int):
    login_client = Client(
        name=f"login_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
    await login_client.connect()
    TEMP_LOGIN_CLIENTS[user_id] = login_client
    return login_client


async def get_or_create_login_client(user_id: int):
    existing = TEMP_LOGIN_CLIENTS.get(user_id)
    if existing:
        return existing
    return await start_login_client(user_id)


async def cleanup_login_client(user_id: int):
    client_obj = TEMP_LOGIN_CLIENTS.pop(user_id, None)
    if client_obj:
        try:
            await client_obj.disconnect()
        except Exception:
            pass


async def begin_login_flow(user_id: int, phone: str):
    login_client = await get_or_create_login_client(user_id)
    sent = await login_client.send_code(phone)
    set_login_temp(user_id, "phone", phone)
    set_login_temp(user_id, "phone_code_hash", sent.phone_code_hash)
    set_user_state(user_id, "login_code")


async def finish_login_with_code(user_id: int, code: str):
    phone = get_login_temp(user_id, "phone", "")
    phone_code_hash = get_login_temp(user_id, "phone_code_hash", "")

    if not phone or not phone_code_hash:
        raise RuntimeError("Login session data missing. Dobara /login try karo.")

    login_client = await get_or_create_login_client(user_id)

    try:
        await login_client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=code,
        )
    except SessionPasswordNeeded:
        set_user_state(user_id, "login_password")
        raise

    me = await login_client.get_me()
    session_string = await login_client.export_session_string()
    save_user_session(user_id, session_string, tg_user_id=me.id, phone=phone)
    clear_login_temp(user_id)
    clear_user_state(user_id)
    await cleanup_login_client(user_id)
    return me, phone


async def finish_login_with_password(user_id: int, password: str):
    phone = get_login_temp(user_id, "phone", "")
    login_client = await get_or_create_login_client(user_id)
    await login_client.check_password(password=password)

    me = await login_client.get_me()
    session_string = await login_client.export_session_string()
    save_user_session(user_id, session_string, tg_user_id=me.id, phone=phone)
    clear_login_temp(user_id)
    clear_user_state(user_id)
    await cleanup_login_client(user_id)
    return me, phone


async def send_broadcast_to_user(client, uid: int, reply_msg, broadcast_text: str):
    if reply_msg:
        if reply_msg.photo:
            return await client.send_photo(uid, photo=reply_msg.photo.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.video:
            return await client.send_video(uid, video=reply_msg.video.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.document:
            return await client.send_document(uid, document=reply_msg.document.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.audio:
            return await client.send_audio(uid, audio=reply_msg.audio.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.voice:
            return await client.send_voice(uid, voice=reply_msg.voice.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.animation:
            return await client.send_animation(uid, animation=reply_msg.animation.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.text:
            return await client.send_message(uid, broadcast_text or reply_msg.text, disable_web_page_preview=True)
        raise RuntimeError("Unsupported broadcast reply message type.")

    if not broadcast_text:
        raise RuntimeError("Empty broadcast text.")

    return await client.send_message(uid, f"📢 **Code Devil Broadcast**\n\n{broadcast_text}", disable_web_page_preview=True)


async def handle_admin_commands(client, message, lowered: str):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return False

    if lowered.startswith("/stats"):
        recent = get_recent_users(5)
        recent_text = "\n".join([f"• {u.get('first_name') or 'User'} ({u.get('id')})" for u in recent]) or "No recent users"
        await message.reply_text(
            "📊 **Bot Stats**\n\n"
            f"**Total Users:** {user_count()}\n"
            f"**Banned Users:** {banned_count()}\n"
            f"**Admins:** {len(ADMIN_IDS) + 1}\n\n"
            f"**Recent Users:**\n{recent_text}"
        )
        return True

    if lowered.startswith("/users"):
        recent = get_recent_users(15)
        if not recent:
            await message.reply_text("Abhi tak koi user data nahi mila.")
            return True
        text = "👥 **Recent Users**\n\n" + "\n".join(
            [f"• {u.get('first_name') or 'User'} | `{u.get('id')}` | @{u.get('username') or 'no_username'}" for u in recent]
        )
        await message.reply_text(text)
        return True

    if lowered.startswith("/premium_status"):
        parts = (message.text or "").split(maxsplit=1)
        target = user_id
        if len(parts) > 1 and parts[1].strip().isdigit():
            target = int(parts[1].strip())
        expiry = get_premium_expiry_text(target) or "No expiry"
        status = "Premium 💎" if is_premium_user(target) else "Free 🆓"
        await message.reply_text(f"User `{target}`\nStatus: **{status}**\nExpiry: `{expiry}`")
        return True

    if lowered.startswith("/add_premium"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /add_premium user_id 30d")
            return True
        target = int(parts[1])
        duration = parts[2]
        record = add_premium(target, duration, granted_by=user_id)
        await message.reply_text(
            f"✅ Premium added\nUser: `{target}`\nExpiry: `{record.get('premium_expires_at') or 'No expiry'}`"
        )
        return True

    if lowered.startswith("/remove_premium"):
        parts = (message.text or "").split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply_text("Use: /remove_premium user_id")
            return True
        target = int(parts[1])
        remove_premium(target)
        await message.reply_text(f"✅ Premium removed for `{target}`")
        return True

    if lowered.startswith("/ban"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text("Use: /ban user_id")
            return True
        target = int(parts[1].strip())
        if target == OWNER_ID:
            await message.reply_text("Owner ko ban nahi kar sakte.")
            return True
        ban_user(target)
        await message.reply_text(f"🚫 User `{target}` ko ban kar diya gaya.")
        return True

    if lowered.startswith("/unban"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text("Use: /unban user_id")
            return True
        target = int(parts[1].strip())
        unban_user(target)
        await message.reply_text(f"✅ User `{target}` ko unban kar diya gaya.")
        return True

    if lowered.startswith("/broadcast"):
        users = get_recent_users(100000)
        sent = 0
        failed = 0
        status = await message.reply_text("📢 Broadcast start ho raha hai...")

        broadcast_text = ""
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) > 1:
            broadcast_text = parts[1].strip()

        reply_msg = message.reply_to_message

        for u in users:
            uid = u.get("id")
            if not uid or is_banned(uid):
                continue

            try:
                await send_broadcast_to_user(client, uid, reply_msg, broadcast_text)
                sent += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await send_broadcast_to_user(client, uid, reply_msg, broadcast_text)
                    sent += 1
                except Exception:
                    failed += 1
            except Exception:
                failed += 1

        await status.edit_text(f"📢 **Broadcast Complete**\n\n✅ Sent: {sent}\n❌ Failed: {failed}")
        return True

    if lowered.startswith("/index_id"):
        set_index_mode(user_id, True)
        await message.reply_text(index_started_text(user_id))
        return True

    if lowered.startswith("/stop_index"):
        set_index_mode(user_id, False)
        await message.reply_text(index_stopped_text(user_id))
        return True

    if lowered.startswith("/index_stats"):
        await message.reply_text(index_stats_text(user_id))
        return True

    return False


@app.on_callback_query()
async def all_callbacks(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    blocked = await check_force_sub(client, callback_query.message)
    if blocked:
        await callback_query.answer("Pehle required channel join karo.", show_alert=True)
        return

    if is_banned(user_id):
        await callback_query.answer("🚫 Aap bot use nahi kar sakte.", show_alert=True)
        return

    cleanup_expired_premium_users()
    s = get_user_settings(user_id)

    if data == "noop":
        await callback_query.answer()
        return

    if data.startswith("batch_refresh:"):
        await _refresh_batch_board_message(client, user_id)
        await callback_query.answer("♻️ Refreshed")
        return

    if data.startswith("batch_close:"):
        await _close_batch_board(client, user_id)
        await callback_query.answer("Closed")
        return

    if data.startswith("batch_cancel_current:"):
        board = _get_batch_board(user_id)
        current_task_id = str((board or {}).get("current_task_id") or "").strip()
        if current_task_id:
            touch_task(current_task_id, {"status": "cancelled", "current_stage": "cancelled", "error": "Cancelled by user"})
            await _refresh_batch_board_message(client, user_id)
            await callback_query.answer(f"Cancelled {current_task_id}")
        else:
            await callback_query.answer("No running task", show_alert=True)
        return

    if data == "clear_finished_tasks":
        removed = 0
        for task in get_user_tasks(user_id, limit=1000):
            if task.get("status") in {"completed", "failed", "cancelled"}:
                delete_task(task.get("id"))
                removed += 1
        await callback_query.answer(f"🧹 Cleared: {removed}")
        return

    if data.startswith("task_debug:"):
        task_id = data.split(":", 1)[1]
        task = get_task(task_id) or {}
        debug_text = (
            "🧪 **Task Debug**\n\n"
            f"ID: `{task.get('id', task_id)}`\n"
            f"Status: `{task.get('status', 'unknown')}`\n"
            f"Source: `{task.get('source', '')}`\n"
            f"Destination: `{task.get('destination_display') or task.get('destination') or 'Not Set'}`\n"
            f"Topic: `{task.get('topic_id') or 'None'}`\n"
            f"Mode: `{task.get('upload_mode') or task.get('mode') or 'unknown'}`\n"
            f"Retries: `{task.get('retry_count', task.get('retries', 0))}`\n"
            f"Error: `{task.get('error', '') or 'None'}`"
        )
        try:
            await callback_query.message.reply_text(debug_text, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("🧪 Debug shown")
        return

    if data == "show_user_limits":
        await callback_query.answer(
            f"Tasks: {get_user_task_limit(user_id)} | Batch: {get_user_batch_limit(user_id)}",
            show_alert=True,
        )
        return

    if data in {"admin_broadcast_help", "admin_recent_users", "admin_logs_summary", "admin_task_debug_help", "admin_destination_help", "show_batch_info"}:
        if data.startswith("admin_") and not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        help_map = {
            "admin_broadcast_help": "📢 Broadcast help\n\nUse: /broadcast your message\nYa kisi media/text par reply karke /broadcast bhejo.",
            "admin_recent_users": "👥 Recent users\n\n/users command use karo ya admin panel ka users section kholo.",
            "admin_logs_summary": "🧾 Logs summary\n\nLog channel aur runtime console logs se detailed status check karo.",
            "admin_task_debug_help": "🧪 Task debug help\n\nTask card ke refresh/cancel buttons use karo. Debug task button raw state dikhata hai.",
            "admin_destination_help": "📌 Destination help\n\nDestination me chat id ya @channelusername set karo. Topic ID optional hai.",
            "show_batch_info": "📦 Batch info\n\nSingle links, multiple links, aur range links dono supported hain.",
        }
        try:
            await callback_query.message.reply_text(help_map[data], disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data in {"clear_topic_id", "remove_topic_id"}:
        update_user_settings(user_id, {"topic_id": ""})
        text = topic_id_text(user_id)
        kb = simple_set_buttons("set_topic_id", "remove_topic_id")
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("🧹 Topic cleared")
        return

    if data in {"clear_destination", "remove_destination"}:
        update_user_settings(user_id, {"upload_destination": ""})
        text = destination_text(user_id)
        kb = simple_set_buttons("set_destination", "remove_destination")
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("🧹 Destination cleared")
        return

    if data.startswith("set_upload_mode:"):
        new_mode = data.split(":", 1)[1].strip().lower()
        if new_mode not in {"media", "document"}:
            new_mode = "document"
        update_user_settings(user_id, {"upload_mode": new_mode})
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("✅ Upload mode updated")
        return

    if data == "toggle_replace_words":
        await callback_query.answer("✍️ Rules set/clear se manage karo")
        return

    if data == "clear_replace_words":
        update_user_settings(user_id, {"replace_words": ""})
        text = replace_words_text(user_id)
        kb = simple_set_buttons("set_replace_words", "remove_replace_words")
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("🧹 Rules cleared")
        return

    if data.startswith("task_refresh:"):
        task_id = data.split(":", 1)[1]
        task = get_task(task_id) or {}
        await update_task_status_message(client, task_id, done=task.get("status") in {"completed", "failed", "cancelled"})
        await callback_query.answer("♻️ Refreshed")
        return

    if data.startswith("task_cancel:"):
        task_id = data.split(":", 1)[1]
        task = get_task(task_id)
        if task:
            touch_task(task_id, {"status": "cancelled", "error": "Cancelled by user"})
            await update_task_status_message(client, task_id, done=True)
        await callback_query.answer("🛑 Cancelled")
        return

    if data == "show_premium_info":
        try:
            await callback_query.message.edit_text(
                premium_info_text(user_id),
                reply_markup=premium_info_buttons(is_admin(user_id)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_admin_panel":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        try:
            await callback_query.message.edit_text(
                admin_panel_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "admin_premium_help":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        try:
            await callback_query.message.edit_text(
                admin_premium_help_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_admin_users":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        recent = get_recent_users(15)
        text = "👥 **Recent Users**\n\n" + ("\n".join([f"• {u.get('first_name') or 'User'} | `{u.get('id')}` | @{u.get('username') or 'no_username'}" for u in recent]) if recent else "No users")
        try:
            await callback_query.message.edit_text(text, reply_markup=admin_panel_buttons(), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_my_tasks":
        tasks = get_user_tasks(user_id, limit=10)
        try:
            await callback_query.message.edit_text(my_tasks_text(tasks), reply_markup=my_tasks_buttons(include_cleanup=True), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_login_info":
        try:
            await callback_query.message.edit_text(login_intro_text(), reply_markup=login_buttons(has_user_session(user_id)), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_login_status":
        try:
            await callback_query.message.edit_text(login_status_text(user_id), reply_markup=login_buttons(has_user_session(user_id)), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "start_login_flow":
        set_user_state(user_id, "login_phone")
        await callback_query.message.reply_text("📱 Ab apna phone number international format me bhejo.\nExample: +91xxxxxxxxxx\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    if data == "do_logout":
        if has_user_session(user_id):
            delete_user_session(user_id)
            clear_login_temp(user_id)
            await cleanup_login_client(user_id)
            try:
                await callback_query.message.edit_text(logout_success_text(), reply_markup=login_buttons(False), disable_web_page_preview=True)
            except Exception:
                pass
        else:
            try:
                await callback_query.message.edit_text(logout_missing_text(), reply_markup=login_buttons(False), disable_web_page_preview=True)
            except Exception:
                pass
        await callback_query.answer()
        return

    if data == "show_settings_home":
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "show_upload_mode":
        text = build_upload_mode_message(user_id)
        kb = submenu_nav()

    elif data == "toggle_upload_mode":
        current = str(s.get("upload_mode", "media") or "media").strip().lower()
        new_mode = "document" if current == "media" else "media"
        update_user_settings(user_id, {"upload_mode": new_mode})
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "show_thumbnail":
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(s["thumbnail_enabled"])

    elif data == "toggle_thumbnail_enabled":
        s["thumbnail_enabled"] = not s["thumbnail_enabled"]
        update_user_settings(user_id, s)
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(s["thumbnail_enabled"])

    elif data == "set_thumbnail_photo":
        set_user_state(user_id, "set_thumbnail_photo")
        await callback_query.message.reply_text("🖼 Ab ek photo bhejo jise custom thumbnail save karna hai.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_thumbnail":
        update_user_settings(user_id, {"thumbnail_file_id": "", "thumbnail_enabled": False})
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(False)

    elif data == "show_caption":
        text = caption_text(user_id)
        kb = caption_buttons(s["caption_enabled"])

    elif data == "toggle_caption_enabled":
        s["caption_enabled"] = not s["caption_enabled"]
        update_user_settings(user_id, s)
        text = caption_text(user_id)
        kb = caption_buttons(s["caption_enabled"])

    elif data == "show_caption_index_settings":
        text = caption_text(user_id)
        kb = caption_index_buttons(s.get("caption_index_enabled", True))

    elif data == "toggle_caption_index_enabled":
        s["caption_index_enabled"] = not s.get("caption_index_enabled", True)
        update_user_settings(user_id, s)
        text = caption_text(user_id)
        kb = caption_index_buttons(s.get("caption_index_enabled", True))

    elif data == "set_caption_index_padding":
        set_user_state(user_id, "set_caption_index_padding")
        await callback_query.message.reply_text("🔢 Ab caption index padding bhejo.\nExample: 2\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_caption_index_start":
        set_user_state(user_id, "set_caption_index_start")
        await callback_query.message.reply_text("🚀 Ab caption index start value bhejo.\nExample: 1\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_caption_text":
        set_user_state(user_id, "set_caption_text")
        await callback_query.message.reply_text("📝 Ab custom caption bhejo.\n{index} use kar sakte ho.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_caption":
        update_user_settings(user_id, {"caption_text": "", "caption_enabled": False})
        text = caption_text(user_id)
        kb = caption_buttons(False)

    elif data == "show_prefix":
        text = prefix_text(user_id)
        kb = simple_set_buttons("set_prefix", "remove_prefix")

    elif data == "set_prefix":
        set_user_state(user_id, "set_prefix")
        await callback_query.message.reply_text("🏷 Ab prefix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_prefix":
        update_user_settings(user_id, {"prefix": ""})
        text = prefix_text(user_id)
        kb = simple_set_buttons("set_prefix", "remove_prefix")

    elif data == "show_suffix":
        text = suffix_text(user_id)
        kb = simple_set_buttons("set_suffix", "remove_suffix")

    elif data == "set_suffix":
        set_user_state(user_id, "set_suffix")
        await callback_query.message.reply_text("🔖 Ab suffix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_suffix":
        update_user_settings(user_id, {"suffix": ""})
        text = suffix_text(user_id)
        kb = simple_set_buttons("set_suffix", "remove_suffix")

    elif data == "show_auto_rename":
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(s.get("auto_rename_enabled", False))

    elif data == "toggle_auto_rename_enabled":
        s["auto_rename_enabled"] = not s.get("auto_rename_enabled", False)
        update_user_settings(user_id, s)
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(s.get("auto_rename_enabled", False))

    elif data == "set_auto_rename":
        set_user_state(user_id, "set_auto_rename")
        await callback_query.message.reply_text("✍️ Ab simple auto rename value bhejo.\n{index} aur {filename} use kar sakte ho.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_rename_template":
        set_user_state(user_id, "set_rename_template")
        await callback_query.message.reply_text("🧩 Ab rename template bhejo.\nExample: Movie_{index}\nYa: {index}_{filename}\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_filename_prefix":
        set_user_state(user_id, "set_filename_prefix")
        await callback_query.message.reply_text("🏷 Ab filename prefix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_filename_suffix":
        set_user_state(user_id, "set_filename_suffix")
        await callback_query.message.reply_text("🔖 Ab filename suffix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "show_filename_index_settings":
        text = auto_rename_text(user_id)
        kb = filename_index_buttons(s.get("filename_index_enabled", False))

    elif data == "toggle_filename_index_enabled":
        s["filename_index_enabled"] = not s.get("filename_index_enabled", False)
        update_user_settings(user_id, s)
        text = auto_rename_text(user_id)
        kb = filename_index_buttons(s.get("filename_index_enabled", False))

    elif data == "set_filename_index_padding":
        set_user_state(user_id, "set_filename_index_padding")
        await callback_query.message.reply_text("🔢 Ab filename index padding bhejo.\nExample: 2\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_filename_index_start":
        set_user_state(user_id, "set_filename_index_start")
        await callback_query.message.reply_text("🚀 Ab filename index start value bhejo.\nExample: 1\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_auto_rename":
        update_user_settings(user_id, {"auto_rename": "", "rename_template": "", "filename_prefix": "", "filename_suffix": "", "auto_rename_enabled": False, "filename_index_enabled": False})
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(False)

    elif data == "show_destination":
        text = destination_text(user_id)
        kb = simple_set_buttons("set_destination", "remove_destination")

    elif data == "set_destination":
        set_user_state(user_id, "set_destination")
        await callback_query.message.reply_text("📍 Ab upload destination bhejo.\nChat ID ya @channelusername format me.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_destination":
        update_user_settings(user_id, {"upload_destination": ""})
        text = destination_text(user_id)
        kb = simple_set_buttons("set_destination", "remove_destination")

    elif data == "show_topic_id":
        text = topic_id_text(user_id)
        kb = simple_set_buttons("set_topic_id", "remove_topic_id")

    elif data == "set_topic_id":
        set_user_state(user_id, "set_topic_id")
        await callback_query.message.reply_text("🧵 Ab topic id bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_topic_id":
        update_user_settings(user_id, {"topic_id": ""})
        text = topic_id_text(user_id)
        kb = simple_set_buttons("set_topic_id", "remove_topic_id")

    elif data == "show_replace_words":
        text = replace_words_text(user_id)
        kb = simple_set_buttons("set_replace_words", "remove_replace_words")

    elif data == "set_replace_words":
        set_user_state(user_id, "set_replace_words")
        await callback_query.message.reply_text("🔁 Ab remove/replace rules bhejo.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_replace_words":
        update_user_settings(user_id, {"replace_words": ""})
        text = replace_words_text(user_id)
        kb = simple_set_buttons("set_replace_words", "remove_replace_words")

    elif data == "show_metadata":
        text = metadata_home_text(user_id)
        kb = metadata_buttons(s["metadata_enabled"])

    elif data == "toggle_metadata_enabled":
        s["metadata_enabled"] = not s["metadata_enabled"]
        update_user_settings(user_id, s)
        text = metadata_home_text(user_id)
        kb = metadata_buttons(s["metadata_enabled"])

    elif data == "show_metadata_video_title":
        text = metadata_field_text(user_id, "Video Title", "metadata_video_title")
        kb = metadata_field_buttons("set_metadata_video_title", "remove_metadata_video_title")

    elif data == "set_metadata_video_title":
        set_user_state(user_id, "set_metadata_video_title")
        await callback_query.message.reply_text("🎬 Ab Video Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_metadata_video_title":
        update_user_settings(user_id, {"metadata_video_title": ""})
        text = metadata_field_text(user_id, "Video Title", "metadata_video_title")
        kb = metadata_field_buttons("set_metadata_video_title", "remove_metadata_video_title")

    elif data == "show_metadata_video_author":
        text = metadata_field_text(user_id, "Video Author", "metadata_video_author")
        kb = metadata_field_buttons("set_metadata_video_author", "remove_metadata_video_author")

    elif data == "set_metadata_video_author":
        set_user_state(user_id, "set_metadata_video_author")
        await callback_query.message.reply_text("👤 Ab Video Author bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_metadata_video_author":
        update_user_settings(user_id, {"metadata_video_author": ""})
        text = metadata_field_text(user_id, "Video Author", "metadata_video_author")
        kb = metadata_field_buttons("set_metadata_video_author", "remove_metadata_video_author")

    elif data == "show_metadata_audio_title":
        text = metadata_field_text(user_id, "Audio Title", "metadata_audio_title")
        kb = metadata_field_buttons("set_metadata_audio_title", "remove_metadata_audio_title")

    elif data == "set_metadata_audio_title":
        set_user_state(user_id, "set_metadata_audio_title")
        await callback_query.message.reply_text("🎵 Ab Audio Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_metadata_audio_title":
        update_user_settings(user_id, {"metadata_audio_title": ""})
        text = metadata_field_text(user_id, "Audio Title", "metadata_audio_title")
        kb = metadata_field_buttons("set_metadata_audio_title", "remove_metadata_audio_title")

    elif data == "show_metadata_subtitle_title":
        text = metadata_field_text(user_id, "Subtitle Title", "metadata_subtitle_title")
        kb = metadata_field_buttons("set_metadata_subtitle_title", "remove_metadata_subtitle_title")

    elif data == "set_metadata_subtitle_title":
        set_user_state(user_id, "set_metadata_subtitle_title")
        await callback_query.message.reply_text("💬 Ab Subtitle Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_metadata_subtitle_title":
        update_user_settings(user_id, {"metadata_subtitle_title": ""})
        text = metadata_field_text(user_id, "Subtitle Title", "metadata_subtitle_title")
        kb = metadata_field_buttons("set_metadata_subtitle_title", "remove_metadata_subtitle_title")

    elif data == "show_index_settings":
        text = index_info_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == "toggle_index_mode":
        current = is_index_mode(user_id)
        set_index_mode(user_id, not current)
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "show_index_stats":
        text = index_stats_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == "show_index_info":
        text = index_info_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == "show_batch_settings":
        text = batch_text(user_id)
        kb = batch_buttons(is_batch_mode(user_id), is_premium_user(user_id))

    elif data == "toggle_batch_mode":
        set_batch_mode(user_id, not is_batch_mode(user_id))
        text = batch_text(user_id)
        kb = batch_buttons(is_batch_mode(user_id), is_premium_user(user_id))

    elif data == "set_batch_links":
        set_user_state(user_id, "set_batch_links")
        await callback_query.message.reply_text("📥 Ab multiple Telegram links bhejo.\nRange format bhi de sakte ho like:\nhttps://t.me/channel/39-69\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "clear_batch_links":
        save_batch_input(user_id, "")
        text = batch_text(user_id)
        kb = batch_buttons(is_batch_mode(user_id), is_premium_user(user_id))

    elif data == "start_batch_now":
        batch_input = get_batch_input(user_id)
        await callback_query.answer("Batch start ho raha hai...")
        await process_batch_links(client, user_id, callback_query.message, batch_input)
        return

    elif data == "reset_all_settings":
        reset_user_settings(user_id)
        clear_user_state(user_id)
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "close_settings":
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        await callback_query.answer("Closed")
        return

    else:
        await callback_query.answer("Unknown action")
        return

    try:
        await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass

    await callback_query.answer("✅ Updated")


@app.on_message(filters.private)
async def catch_all(client, message):
    register_user(message.from_user)
    user_id = message.from_user.id
    cleanup_expired_premium_users()

    blocked = await check_force_sub(client, message)
    if blocked:
        return

    if is_banned(user_id):
        await message.reply_text("🚫 Aapko is bot se ban kiya gaya hai.")
        return

    text_raw = message.text or message.caption or ""
    text = text_raw.strip()
    lowered = text.lower()
    state = get_user_state(user_id)

    if lowered.startswith("/login"):
        if has_user_session(user_id):
            await message.reply_text(login_status_text(user_id), reply_markup=login_buttons(True))
            return
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        set_user_state(user_id, "login_phone")
        await message.reply_text(ask_phone_text())
        return

    if state == "login_phone" and not lowered.startswith("/"):
        phone = text.replace(" ", "")
        try:
            await begin_login_flow(user_id, phone)
            await message.reply_text(ask_code_text())
            return
        except PhoneNumberInvalid:
            await message.reply_text(login_failed_text("Invalid phone number."))
            return
        except FloodWait as e:
            await message.reply_text(login_failed_text(f"FloodWait: {e.value}s"))
            return
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return

    if state == "login_code" and not lowered.startswith("/"):
        code = text.replace(" ", "")
        try:
            me, phone = await finish_login_with_code(user_id, code)
            await message.reply_text(login_success_text(phone))
            return
        except SessionPasswordNeeded:
            await message.reply_text(ask_password_text())
            return
        except PhoneCodeInvalid:
            await message.reply_text(login_failed_text("Invalid OTP / code."))
            return
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return

    if state == "login_password" and not lowered.startswith("/"):
        try:
            me, phone = await finish_login_with_password(user_id, text)
            await message.reply_text(login_success_text(phone))
            return
        except PasswordHashInvalid:
            await message.reply_text(login_failed_text("Wrong password."))
            return
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return

    if state == "set_batch_links" and not lowered.startswith("/"):
        save_batch_input(user_id, text_raw)
        clear_user_state(user_id)
        await message.reply_text("✅ Batch links save ho gaye.\n/settings me Batch section se Start Batch chala sakte ho.")
        return

    ignored_cmds = (
        "/stop_index",
        "/index_stats",
        "/index_id",
        "/settings",
        "/cancel",
        "/start",
        "/help",
        "/plan",
        "/terms",
        "/ping",
        "/login",
        "/login_status",
        "/logout",
        "/my_tasks",
    )

    if not any(lowered.startswith(cmd) for cmd in ignored_cmds):
        if is_batch_mode(user_id):
            links = parse_batch_links(text_raw)
            normalized_text = str(text_raw or "").strip()
            token_count = len([part for part in normalized_text.split() if part.strip()])
            is_range_input = bool(re.search(r"https?://(?:t|telegram)\.me/\S+?-\d+", normalized_text))
            if links and (len(links) > 1 or token_count > 1 or is_range_input or "\n" in normalized_text):
                await process_batch_links(client, user_id, message, text_raw)
                return

        info = extract_telegram_link_info(text_raw)
        if info:
            await process_link_task(client, user_id, message, text_raw.strip())
            return

    if not state and is_media_message(message):
        await enqueue_direct_message_task(client, user_id, message)
        return

    if state and not lowered.startswith("/cancel"):
        setting_key = WAITING_KEYS.get(state)

        if setting_key == "thumbnail_file_id":
            if message.photo:
                update_user_settings(user_id, {"thumbnail_file_id": message.photo.file_id, "thumbnail_enabled": True})
                clear_user_state(user_id)
                await message.reply_text("✅ Custom thumbnail save ho gaya.\n\n/settings bhejo dekhne ke liye.")
                return
            await message.reply_text("❌ Thumbnail ke liye photo bhejna zaroori hai. /cancel bhej kar cancel kar sakte ho.")
            return

        if setting_key:
            value = text
            if setting_key in {"caption_index_padding", "caption_index_start", "filename_index_padding", "filename_index_start"}:
                if not value.isdigit():
                    await message.reply_text("❌ Yahan sirf number bhejo.\n/cancel bhej kar cancel kar sakte ho.")
                    return
                value = int(value)

            if setting_key == "topic_id" and value and not value.lstrip("-").isdigit():
                await message.reply_text("❌ Topic ID sirf number hona chahiye.\n/cancel bhej kar cancel kar sakte ho.")
                return

            update_user_settings(user_id, {setting_key: value})

            if setting_key == "caption_text":
                update_user_settings(user_id, {"caption_enabled": True})
            if setting_key in {"auto_rename", "rename_template", "filename_prefix", "filename_suffix"}:
                update_user_settings(user_id, {"auto_rename_enabled": True})
            if setting_key.startswith("metadata_"):
                update_user_settings(user_id, {"metadata_enabled": True})

            clear_user_state(user_id)
            await message.reply_text(f"✅ `{setting_key.replace('_', ' ').title()}` update ho gaya.\n\n/settings bhejo dekhne ke liye.")
            return

    if await handle_admin_commands(client, message, lowered):
        return

    if lowered.startswith("/cancel"):
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        await message.reply_text("❌ Current input mode cancel kar diya gaya.")
        return

    if lowered.startswith("/ping"):
        await message.reply_text("✅ Bot online hai aur sahi se reply kar raha hai.")
        return

    if lowered.startswith("/start"):
        reset_user_index_counter(user_id)
        await message.reply_text(
            start_text() + "\n\n🔄 Tumhara current user index reset ho gaya hai. Ab next item `01` se start hoga.",
            reply_markup=build_start_markup(user_id),
            disable_web_page_preview=True,
        )
        return

    if lowered.startswith("/help"):
        await message.reply_text(help_text())
        return

    if lowered.startswith("/plan"):
        await message.reply_text(plan_text())
        return

    if lowered.startswith("/terms"):
        await message.reply_text(terms_text())
        return

    if lowered.startswith("/settings"):
        await message.reply_text(
            settings_home_text(user_id),
            reply_markup=build_settings_home_markup(user_id),
            disable_web_page_preview=True,
        )
        return

    if lowered.startswith("/login_status"):
        await message.reply_text(login_status_text(user_id), reply_markup=login_buttons(has_user_session(user_id)))
        return

    if lowered.startswith("/logout"):
        if has_user_session(user_id):
            delete_user_session(user_id)
            clear_login_temp(user_id)
            await cleanup_login_client(user_id)
            await message.reply_text(logout_success_text(), reply_markup=login_buttons(False))
        else:
            await message.reply_text(logout_missing_text(), reply_markup=login_buttons(False))
        return

    if lowered.startswith("/my_tasks"):
        tasks = get_user_tasks(user_id, limit=10)
        await message.reply_text(my_tasks_text(tasks), reply_markup=my_tasks_buttons(include_cleanup=True), disable_web_page_preview=True)
        return

    await message.reply_text(unknown_text())
