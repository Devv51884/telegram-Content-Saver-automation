from __future__ import annotations

import os
import re
import uuid
import time
import asyncio
import tempfile
import subprocess
import importlib.util
import sys
import site
from pathlib import Path
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
    advanced_settings_buttons,
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
    upload_mode_buttons,
    storage_mode_buttons,
    replace_words_buttons,
    gdrive_buttons,
    rclone_buttons,
    personal_bot_buttons,
    route_template_buttons,
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
    advanced_settings_text,
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
    admin_plan_help_text,
    gdrive_text,
    rclone_text,
    personal_bot_text,
    route_template_text,
    admin_stats_text,
    all_users_text,
    batch_analysis_text,
    id_info_text,
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
    get_user_plan_name,
    get_user_plan_features,
    set_user_plan_name,
    set_user_plan_features,
    cleanup_expired_premium_users,
    cleanup_stale_active_tasks,
    delete_task,
    get_all_users_page,
    get_detailed_stats,
    analyze_batch_input,
    save_user_limit_record,
    get_user_allowed_storage_modes,
    user_can_use_storage_mode,
    get_user_storage_mode,
    get_user_telegram_upload_mode,
)

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

TEMP_LOGIN_CLIENTS = {}
IGNORED_DIRECT_MESSAGES: dict[int, dict[int, float]] = {}
IGNORED_DIRECT_SIGNATURES: dict[int, dict[str, dict[str, float | int]]] = {}
RELAY_BRIDGE_WAITERS: dict[int, dict[str, list[asyncio.Future]]] = {}
TARGET_ACCESS_CACHE: dict[tuple[int, str, str], dict] = {}
TARGET_PEER_READY_CACHE: dict[tuple[int, str], float] = {}

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
TARGET_ACCESS_CACHE_TTL = float(getattr(cfg, "TARGET_ACCESS_CACHE_TTL", 45.0) or 45.0)
TARGET_PEER_READY_TTL = float(getattr(cfg, "TARGET_PEER_READY_TTL", 90.0) or 90.0)

TASK_QUEUE: asyncio.Queue = asyncio.Queue()
TASK_WORKERS = []
TASK_WORKERS_STARTED = False
TASK_WORKER_LOCK = None


def ensure_shared_user_site_packages():
    candidates = []
    try:
        user_site = site.getusersitepackages()
        if user_site:
            candidates.append(user_site)
    except Exception:
        pass
    appdata = str(os.environ.get("APPDATA", "") or "").strip()
    if appdata:
        candidates.append(os.path.join(appdata, "Python", f"Python{sys.version_info.major}{sys.version_info.minor}", "site-packages"))

    for candidate in candidates:
        candidate = str(candidate or "").strip()
        if candidate and os.path.isdir(candidate) and candidate not in sys.path:
            sys.path.append(candidate)


ensure_shared_user_site_packages()


def now_iso() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def mark_ignored_direct_message(user_id: int, message_id: int, ttl_seconds: float = 180.0):
    user_id = int(user_id or 0)
    message_id = int(message_id or 0)
    if not user_id or not message_id:
        return
    expiry = time.time() + float(ttl_seconds or 180.0)
    ignored = IGNORED_DIRECT_MESSAGES.setdefault(user_id, {})
    ignored[message_id] = expiry


def should_ignore_direct_message(user_id: int, message_id: int) -> bool:
    user_id = int(user_id or 0)
    message_id = int(message_id or 0)
    if not user_id or not message_id:
        return False

    ignored = IGNORED_DIRECT_MESSAGES.get(user_id) or {}
    if not ignored:
        return False

    now = time.time()
    expired = [mid for mid, expiry in ignored.items() if expiry <= now]
    for mid in expired:
        ignored.pop(mid, None)

    should_ignore = bool(ignored.pop(message_id, None))
    if not ignored:
        IGNORED_DIRECT_MESSAGES.pop(user_id, None)
    return should_ignore


def get_message_media_kind(source_msg) -> str:
    if not source_msg:
        return ""
    for media in ("photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"):
        if getattr(source_msg, media, None):
            return media
    if str(getattr(source_msg, "text", "") or "").strip():
        return "text"
    if str(getattr(source_msg, "caption", "") or "").strip():
        return "caption"
    return str(getattr(source_msg, "media", "") or "").strip().lower()


def get_message_unique_id(source_msg) -> str:
    if not source_msg:
        return ""
    for media in ("photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"):
        obj = getattr(source_msg, media, None)
        if not obj:
            continue
        unique_id = getattr(obj, "file_unique_id", None)
        if unique_id:
            return str(unique_id)
        file_id = getattr(obj, "file_id", None)
        if file_id:
            return str(file_id)
    return ""


def build_message_relay_signature(source_msg) -> str:
    if not source_msg:
        return ""
    media_kind = get_message_media_kind(source_msg)
    unique_id = get_message_unique_id(source_msg)
    file_size = str(get_message_file_size(source_msg) or "")
    duration = str(get_message_duration(source_msg) or "")
    text_value = str(getattr(source_msg, "caption", None) or getattr(source_msg, "text", None) or "").strip()
    text_value = text_value[:120]
    return "|".join([media_kind, unique_id, file_size, duration, text_value])


def mark_ignored_direct_signature(user_id: int, source_msg, ttl_seconds: float = 180.0):
    user_id = int(user_id or 0)
    signature = build_message_relay_signature(source_msg)
    if not user_id or not signature:
        return

    expiry = time.time() + float(ttl_seconds or 180.0)
    user_signatures = IGNORED_DIRECT_SIGNATURES.setdefault(user_id, {})
    item = user_signatures.get(signature) or {"count": 0, "expiry": expiry}
    item["count"] = int(item.get("count", 0) or 0) + 1
    item["expiry"] = max(float(item.get("expiry", expiry) or expiry), expiry)
    user_signatures[signature] = item


def should_ignore_direct_message_payload(user_id: int, message) -> bool:
    if should_ignore_direct_message(user_id, getattr(message, "id", 0)):
        return True

    user_id = int(user_id or 0)
    if not user_id:
        return False

    user_signatures = IGNORED_DIRECT_SIGNATURES.get(user_id) or {}
    if not user_signatures:
        return False

    now = time.time()
    expired = [signature for signature, item in user_signatures.items() if float(item.get("expiry", 0) or 0) <= now]
    for signature in expired:
        user_signatures.pop(signature, None)

    signature = build_message_relay_signature(message)
    item = user_signatures.get(signature)
    if not item:
        if not user_signatures:
            IGNORED_DIRECT_SIGNATURES.pop(user_id, None)
        return False

    count = int(item.get("count", 0) or 0)
    if count <= 1:
        user_signatures.pop(signature, None)
    else:
        item["count"] = count - 1
        user_signatures[signature] = item

    if not user_signatures:
        IGNORED_DIRECT_SIGNATURES.pop(user_id, None)
    return True


def _cleanup_relay_waiters(user_id: int, signature: str):
    user_id = int(user_id or 0)
    signature = str(signature or "").strip()
    if not user_id or not signature:
        return
    user_waiters = RELAY_BRIDGE_WAITERS.get(user_id) or {}
    waiters = [future for future in (user_waiters.get(signature) or []) if future and not future.done()]
    if waiters:
        user_waiters[signature] = waiters
        RELAY_BRIDGE_WAITERS[user_id] = user_waiters
        return
    user_waiters.pop(signature, None)
    if user_waiters:
        RELAY_BRIDGE_WAITERS[user_id] = user_waiters
    else:
        RELAY_BRIDGE_WAITERS.pop(user_id, None)


def create_relay_bridge_waiter(user_id: int, source_msg):
    user_id = int(user_id or 0)
    signature = build_message_relay_signature(source_msg)
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    user_waiters = RELAY_BRIDGE_WAITERS.setdefault(user_id, {})
    waiters = user_waiters.setdefault(signature, [])
    waiters.append(future)
    return signature, future


def capture_relay_bridge_message(user_id: int, message) -> bool:
    user_id = int(user_id or 0)
    if not user_id:
        return False
    signature = build_message_relay_signature(message)
    if not signature:
        return False
    user_waiters = RELAY_BRIDGE_WAITERS.get(user_id) or {}
    waiters = user_waiters.get(signature) or []
    while waiters:
        future = waiters.pop(0)
        if not future or future.done():
            continue
        future.set_result(message)
        user_waiters[signature] = waiters
        _cleanup_relay_waiters(user_id, signature)
        return True
    _cleanup_relay_waiters(user_id, signature)
    return False


async def wait_for_relay_bridge_message(user_id: int, source_msg, timeout: float = 8.0):
    signature, future = create_relay_bridge_waiter(user_id, source_msg)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        _cleanup_relay_waiters(user_id, signature)


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ADMIN_IDS


def normalize_target(target):
    if target is None:
        return None
    if isinstance(target, int):
        return target
    target = str(target or "").strip()
    if not target:
        return None
    if target.lstrip("-").isdigit():
        return int(target)
    return target


def safe_topic_id(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    value = str(value or "").strip()
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


def get_file_replace_rules(settings: dict | None) -> str:
    settings = settings or {}
    return str(settings.get("replace_words_file") or settings.get("replace_words") or "").strip()


def get_caption_replace_rules(settings: dict | None) -> str:
    settings = settings or {}
    return str(settings.get("replace_words_caption") or settings.get("replace_words") or "").strip()


def update_replace_rule_settings(
    user_id: int,
    settings: dict | None = None,
    *,
    file_rules: str | None = None,
    caption_rules: str | None = None,
):
    current = dict(settings or get_user_settings(user_id) or {})
    next_file_rules = str(get_file_replace_rules(current) if file_rules is None else file_rules or "").strip()
    next_caption_rules = str(get_caption_replace_rules(current) if caption_rules is None else caption_rules or "").strip()
    legacy_rules = next_file_rules if next_file_rules and next_file_rules == next_caption_rules else ""
    payload = {
        "replace_words": legacy_rules,
        "replace_words_file": next_file_rules,
        "replace_words_caption": next_caption_rules,
    }
    update_user_settings(user_id, payload)
    current.update(payload)
    return current


def get_message_file_name(source_msg) -> str:
    if source_msg.document and getattr(source_msg.document, "file_name", None):
        return source_msg.document.file_name
    if source_msg.video and getattr(source_msg.video, "file_name", None):
        return source_msg.video.file_name
    if source_msg.audio and getattr(source_msg.audio, "file_name", None):
        return source_msg.audio.file_name
    if source_msg.animation and getattr(source_msg.animation, "file_name", None):
        return source_msg.animation.file_name
    if source_msg.video_note:
        return "video_note.mp4"
    if source_msg.sticker and getattr(source_msg.sticker, "file_name", None):
        return source_msg.sticker.file_name
    if source_msg.sticker:
        if bool(getattr(source_msg.sticker, "is_animated", False)):
            return "sticker.tgs"
        if bool(getattr(source_msg.sticker, "is_video", False)):
            return "sticker.webm"
        return "sticker.webp"
    if source_msg.photo:
        return "photo.jpg"
    if source_msg.voice:
        return "voice.ogg"
    return "file"


def get_message_file_size(source_msg) -> int:
    for media in ("document", "video", "audio", "photo", "voice", "animation", "sticker", "video_note"):
        obj = getattr(source_msg, media, None)
        if obj and getattr(obj, "file_size", None):
            return int(getattr(obj, "file_size", 0) or 0)
    return 0


def get_message_duration(source_msg) -> str:
    for media in ("video", "audio", "voice", "animation", "video_note"):
        obj = getattr(source_msg, media, None)
        if obj and getattr(obj, "duration", None):
            return str(getattr(obj, "duration", "") or "")
    return ""


def get_message_file_id(source_msg) -> str:
    if not source_msg:
        return ""
    for media in ("photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"):
        obj = getattr(source_msg, media, None)
        file_id = getattr(obj, "file_id", None) if obj else None
        if file_id:
            return str(file_id)
    return ""


def normalize_message_result(result):
    if isinstance(result, (list, tuple)):
        return result[0] if result else None
    return result


def classify_delivery_error(exc) -> str:
    text = str(exc or "").strip().upper()
    if "CHAT_FORWARDS_RESTRICTED" in text:
        return "chat_forwards_restricted"
    if "PEER_ID_INVALID" in text:
        return "peer_id_invalid"
    if "CHANNEL_INVALID" in text:
        return "channel_invalid"
    if "TOPIC_DELETED" in text:
        return "topic_deleted"
    if "TOPIC" in text and "INVALID" in text:
        return "topic_invalid"
    return "unknown"


def remember_delivery_error_codes(settings: dict | None, error_codes):
    if not isinstance(settings, dict):
        return
    cleaned = []
    for code in error_codes or []:
        value = str(code or "").strip().lower()
        if value and value not in cleaned:
            cleaned.append(value)
    settings["_last_delivery_error_codes"] = cleaned


def consume_delivery_error_codes(settings: dict | None) -> list[str]:
    if not isinstance(settings, dict):
        return []
    raw = settings.pop("_last_delivery_error_codes", [])
    if not isinstance(raw, (list, tuple, set)):
        return []
    cleaned = []
    for code in raw:
        value = str(code or "").strip().lower()
        if value and value not in cleaned:
            cleaned.append(value)
    return cleaned


async def ensure_target_peer_ready(client, target):
    if not client:
        return
    target = normalize_target(target)
    cache_key = (id(client), str(target))
    now = time.time()
    expired_peer_keys = [key for key, expiry in TARGET_PEER_READY_CACHE.items() if expiry <= now]
    for key in expired_peer_keys:
        TARGET_PEER_READY_CACHE.pop(key, None)
    if TARGET_PEER_READY_CACHE.get(cache_key, 0) > now:
        return
    try:
        await client.get_chat(target)
        TARGET_PEER_READY_CACHE[cache_key] = now + TARGET_PEER_READY_TTL
    except Exception:
        pass


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
        or getattr(source_msg, "sticker", None)
        or getattr(source_msg, "video_note", None)
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
        "sticker",
        "video_note",
    }


def is_media_like_message(source_msg) -> bool:
    if is_media_message(source_msg):
        return True
    media_name = str(getattr(source_msg, "media", "") or "").lower()
    return any(token in media_name for token in ["photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"])


def build_template_context(source_msg, settings: dict, index_no: int = 0):
    filename = sanitize_filename(get_message_file_name(source_msg))
    filename = apply_replace_rules(filename, get_file_replace_rules(settings))

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

    caption = apply_replace_rules(caption, get_caption_replace_rules(settings))

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

    value = apply_replace_rules(value, get_caption_replace_rules(settings))

    prefix = (settings.get("prefix") or "").strip()
    suffix = (settings.get("suffix") or "").strip()

    if prefix:
        value = f"{prefix} {value}".strip()
    if suffix:
        value = f"{value} {suffix}".strip()

    return value or " "


def build_final_filename(original_filename: str, settings: dict, index_no: int = 0):
    original_filename = sanitize_filename(original_filename or "file")
    original_filename = apply_replace_rules(original_filename, get_file_replace_rules(settings))

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

    new_base = apply_replace_rules(new_base, get_file_replace_rules(settings))
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
        or get_file_replace_rules(settings)
        or get_caption_replace_rules(settings)
        or settings.get("auto_rename_enabled")
        or settings.get("rename_template")
        or settings.get("auto_rename")
        or settings.get("filename_prefix")
        or settings.get("filename_suffix")
        or settings.get("filename_index_enabled")
        or settings.get("metadata_enabled")
    )


def normalize_storage_mode(value: str) -> str:
    value = str(value or "telegram").strip().lower()
    return value if value in {"telegram", "gdrive", "rclone"} else "telegram"


def get_configured_storage_destination(settings: dict | None):
    settings = settings or {}
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    if storage_mode == "gdrive":
        return str(settings.get("gdrive_folder_id", "") or "").strip() or None
    if storage_mode == "rclone":
        return str(settings.get("rclone_remote_path", "") or "").strip() or None
    return normalize_target(settings.get("upload_destination", "")) or DEFAULT_DESTINATION or None


def ensure_storage_runtime_ready(settings: dict | None):
    settings = settings or {}
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))

    if storage_mode == "gdrive":
        ensure_shared_user_site_packages()
        token_path = str(settings.get("gdrive_token_path", "") or "").strip()
        folder_id = str(settings.get("gdrive_folder_id", "") or "").strip()
        if not token_path or not os.path.exists(token_path):
            raise RuntimeError("Google Drive token.pickle missing hai.")
        if not folder_id:
            raise RuntimeError("Google Drive Folder ID set nahi hai.")
        if importlib.util.find_spec("googleapiclient") is None:
            raise RuntimeError("Google Drive runtime missing hai. `google-api-python-client` install karo.")
        return

    if storage_mode == "rclone":
        config_path = str(settings.get("rclone_config_path", "") or "").strip()
        remote_path = str(settings.get("rclone_remote_path", "") or "").strip()
        if not config_path or not os.path.exists(config_path):
            raise RuntimeError("rclone.conf missing hai.")
        if not remote_path:
            raise RuntimeError("Rclone Path set nahi hai.")


def get_next_allowed_storage_mode(current_mode: str, allowed_modes: list[str] | None = None) -> str:
    normalized = []
    for mode in (allowed_modes or ["telegram"]):
        mode = normalize_storage_mode(mode)
        if mode not in normalized:
            normalized.append(mode)
    if not normalized:
        normalized = ["telegram"]

    current_mode = normalize_storage_mode(current_mode)
    if current_mode not in normalized:
        return normalized[0]
    return normalized[(normalized.index(current_mode) + 1) % len(normalized)]


def get_effective_storage_mode_for_message(user_id: int, source_msg, settings: dict) -> str:
    settings = settings or {}
    base_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    route_template = str(settings.get("route_template", "off") or "off").strip().lower()
    file_name = (get_message_file_name(source_msg) or "").lower()
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
    mode = base_mode
    if route_template == "smart":
        if source_msg.document and ext in {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt"}:
            mode = "gdrive"
        elif source_msg.document and ext in {"zip", "rar", "7z", "tar", "gz"}:
            mode = "rclone"
    elif route_template == "docs_to_gdrive" and (source_msg.document or ext in {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt"}):
        mode = "gdrive"
    elif route_template == "media_to_telegram" and is_media_message(source_msg):
        mode = "telegram"
    elif route_template == "archives_to_rclone" and ext in {"zip", "rar", "7z", "tar", "gz"}:
        mode = "rclone"
    if not user_can_use_storage_mode(user_id, mode):
        raise RuntimeError(f"Current plan me {mode} storage allowed nahi hai. Allowed: {', '.join(get_user_allowed_storage_modes(user_id))}")
    return mode


def get_primary_telegram_settings(settings: dict) -> dict:
    cloned = dict(settings or {})
    tg_mode = str(cloned.get("telegram_upload_mode", cloned.get("upload_mode", "media")) or "media").strip().lower()
    if tg_mode not in {"media", "document"}:
        tg_mode = "media"
    cloned["telegram_upload_mode"] = tg_mode
    cloned["upload_mode"] = tg_mode
    return cloned


def derive_gdrive_token_dest(user_id: int, filename: str = "token.pickle") -> str:
    folder = getattr(cfg, "GDRIVE_TOKENS_DIR", TEMP_DIR)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}_{filename}")


def derive_rclone_config_dest(user_id: int, filename: str = "rclone.conf") -> str:
    folder = getattr(cfg, "RCLONE_CONFIGS_DIR", TEMP_DIR)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}_{filename}")


PERSONAL_BOT_CLIENTS = {}


async def get_or_create_personal_bot_client(user_id: int, settings: dict):
    mode = str((settings or {}).get("bot_delivery_mode", "main") or "main").strip().lower()
    token = str((settings or {}).get("personal_bot_token", "") or "").strip()
    if mode != "personal" or not token:
        return None
    cache = PERSONAL_BOT_CLIENTS.get(user_id)
    if cache and cache.get("token") == token:
        return cache.get("client")
    client_obj = Client(
        name=f"personal_bot_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=token,
        in_memory=True,
    )
    await client_obj.start()
    me = await client_obj.get_me()
    update_user_settings(user_id, {"personal_bot_username": getattr(me, "username", "") or ""})
    PERSONAL_BOT_CLIENTS[user_id] = {"token": token, "client": client_obj}
    return client_obj


async def cleanup_personal_bot_client(user_id: int):
    cache = PERSONAL_BOT_CLIENTS.pop(user_id, None)
    if cache and cache.get("client"):
        try:
            await cache["client"].stop()
        except Exception:
            pass


async def validate_personal_bot_token(user_id: int, token: str):
    temp_client = Client(
        name=f"validate_personal_bot_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=token,
        in_memory=True,
    )
    await temp_client.start()
    try:
        me = await temp_client.get_me()
        return me
    finally:
        try:
            await temp_client.stop()
        except Exception:
            pass


def create_temp_text_file(source_msg, settings: dict, index_no: int = 0):
    os.makedirs(TEMP_DIR, exist_ok=True)
    path = os.path.join(TEMP_DIR, f"text_{uuid.uuid4().hex[:8]}.txt")
    value = build_final_text(source_msg.text or source_msg.caption or "", source_msg, settings, index_no=index_no)
    Path(path).write_text(ensure_non_empty_text(value), encoding="utf-8")
    return path


def _build_gdrive_service(token_path: str):
    import pickle
    from googleapiclient.discovery import build
    with open(token_path, "rb") as fh:
        creds = pickle.load(fh)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _upload_file_to_gdrive_sync(token_path: str, file_path: str, folder_id: str):
    from googleapiclient.http import MediaFileUpload
    service = _build_gdrive_service(token_path)
    metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        metadata["parents"] = [folder_id]
    media = MediaFileUpload(file_path, resumable=False)
    return service.files().create(body=metadata, media_body=media, fields="id,name,webViewLink").execute()


async def upload_file_to_gdrive(user_id: int, settings: dict, file_path: str):
    token_path = str(settings.get("gdrive_token_path", "") or "").strip()
    folder_id = str(settings.get("gdrive_folder_id", "") or "").strip()
    if not token_path or not os.path.exists(token_path):
        raise RuntimeError("Google Drive token.pickle missing hai.")
    if not folder_id:
        raise RuntimeError("Google Drive folder ID set nahi hai.")
    result = await asyncio.to_thread(_upload_file_to_gdrive_sync, token_path, file_path, folder_id)
    update_user_settings(user_id, {"gdrive_last_file_link": str(result.get("webViewLink", "") or result.get("id", ""))})
    return result


async def validate_gdrive_settings_for_user(settings: dict):
    token_path = str(settings.get("gdrive_token_path", "") or "").strip()
    folder_id = str(settings.get("gdrive_folder_id", "") or "").strip()
    if not token_path or not os.path.exists(token_path):
        raise RuntimeError("token.pickle missing")
    if not folder_id:
        raise RuntimeError("folder id missing")
    def _validate():
        service = _build_gdrive_service(token_path)
        return service.files().get(fileId=folder_id, fields="id,name,mimeType").execute()
    return await asyncio.to_thread(_validate)


async def upload_file_to_rclone(user_id: int, settings: dict, file_path: str):
    config_path = str(settings.get("rclone_config_path", "") or "").strip()
    remote_path = str(settings.get("rclone_remote_path", "") or "").strip()
    if not config_path or not os.path.exists(config_path):
        raise RuntimeError("rclone config missing hai.")
    if not remote_path:
        raise RuntimeError("rclone remote path set nahi hai.")
    target = remote_path.rstrip("/") + "/" + os.path.basename(file_path)
    proc = await asyncio.create_subprocess_exec(
        getattr(cfg, "RCLONE_BIN", "rclone"), "copyto", file_path, target, "--config", config_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((stderr or stdout or b"rclone failed").decode("utf-8", "ignore")[:500])
    update_user_settings(user_id, {"rclone_last_file_path": target})
    return {"path": target}


async def validate_rclone_settings_for_user(settings: dict):
    config_path = str(settings.get("rclone_config_path", "") or "").strip()
    remote_path = str(settings.get("rclone_remote_path", "") or "").strip()
    if not config_path or not os.path.exists(config_path):
        raise RuntimeError("rclone.conf missing")
    if not remote_path:
        raise RuntimeError("remote path missing")
    proc = await asyncio.create_subprocess_exec(
        getattr(cfg, "RCLONE_BIN", "rclone"), "lsf", remote_path, "--max-depth", "1", "--config", config_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((stderr or stdout or b"rclone validation failed").decode("utf-8", "ignore")[:500])
    return {"path": remote_path}


async def validate_telegram_destination(client, settings: dict):
    destination = normalize_target(settings.get("upload_destination", "")) or DEFAULT_DESTINATION or None
    if not destination:
        raise RuntimeError("Telegram destination set nahi hai")
    chat = await client.get_chat(destination)
    me = await client.get_me()
    try:
        member = await client.get_chat_member(chat.id, me.id)
        member_status = str(getattr(member, "status", "unknown"))
    except Exception:
        member_status = "unknown"
    return {"chat_id": chat.id, "title": getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown", "type": str(getattr(chat, "type", "unknown")), "member_status": member_status}


async def validate_current_destination_settings(client, settings: dict):
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    if storage_mode == "gdrive":
        return await validate_gdrive_settings_for_user(settings)
    if storage_mode == "rclone":
        return await validate_rclone_settings_for_user(settings)
    return await validate_telegram_destination(client, settings)


async def upload_to_storage_target(client, task_id: str, source_msg, settings: dict, user_id: int, file_path: str, storage_mode: str, index_no: int = 0, fetch_mode: str = "bot", user_client=None):
    storage_mode = normalize_storage_mode(storage_mode)
    if storage_mode == "gdrive":
        info = await upload_file_to_gdrive(user_id, settings, file_path)
        delivered_to = ["gdrive"]
        delivery_errors = []
        if LOG_CHANNEL:
            try:
                log_settings = get_primary_telegram_settings(settings)
                await deliver_log_channel_with_best_effort(client, task_id, source_msg, log_settings, file_path, index_no=index_no, fetch_mode=fetch_mode, user_client=user_client)
                delivered_to.append(str(LOG_CHANNEL))
            except Exception as e:
                delivery_errors.append(f"{LOG_CHANNEL}: {e}")
        return delivered_to, delivery_errors, info
    if storage_mode == "rclone":
        info = await upload_file_to_rclone(user_id, settings, file_path)
        delivered_to = ["rclone"]
        delivery_errors = []
        if LOG_CHANNEL:
            try:
                log_settings = get_primary_telegram_settings(settings)
                await deliver_log_channel_with_best_effort(client, task_id, source_msg, log_settings, file_path, index_no=index_no, fetch_mode=fetch_mode, user_client=user_client)
                delivered_to.append(str(LOG_CHANNEL))
            except Exception as e:
                delivery_errors.append(f"{LOG_CHANNEL}: {e}")
        return delivered_to, delivery_errors, info
    raise RuntimeError("Unsupported storage mode")


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


async def send_cached_media_to_target(client, target, source_msg, settings: dict, index_no: int = 0):
    target = normalize_target(target)
    await ensure_target_peer_ready(client, target)
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    caption = build_final_caption(source_msg, settings, index_no=index_no)
    caption = caption if str(caption or "").strip() else None
    caption_parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html")) if caption else None
    file_id = get_message_file_id(source_msg)
    if not file_id:
        return None

    if source_msg.photo:
        return await client.send_photo(
            chat_id=target,
            photo=file_id,
            caption=caption,
            parse_mode=caption_parse_mode,
            message_thread_id=topic_id if topic_id else None,
        )
    if source_msg.video:
        return await client.send_video(
            chat_id=target,
            video=file_id,
            caption=caption,
            parse_mode=caption_parse_mode,
            message_thread_id=topic_id if topic_id else None,
            duration=getattr(source_msg.video, "duration", None),
            width=getattr(source_msg.video, "width", None),
            height=getattr(source_msg.video, "height", None),
            supports_streaming=bool(getattr(source_msg.video, "supports_streaming", False)),
        )
    if source_msg.document:
        return await client.send_document(
            chat_id=target,
            document=file_id,
            caption=caption,
            parse_mode=caption_parse_mode,
            message_thread_id=topic_id if topic_id else None,
        )
    if source_msg.audio:
        return await client.send_audio(
            chat_id=target,
            audio=file_id,
            caption=caption,
            parse_mode=caption_parse_mode,
            message_thread_id=topic_id if topic_id else None,
            duration=getattr(source_msg.audio, "duration", None),
            performer=getattr(source_msg.audio, "performer", None),
            title=getattr(source_msg.audio, "title", None),
        )
    if source_msg.voice:
        return await client.send_voice(
            chat_id=target,
            voice=file_id,
            caption=caption,
            parse_mode=caption_parse_mode,
            message_thread_id=topic_id if topic_id else None,
            duration=getattr(source_msg.voice, "duration", None),
        )
    if source_msg.animation:
        return await client.send_animation(
            chat_id=target,
            animation=file_id,
            caption=caption,
            parse_mode=caption_parse_mode,
            message_thread_id=topic_id if topic_id else None,
            duration=getattr(source_msg.animation, "duration", None),
            width=getattr(source_msg.animation, "width", None),
            height=getattr(source_msg.animation, "height", None),
        )
    if source_msg.sticker:
        return await client.send_sticker(
            chat_id=target,
            sticker=file_id,
            message_thread_id=topic_id if topic_id else None,
        )
    if source_msg.video_note:
        return await client.send_video_note(
            chat_id=target,
            video_note=file_id,
            message_thread_id=topic_id if topic_id else None,
            duration=getattr(source_msg.video_note, "duration", None),
            length=getattr(source_msg.video_note, "length", None),
        )
    return None


async def try_direct_forward_with_user_client(user_client, source_msg, target, settings: dict, index_no: int = 0):
    target = normalize_target(target)
    await ensure_target_peer_ready(user_client, target)
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    errors = []
    error_codes = []
    try:
        result = normalize_message_result(await user_client.copy_message(
            chat_id=target,
            from_chat_id=source_msg.chat.id,
            message_id=source_msg.id,
            message_thread_id=topic_id if topic_id else None,
        ))
        if result:
            remember_delivery_error_codes(settings, [])
            return result
    except Exception as exc:
        errors.append(f"copy: {exc}")
        error_codes.append(classify_delivery_error(exc))
        if topic_id:
            try:
                result = normalize_message_result(await user_client.copy_message(
                    chat_id=target,
                    from_chat_id=source_msg.chat.id,
                    message_id=source_msg.id,
                ))
                if result:
                    remember_delivery_error_codes(settings, [])
                    return result
            except Exception as retry_exc:
                errors.append(f"copy(no-topic): {retry_exc}")
                error_codes.append(classify_delivery_error(retry_exc))

    try:
        result = normalize_message_result(await user_client.forward_messages(
            chat_id=target,
            from_chat_id=source_msg.chat.id,
            message_ids=source_msg.id,
            message_thread_id=topic_id if topic_id else None,
            drop_author=False,
        ))
        if result:
            remember_delivery_error_codes(settings, [])
            return result
    except Exception as exc:
        errors.append(f"forward: {exc}")
        error_codes.append(classify_delivery_error(exc))
        if topic_id:
            try:
                result = normalize_message_result(await user_client.forward_messages(
                    chat_id=target,
                    from_chat_id=source_msg.chat.id,
                    message_ids=source_msg.id,
                    drop_author=False,
                ))
                if result:
                    remember_delivery_error_codes(settings, [])
                    return result
            except Exception as retry_exc:
                errors.append(f"forward(no-topic): {retry_exc}")
                error_codes.append(classify_delivery_error(retry_exc))

    remember_delivery_error_codes(settings, error_codes)
    debug_log(f"User direct save failed for {target}: {' | '.join(errors)}")
    return None


async def probe_target_client_access(client_obj, client_kind: str, target):
    info = {
        "client": client_obj,
        "client_kind": client_kind,
        "target": normalize_target(target),
        "resolved": False,
        "writable": False,
        "chat_id": 0,
        "chat_type": "",
        "member_status": "",
        "title": "",
        "error": "",
    }
    if not client_obj:
        return info

    cache_key = (id(client_obj), str(client_kind or ""), str(info["target"]))
    now = time.time()
    expired_cache_keys = [key for key, entry in TARGET_ACCESS_CACHE.items() if float((entry or {}).get("expires_at", 0) or 0) <= now]
    for key in expired_cache_keys:
        TARGET_ACCESS_CACHE.pop(key, None)
    cached_entry = TARGET_ACCESS_CACHE.get(cache_key)
    if cached_entry:
        cached_info = dict(cached_entry.get("info") or {})
        cached_info["client"] = client_obj
        return cached_info

    try:
        chat = await client_obj.get_chat(info["target"])
        info["resolved"] = True
        info["chat_id"] = getattr(chat, "id", 0) or 0
        info["chat_type"] = normalize_chat_type(getattr(chat, "type", ""))
        info["title"] = getattr(chat, "title", None) or getattr(chat, "first_name", None) or ""
        TARGET_PEER_READY_CACHE[(id(client_obj), str(info["target"]))] = now + TARGET_PEER_READY_TTL
    except Exception as exc:
        info["error"] = str(exc)
        TARGET_ACCESS_CACHE[cache_key] = {"expires_at": now + TARGET_ACCESS_CACHE_TTL, "info": dict(info)}
        return info

    try:
        me = getattr(client_obj, "me", None) or await client_obj.get_me()
    except Exception as exc:
        info["error"] = str(exc)
        TARGET_ACCESS_CACHE[cache_key] = {"expires_at": now + TARGET_ACCESS_CACHE_TTL, "info": dict(info)}
        return info

    member_status = ""
    if info["chat_type"] in {"private", "bot"}:
        member_status = "member"
    else:
        try:
            member = await client_obj.get_chat_member(info["chat_id"], me.id)
            member_status = normalize_member_status(getattr(member, "status", ""))
        except Exception as exc:
            info["error"] = str(exc)
            member_status = ""

    info["member_status"] = member_status
    info["writable"] = is_positive_writable_target(info["chat_type"], member_status)
    TARGET_ACCESS_CACHE[cache_key] = {"expires_at": now + TARGET_ACCESS_CACHE_TTL, "info": dict(info)}
    return info


async def probe_target_access_map(client_map: dict, target):
    client_kinds = ("main_bot", "user_session", "personal_bot")
    results = await asyncio.gather(*[
        probe_target_client_access(client_map.get(client_kind), client_kind, target)
        for client_kind in client_kinds
    ])
    return {client_kind: result for client_kind, result in zip(client_kinds, results)}


async def copy_result_to_target(client, delivered_message, target, settings: dict):
    if not delivered_message:
        return None
    return await copy_known_message_to_target(
        client,
        getattr(getattr(delivered_message, "chat", None), "id", None),
        getattr(delivered_message, "id", None),
        target,
        settings,
    )


async def copy_known_message_to_target(client, from_chat_id, message_id, target, settings: dict):
    if not from_chat_id or not message_id:
        return None
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    target = normalize_target(target)
    await ensure_target_peer_ready(client, target)
    try:
        return normalize_message_result(await client.copy_message(
            chat_id=target,
            from_chat_id=from_chat_id,
            message_id=message_id,
            message_thread_id=topic_id if topic_id else None,
        ))
    except Exception:
        if topic_id:
            try:
                return normalize_message_result(await client.copy_message(
                    chat_id=target,
                    from_chat_id=from_chat_id,
                    message_id=message_id,
                ))
            except Exception:
                pass
        try:
            return normalize_message_result(await client.forward_messages(
                chat_id=target,
                from_chat_id=from_chat_id,
                message_ids=message_id,
                message_thread_id=topic_id if topic_id else None,
                drop_author=False,
            ))
        except Exception:
            if topic_id:
                try:
                    return normalize_message_result(await client.forward_messages(
                        chat_id=target,
                        from_chat_id=from_chat_id,
                        message_ids=message_id,
                        drop_author=False,
                    ))
                except Exception:
                    pass
            return None


async def ensure_downloaded_source_file(ui_client, task_id: str, source_msg, settings: dict, index_no: int, download_state: dict, source_access: dict, client_map: dict):
    download_state = download_state or {}
    current_path = str(download_state.get("path") or "").strip()
    if current_path and os.path.exists(current_path):
        return current_path

    download_client_kind = select_download_client_kind(source_access, client_map)
    if not download_client_kind:
        raise RuntimeError("Source message readable client nahi mila, isliye download start nahi ho paya.")

    fallback_reason = str(download_state.get("fallback_reason") or "").strip()
    reason_text = f"Fallback: {fallback_reason}" if fallback_reason else "Preparing fallback download"
    touch_task(task_id, {
        "status": "downloading",
        "current_stage": "downloading",
        "progress_text": reason_text,
        "is_visible": True,
        "fallback_reason": fallback_reason,
        "delivery_path": "download_upload",
        "delivery_client_kind": download_client_kind,
    })
    await update_task_status_message(ui_client, task_id)

    source_client = client_map.get(download_client_kind)
    download_hint = get_temp_download_path(source_msg)
    download_path = download_hint
    try:
        download_result = await source_client.download_media(
            source_msg,
            file_name=download_hint,
            progress=progress_callback,
            progress_args=(ui_client, task_id, "downloading"),
        )
        download_path = resolve_downloaded_path(download_hint, download_result)
        ensure_valid_downloaded_file(download_path)
        download_path = rename_downloaded_file(download_path, source_msg, settings, index_no=index_no)
        ensure_valid_downloaded_file(download_path)
    except Exception:
        safe_delete_local_file(download_path)
        if download_path != download_hint:
            safe_delete_local_file(download_hint)
        raise

    download_state["path"] = download_path
    download_state["download_client_kind"] = download_client_kind
    return download_path


async def relay_message_via_log_channel(client_map: dict, source_msg, relay_target, target, settings: dict, index_no: int = 0):
    relay_target = normalize_target(relay_target)
    target = normalize_target(target)
    relay_source_kind = str((settings or {}).get("_relay_source_client_kind") or "").strip().lower()
    relay_client_kind = str((settings or {}).get("_relay_client_kind") or "").strip().lower()

    relay_source_client = client_map.get(relay_source_kind)
    relay_client = client_map.get(relay_client_kind)
    if not relay_source_client or not relay_client:
        raise RuntimeError("Relay clients unavailable")

    relay_settings = dict(settings or {})
    relay_settings["topic_id"] = ""
    relay_settings.pop("_relay_source_client_kind", None)
    relay_settings.pop("_relay_client_kind", None)

    if relay_source_kind == "user_session":
        bridge_message = await try_direct_forward_with_user_client(relay_source_client, source_msg, relay_target, relay_settings, index_no=index_no)
    elif relay_source_kind == "main_bot":
        bridge_message = await try_direct_copy(relay_source_client, source_msg, relay_target, relay_settings, index_no=index_no)
    else:
        raise RuntimeError("Relay source client unsupported")

    if not bridge_message:
        raise RuntimeError("Relay bridge send failed")

    delivery_message = await copy_result_to_target(relay_client, bridge_message, target, settings)
    if not delivery_message:
        raise RuntimeError("Relay destination copy failed")

    return bridge_message, delivery_message


async def get_main_bot_bridge_target(bot_client):
    me = getattr(bot_client, "me", None) or await bot_client.get_me()
    username = str(getattr(me, "username", "") or "").strip()
    if username:
        return f"@{username}"
    return int(getattr(me, "id", 0) or 0)


def can_use_bot_pm_relay(source_access: dict | None, target_access: dict | None, client_map: dict | None = None) -> bool:
    source_access = source_access or {}
    target_access = target_access or {}
    client_map = client_map or {}
    if not source_access.get("user_session"):
        return False
    if not (target_access.get("main_bot") or {}).get("writable"):
        return False
    return bool(client_map.get("user_session") and client_map.get("main_bot"))


async def relay_message_via_bot_pm(client_map: dict, source_msg, user_id: int, target, settings: dict, index_no: int = 0):
    relay_source_client = client_map.get("user_session")
    relay_client = client_map.get("main_bot")
    if not relay_source_client or not relay_client:
        raise RuntimeError("Bot PM relay clients unavailable")

    bridge_target = await get_main_bot_bridge_target(relay_client)
    relay_settings = dict(settings or {})
    relay_settings["topic_id"] = ""
    mark_ignored_direct_signature(user_id, source_msg)
    bridge_future = asyncio.create_task(wait_for_relay_bridge_message(user_id, source_msg))

    bridge_message = await try_direct_forward_with_user_client(
        relay_source_client,
        source_msg,
        bridge_target,
        relay_settings,
        index_no=index_no,
    )
    if not bridge_message:
        bridge_future.cancel()
        raise RuntimeError("Bot PM relay bridge send failed")

    bot_bridge_message = None
    try:
        bot_bridge_message = await bridge_future
    except Exception:
        bot_bridge_message = None
    if bot_bridge_message:
        mark_ignored_direct_message(user_id, getattr(bot_bridge_message, "id", None))

    try:
        delivery_message = None
        for attempt in range(3):
            delivery_message = await copy_known_message_to_target(
                relay_client,
                getattr(getattr(bot_bridge_message, "chat", None), "id", None) or int(user_id),
                getattr(bot_bridge_message, "id", None) or getattr(bridge_message, "id", None),
                target,
                settings,
            )
            if delivery_message:
                break
            await asyncio.sleep(0.4 * (attempt + 1))
        if not delivery_message:
            raise RuntimeError("Bot PM relay destination copy failed")
        return bridge_message, delivery_message
    finally:
        await safe_delete_message(bridge_message)
        if bot_bridge_message and getattr(bot_bridge_message, "id", None) != getattr(bridge_message, "id", None):
            await safe_delete_message(bot_bridge_message)


async def deliver_target_with_routing(ui_client, task_id: str, source_msg, settings: dict, target, *, client_map: dict, source_access: dict, index_no: int = 0, download_state: dict | None = None, allow_download_fallback: bool = True):
    target = normalize_target(target)
    ensure_task_not_cancelled(task_id)
    user_id = int((settings or {}).get("_delivery_user_id") or 0)
    source_is_media = is_media_message(source_msg)
    has_cached_file_id = bool(get_message_file_id(source_msg))
    has_transforming = has_transforming_settings(settings)
    is_protected = source_has_protected_content(source_msg)
    relay_target_available = bool(LOG_CHANNEL and str(normalize_target(LOG_CHANNEL)) != str(target))
    if relay_target_available:
        access_map, relay_access_map = await asyncio.gather(
            probe_target_access_map(client_map, target),
            probe_target_access_map(client_map, LOG_CHANNEL),
        )
    else:
        access_map = await probe_target_access_map(client_map, target)
        relay_access_map = {}
    prefer_personal_upload = str((settings or {}).get("bot_delivery_mode", "main") or "main").strip().lower() == "personal"
    bot_pm_relay_available = bool(user_id) and can_use_bot_pm_relay(source_access, access_map, client_map)
    allow_main_bot_direct = bool(ENABLE_DIRECT_PUBLIC_COPY and cfg.PREFER_COPY_OVER_DOWNLOAD)
    allow_user_session_direct = bool(cfg.ALLOW_FORWARD_AS_FALLBACK and ENABLE_DIRECT_PRIVATE_COPY)

    plan = build_target_delivery_plan(
        is_media=source_is_media,
        has_cached_file_id=has_cached_file_id,
        has_transforming=has_transforming,
        is_protected=is_protected,
        source_access=source_access,
        target_access=access_map,
        allow_main_bot_direct=allow_main_bot_direct,
        allow_user_session_direct=allow_user_session_direct,
        prefer_personal_upload=prefer_personal_upload,
        relay_access=relay_access_map,
        relay_target_available=relay_target_available,
        bot_pm_relay_available=bot_pm_relay_available,
    )

    if plan.get("error"):
        raise RuntimeError(build_target_access_error(target, access_map))

    delivery_message = None
    bridge_message = None
    delivery_client_kind = plan.get("direct_client_kind") or plan.get("cached_client_kind") or plan.get("upload_client_kind")
    route_client_label = delivery_client_kind
    delivery_path = describe_delivery_path(plan.get("mode", ""), delivery_client_kind)

    if plan.get("mode") == "direct":
        touch_task(task_id, {
            "status": "copying",
            "current_stage": "copying",
            "progress_text": describe_target_route(target, delivery_path, route_client_label),
            "is_visible": True,
            "delivery_path": delivery_path,
            "delivery_client_kind": delivery_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)

        if plan.get("direct_client_kind") == "main_bot":
            try:
                delivery_message = await try_direct_copy(client_map["main_bot"], source_msg, target, settings, index_no=index_no)
            except Exception:
                delivery_message = None
        elif plan.get("direct_client_kind") == "user_session":
            delivery_message = await try_direct_forward_with_user_client(client_map["user_session"], source_msg, target, settings, index_no=index_no)

        ensure_task_not_cancelled(task_id)
        if delivery_message:
            return {
                "message": delivery_message,
                "target": target,
                "delivery_path": delivery_path,
                "delivery_client_kind": delivery_client_kind,
                "route_client_label": route_client_label,
                "fallback_reason": "",
                "target_access": access_map,
            }

        if download_state is None:
            download_state = {}
        direct_error_codes = consume_delivery_error_codes(settings)
        if "chat_forwards_restricted" in direct_error_codes:
            download_state["fallback_reason"] = "protected_content"
            plan = {
                "mode": "upload" if source_is_media else "text",
                "direct_client_kind": None,
                "cached_client_kind": None,
                "relay_source_client_kind": None,
                "relay_client_kind": None,
                "relay_via": "",
                "upload_client_kind": choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload),
                "fallback_reason": "protected_content",
                "error": "",
            }
        else:
            download_state["fallback_reason"] = "direct_attempt_failed"
            plan = build_followup_delivery_plan_after_direct_failure(
                failed_client_kind=plan.get("direct_client_kind") or "",
                is_media=source_is_media,
                has_cached_file_id=has_cached_file_id,
                has_transforming=has_transforming,
                is_protected=is_protected,
                source_access=source_access,
                target_access=access_map,
                allow_main_bot_direct=allow_main_bot_direct,
                allow_user_session_direct=allow_user_session_direct,
                prefer_personal_upload=prefer_personal_upload,
                relay_access=relay_access_map,
                relay_target_available=relay_target_available,
                bot_pm_relay_available=bot_pm_relay_available,
            )
        if plan.get("error"):
            raise RuntimeError(build_target_access_error(target, access_map))
        if plan.get("mode") == "direct":
            next_direct_kind = plan.get("direct_client_kind")
            next_delivery_path = describe_delivery_path("direct", next_direct_kind)
            next_route_label = next_direct_kind
            touch_task(task_id, {
                "status": "copying",
                "current_stage": "copying",
                "progress_text": describe_target_route(target, next_delivery_path, next_route_label),
                "is_visible": True,
                "delivery_path": next_delivery_path,
                "delivery_client_kind": next_direct_kind,
                "fallback_reason": "",
            })
            await update_task_status_message(ui_client, task_id)
            ensure_task_not_cancelled(task_id)
            if next_direct_kind == "main_bot":
                try:
                    delivery_message = await try_direct_copy(client_map["main_bot"], source_msg, target, settings, index_no=index_no)
                except Exception:
                    delivery_message = None
            elif next_direct_kind == "user_session":
                delivery_message = await try_direct_forward_with_user_client(client_map["user_session"], source_msg, target, settings, index_no=index_no)
            ensure_task_not_cancelled(task_id)
            if delivery_message:
                return {
                    "message": delivery_message,
                    "target": target,
                    "delivery_path": next_delivery_path,
                    "delivery_client_kind": next_direct_kind,
                    "route_client_label": next_route_label,
                    "fallback_reason": "",
                    "target_access": access_map,
                }
            plan = build_followup_delivery_plan_after_direct_failure(
                failed_client_kind=next_direct_kind or "",
                is_media=source_is_media,
                has_cached_file_id=has_cached_file_id,
                has_transforming=has_transforming,
                is_protected=is_protected,
                source_access=source_access,
                target_access=access_map,
                allow_main_bot_direct=False,
                allow_user_session_direct=False,
                prefer_personal_upload=prefer_personal_upload,
                relay_access=relay_access_map,
                relay_target_available=relay_target_available,
                bot_pm_relay_available=bot_pm_relay_available,
            )
            if plan.get("error"):
                raise RuntimeError(build_target_access_error(target, access_map))
        if plan.get("mode") in {"upload", "text"} and not plan.get("upload_client_kind"):
            plan["upload_client_kind"] = choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload)
            if not plan["upload_client_kind"]:
                raise RuntimeError(build_target_access_error(target, access_map))
        delivery_client_kind = plan.get("direct_client_kind") or plan.get("cached_client_kind") or plan.get("relay_client_kind") or plan.get("upload_client_kind")
        route_client_label = delivery_client_kind
        delivery_path = describe_delivery_path(plan.get("mode", ""), plan.get("direct_client_kind") or plan.get("relay_client_kind") or delivery_client_kind)

    if plan.get("mode") == "cached":
        cached_client_kind = plan.get("cached_client_kind")
        cached_client = client_map.get(cached_client_kind)
        if not cached_client:
            raise RuntimeError(build_target_access_error(target, access_map))

        touch_task(task_id, {
            "status": "copying",
            "current_stage": "copying",
            "progress_text": describe_target_route(target, "cached_send", cached_client_kind),
            "is_visible": True,
            "delivery_path": "cached_send",
            "delivery_client_kind": cached_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)

        try:
            delivery_message = normalize_message_result(await send_cached_media_to_target(cached_client, target, source_msg, settings, index_no=index_no))
        except Exception:
            delivery_message = None

        ensure_task_not_cancelled(task_id)
        if delivery_message:
            return {
                "message": delivery_message,
                "target": target,
                "delivery_path": "cached_send",
                "delivery_client_kind": cached_client_kind,
                "route_client_label": cached_client_kind,
                "fallback_reason": "",
                "target_access": access_map,
            }

        if download_state is None:
            download_state = {}
        download_state["fallback_reason"] = "cached_send_failed"
        relay_plan = choose_relay_delivery_plan(
            source_access,
            access_map,
            relay_access_map,
            relay_target_available=relay_target_available,
            prefer_personal_upload=prefer_personal_upload,
            bot_pm_relay_available=bot_pm_relay_available,
        )
        if relay_plan:
            plan["mode"] = "relay"
            plan.update(relay_plan)
            plan["fallback_reason"] = "cached_send_failed"
        else:
            plan["mode"] = "upload"
            plan["upload_client_kind"] = choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload)
            plan["fallback_reason"] = "cached_send_failed"
            if not plan["upload_client_kind"]:
                raise RuntimeError(build_target_access_error(target, access_map))
            delivery_client_kind = plan["upload_client_kind"]
            route_client_label = delivery_client_kind
            delivery_path = "download_upload"

    if plan.get("mode") == "relay":
        relay_source_kind = plan.get("relay_source_client_kind")
        relay_client_kind = plan.get("relay_client_kind")
        relay_via = str(plan.get("relay_via") or "log_channel").strip().lower()
        relay_label = f"{relay_source_kind}->{relay_client_kind}"
        if relay_via == "bot_pm":
            relay_label = f"{relay_label}(pm)"
        relay_settings = dict(settings or {})
        relay_settings["_relay_source_client_kind"] = relay_source_kind
        relay_settings["_relay_client_kind"] = relay_client_kind
        touch_task(task_id, {
            "status": "copying",
            "current_stage": "copying",
            "progress_text": describe_target_route(target, "relay_copy", relay_label),
            "is_visible": True,
            "delivery_path": "relay_copy",
            "delivery_client_kind": relay_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)

        try:
            if relay_via == "bot_pm":
                bridge_message, delivery_message = await relay_message_via_bot_pm(
                    client_map,
                    source_msg,
                    user_id,
                    target,
                    relay_settings,
                    index_no=index_no,
                )
            else:
                bridge_message, delivery_message = await relay_message_via_log_channel(
                    client_map,
                    source_msg,
                    LOG_CHANNEL,
                    target,
                    relay_settings,
                    index_no=index_no,
                )
        except Exception:
            bridge_message = None
            delivery_message = None

        ensure_task_not_cancelled(task_id)
        if delivery_message:
            relay_target_value = ""
            if relay_via == "log_channel":
                relay_target_value = str(normalize_target(LOG_CHANNEL))
            return {
                "message": delivery_message,
                "bridge_message": bridge_message,
                "relay_target": relay_target_value,
                "relay_source_client_kind": relay_source_kind,
                "target": target,
                "delivery_path": "relay_copy",
                "delivery_client_kind": relay_client_kind,
                "route_client_label": relay_label,
                "relay_via": relay_via,
                "fallback_reason": "",
                "target_access": access_map,
            }

        if download_state is None:
            download_state = {}
        download_state["fallback_reason"] = "relay_copy_failed"
        plan["mode"] = "upload" if source_is_media else "text"
        plan["upload_client_kind"] = choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload)
        plan["fallback_reason"] = "relay_copy_failed"
        if not plan["upload_client_kind"]:
            raise RuntimeError(build_target_access_error(target, access_map))
        delivery_client_kind = plan["upload_client_kind"]
        route_client_label = delivery_client_kind
        delivery_path = "download_upload" if source_is_media else "text_send"

    if plan.get("mode") == "text":
        text_client_kind = plan.get("upload_client_kind")
        text_client = client_map.get(text_client_kind)
        if not text_client:
            raise RuntimeError(build_target_access_error(target, access_map))
        touch_task(task_id, {
            "status": "uploading",
            "current_stage": "uploading",
            "progress_text": describe_target_route(target, "text_send", text_client_kind),
            "is_visible": True,
            "delivery_path": "text_send",
            "delivery_client_kind": text_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)
        delivery_message = await send_text_to_target(text_client, target, source_msg, settings, index_no=index_no)
        ensure_task_not_cancelled(task_id)
        return {
            "message": delivery_message,
            "target": target,
            "delivery_path": "text_send",
            "delivery_client_kind": text_client_kind,
            "route_client_label": text_client_kind,
            "fallback_reason": "",
            "target_access": access_map,
        }

    if download_state is None:
        download_state = {}
    if not download_state.get("fallback_reason"):
        download_state["fallback_reason"] = plan.get("fallback_reason", "")
    if not allow_download_fallback:
        fallback_reason = str(download_state.get("fallback_reason") or plan.get("fallback_reason") or "download_fallback_required")
        raise RuntimeError(f"Download fallback disabled for target {target} ({fallback_reason})")

    download_path = await ensure_downloaded_source_file(
        ui_client,
        task_id,
        source_msg,
        settings,
        index_no,
        download_state,
        source_access,
        client_map,
    )

    upload_client_kind = plan.get("upload_client_kind")
    upload_client = client_map.get(upload_client_kind)
    if not upload_client:
        raise RuntimeError(build_target_access_error(target, access_map))

    touch_task(task_id, {
        "status": "uploading",
        "current_stage": "uploading",
        "progress_text": describe_target_route(target, "download_upload", upload_client_kind),
        "is_visible": True,
        "delivery_path": "download_upload",
        "delivery_client_kind": upload_client_kind,
        "fallback_reason": str(download_state.get("fallback_reason") or ""),
    })
    await update_task_status_message(ui_client, task_id)
    ensure_task_not_cancelled(task_id)

    delivery_message = await upload_file_to_target(upload_client, task_id, target, download_path, source_msg, settings, index_no=index_no)
    ensure_task_not_cancelled(task_id)
    return {
        "message": delivery_message,
        "target": target,
        "delivery_path": "download_upload",
        "delivery_client_kind": upload_client_kind,
        "route_client_label": upload_client_kind,
        "fallback_reason": str(download_state.get("fallback_reason") or ""),
        "target_access": access_map,
    }


async def deliver_primary_then_log_routed(ui_client, task_id: str, source_msg, settings: dict, destination, *, user_id: int = 0, client_map: dict, source_access: dict, index_no: int = 0):
    if not destination and not LOG_CHANNEL:
        raise RuntimeError("No destination configured. Destination aur log channel dono blank hain.")

    ensure_task_not_cancelled(task_id)
    routing_settings = dict(settings or {})
    routing_settings["_delivery_user_id"] = int(user_id or 0)
    delivered_to = []
    delivery_errors = []
    route_summaries = []
    download_state = {"path": None, "fallback_reason": ""}
    primary_result = None
    primary_route = None

    if destination:
        try:
            primary_route = await deliver_target_with_routing(
                ui_client,
                task_id,
                source_msg,
                routing_settings,
                destination,
                client_map=client_map,
                source_access=source_access,
                index_no=index_no,
                download_state=download_state,
            )
            primary_result = primary_route.get("message")
            if primary_result:
                delivered_to.append(str(destination))
                route_summaries.append(describe_target_route(destination, primary_route.get("delivery_path", ""), primary_route.get("route_client_label") or primary_route.get("delivery_client_kind")))
            else:
                delivery_errors.append(f"{destination}: send returned empty response")
        except Exception as exc:
            delivery_errors.append(f"{destination}: {exc}")

    ensure_task_not_cancelled(task_id)
    relay_log_delivered = False
    relay_target = str((primary_route or {}).get("relay_target") or "").strip()
    if relay_target and str(normalize_target(LOG_CHANNEL)) == relay_target and str(LOG_CHANNEL) != str(destination):
        relay_log_delivered = True
        if str(LOG_CHANNEL) not in delivered_to:
            delivered_to.append(str(LOG_CHANNEL))
        route_summaries.append(
            describe_target_route(
                LOG_CHANNEL,
                "direct_forward",
                (primary_route or {}).get("relay_source_client_kind") or (primary_route or {}).get("delivery_client_kind"),
            )
        )

    if LOG_CHANNEL and str(LOG_CHANNEL) != str(destination) and not relay_log_delivered:
        ensure_task_not_cancelled(task_id)
        log_access_map = await probe_target_access_map(client_map, LOG_CHANNEL)
        copied = None
        if primary_result and primary_route and ENABLE_LOG_FROM_DESTINATION:
            copy_client_kind = choose_log_copy_client_kind(
                (primary_route or {}).get("target_access"),
                log_access_map,
                preferred_client_kind=primary_route.get("delivery_client_kind"),
            )
            if copy_client_kind:
                copied = await copy_result_to_target(client_map.get(copy_client_kind), primary_result, LOG_CHANNEL, settings)
                ensure_task_not_cancelled(task_id)
                if copied:
                    delivered_to.append(str(LOG_CHANNEL))
                    route_summaries.append(describe_target_route(LOG_CHANNEL, "direct_copy", copy_client_kind))

        if not copied:
            try:
                log_route = await deliver_target_with_routing(
                    ui_client,
                    task_id,
                    source_msg,
                    routing_settings,
                    LOG_CHANNEL,
                    client_map=client_map,
                    source_access=source_access,
                    index_no=index_no,
                    download_state=download_state,
                    allow_download_fallback=not bool(primary_result),
                )
                log_result = log_route.get("message")
                if log_result:
                    delivered_to.append(str(LOG_CHANNEL))
                    route_summaries.append(describe_target_route(LOG_CHANNEL, log_route.get("delivery_path", ""), log_route.get("route_client_label") or log_route.get("delivery_client_kind")))
                else:
                    delivery_errors.append(f"{LOG_CHANNEL}: send returned empty response")
            except Exception as exc:
                delivery_errors.append(f"{LOG_CHANNEL}: {exc}")

    if not delivered_to:
        raise RuntimeError("Delivery failed: " + " | ".join(delivery_errors))

    return delivered_to, delivery_errors, {
        "delivery_path": str(primary_route.get("delivery_path") if primary_route else ""),
        "delivery_client_kind": str(primary_route.get("delivery_client_kind") if primary_route else ""),
        "route_client_label": str((primary_route or {}).get("route_client_label") or (primary_route or {}).get("delivery_client_kind") or ""),
        "fallback_reason": str(download_state.get("fallback_reason") or ""),
        "route_summaries": route_summaries,
        "download_path": str(download_state.get("path") or ""),
    }


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
    "show_caption",
    "toggle_caption_enabled",
    "show_caption_index_settings",
    "toggle_caption_index_enabled",
    "set_caption_index_padding",
    "set_caption_index_start",
    "set_caption_text",
    "remove_caption",
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
        board["status"] = "Cancelling" if not only_current else str(board.get("status") or "Running")
        if not only_current:
            board["cancel_all_requested"] = True
        if only_current:
            current_task_id = str(board.get("current_task_id") or "").strip()
            if current_task_id:
                task_ids.append(current_task_id)
        else:
            tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
            task_ids.extend(str(task_id) for task_id in tasks.keys())
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
        if _cancel_task_record(task_id):
            cancelled_ids.append(task_id)

    if board and board.get("batch_key") == batch_key:
        tasks = board.get("tasks", {}) if isinstance(board.get("tasks", {}), dict) else {}
        for task_id in cancelled_ids:
            row = dict(tasks.get(task_id) or {})
            row["status"] = "cancelled"
            tasks[task_id] = row
        if only_current and cancelled_ids:
            board["current_stage"] = "Cancelled"
        if not only_current and cancelled_ids:
            board["note"] = "Batch cancelled by user"
        board["tasks"] = tasks
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


def build_missing_storage_target_text(settings: dict | None) -> str:
    settings = settings or {}
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))

    if storage_mode == "gdrive":
        has_token = bool(str(settings.get("gdrive_token_path", "") or "").strip())
        has_folder = bool(str(settings.get("gdrive_folder_id", "") or "").strip())
        if not has_token and not has_folder:
            return (
                "☁️ Google Drive Storage Mode selected hai.\n\n"
                "Pehle `token.pickle` aur `Folder ID` set karo.\n"
                "/settings → token.pickle aur Folder ID"
            )
        if not has_token:
            return (
                "☁️ Google Drive Storage Mode selected hai.\n\n"
                "Pehle `token.pickle` set karo.\n"
                "/settings → token.pickle"
            )
        return (
            "☁️ Google Drive Storage Mode selected hai.\n\n"
            "Pehle `Folder ID` set karo.\n"
            "/settings → Folder ID"
        )

    if storage_mode == "rclone":
        has_config = bool(str(settings.get("rclone_config_path", "") or "").strip())
        has_remote_path = bool(str(settings.get("rclone_remote_path", "") or "").strip())
        if not has_config and not has_remote_path:
            return (
                "🗂 Rclone Storage Mode selected hai.\n\n"
                "Pehle `rclone.conf` aur `Rclone Path` set karo.\n"
                "/settings → Rclone Config aur Rclone Path"
            )
        if not has_config:
            return (
                "🗂 Rclone Storage Mode selected hai.\n\n"
                "Pehle `rclone.conf` set karo.\n"
                "/settings → Rclone Config"
            )
        return (
            "🗂 Rclone Storage Mode selected hai.\n\n"
            "Pehle `Rclone Path` set karo.\n"
            "/settings → Rclone Path"
        )

    return (
        "📍 Pehle apna destination set karo.\n\n"
        "/settings → Upload Destination me chat id ya @channelusername set karo, tabhi content save hoga."
    )


async def ask_set_destination(message, info_message=None, settings: dict | None = None):
    text = build_missing_storage_target_text(settings)
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
    if source_msg.video_note:
        return os.path.join(TEMP_DIR, f"{base_name}.mp4")
    if source_msg.sticker:
        if bool(getattr(source_msg.sticker, "is_animated", False)):
            return os.path.join(TEMP_DIR, f"{base_name}.tgs")
        if bool(getattr(source_msg.sticker, "is_video", False)):
            return os.path.join(TEMP_DIR, f"{base_name}.webm")
        return os.path.join(TEMP_DIR, f"{base_name}.webp")
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
    await client.start()
    return client


async def get_or_create_delivery_user_client(user_id: int, existing_client=None):
    if existing_client:
        return existing_client, False
    if not has_user_session(user_id):
        return None, False
    try:
        client = await get_authorized_client_for_user(user_id)
    except Exception as exc:
        debug_log(f"Delivery user client unavailable for {user_id}: {exc}")
        return None, False
    return client, bool(client)


async def safe_close_client(client_obj):
    if not client_obj:
        return
    try:
        await client_obj.stop()
        return
    except Exception:
        pass
    try:
        await client_obj.disconnect()
    except Exception:
        pass


def safe_delete_local_file(file_path: str):
    file_path = str(file_path or "").strip()
    if not file_path:
        return
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except Exception:
        pass


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
            await safe_close_client(user_client)
            raise

    return None, info, None, "bot"


def normalize_link_type(info: dict | None) -> str:
    value = str((info or {}).get("link_type") or "").strip().lower()
    if value in {"public", "private", "public_topic", "private_topic", "direct_message"}:
        return value
    return "unknown"


def source_has_protected_content(source_msg) -> bool:
    if not source_msg:
        return False
    if bool(getattr(source_msg, "has_protected_content", False)):
        return True
    chat = getattr(source_msg, "chat", None)
    chat_type = normalize_chat_type(getattr(chat, "type", ""))
    if chat_type == "forum" and bool(getattr(chat, "has_protected_content", False)):
        return True
    return False


def build_source_access_map(link_type: str, fetch_mode: str, has_user_session_client: bool) -> dict:
    link_type = str(link_type or "unknown").strip().lower()
    fetch_mode = str(fetch_mode or "bot").strip().lower()
    access = {"main_bot": False, "user_session": False, "personal_bot": False}

    if link_type == "direct_message":
        access["main_bot"] = True
        return access

    if link_type in {"private", "private_topic"}:
        access["user_session"] = bool(has_user_session_client)
        return access

    if link_type in {"public", "public_topic"}:
        access["main_bot"] = fetch_mode == "bot"
        access["user_session"] = bool(has_user_session_client)
        return access

    access["main_bot"] = fetch_mode == "bot"
    access["user_session"] = bool(has_user_session_client and fetch_mode == "user")
    return access


def normalize_chat_type(value) -> str:
    value = str(value or "").strip().lower()
    if "." in value:
        value = value.rsplit(".", 1)[-1]
    return value


def normalize_member_status(value) -> str:
    value = str(value or "").strip().lower()
    if "." in value:
        value = value.rsplit(".", 1)[-1]
    return value


def is_positive_writable_target(chat_type: str, member_status: str) -> bool:
    chat_type = normalize_chat_type(chat_type)
    member_status = normalize_member_status(member_status)

    if chat_type in {"private", "bot"}:
        return True
    if chat_type in {"group", "supergroup"}:
        return member_status in {"member", "administrator", "creator", "owner"}
    if chat_type == "channel":
        return member_status in {"administrator", "creator", "owner"}
    return False


def choose_upload_client_kind(target_access: dict, prefer_personal_upload: bool = False) -> str | None:
    target_access = target_access or {}
    priority = ["personal_bot", "main_bot", "user_session"] if prefer_personal_upload else ["main_bot", "user_session", "personal_bot"]
    for kind in priority:
        if (target_access.get(kind) or {}).get("writable"):
            return kind
    return None


def choose_cached_client_kind(source_access: dict | None, target_access: dict | None) -> str | None:
    source_access = source_access or {}
    target_access = target_access or {}
    for kind in ("main_bot", "user_session"):
        if source_access.get(kind) and (target_access.get(kind) or {}).get("writable"):
            return kind
    return None


def choose_fast_cached_delivery_client_kind(
    source_access: dict | None,
    target_access: dict | None,
    *,
    prefer_personal_upload: bool = False,
) -> str | None:
    source_access = source_access or {}
    target_access = target_access or {}
    for kind in ("main_bot", "user_session", "personal_bot"):
        if source_access.get(kind) and (target_access.get(kind) or {}).get("writable"):
            return kind
    return None


def choose_relay_route_kinds(
    source_access: dict | None,
    target_access: dict | None,
    relay_access: dict | None,
    *,
    prefer_personal_upload: bool = False,
) -> tuple[str | None, str | None]:
    source_access = source_access or {}
    target_access = target_access or {}
    relay_access = relay_access or {}

    relay_client_kind = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
    if not relay_client_kind or relay_client_kind == "user_session":
        return None, None
    if not (relay_access.get(relay_client_kind) or {}).get("writable"):
        return None, None

    for source_kind in ("user_session", "main_bot"):
        if source_kind == relay_client_kind:
            continue
        if source_access.get(source_kind) and (relay_access.get(source_kind) or {}).get("writable"):
            return source_kind, relay_client_kind
    return None, None


def choose_relay_delivery_plan(
    source_access: dict | None,
    target_access: dict | None,
    relay_access: dict | None,
    *,
    relay_target_available: bool = False,
    prefer_personal_upload: bool = False,
    bot_pm_relay_available: bool = False,
) -> dict | None:
    if relay_target_available:
        relay_source_kind, relay_client_kind = choose_relay_route_kinds(
            source_access,
            target_access,
            relay_access,
            prefer_personal_upload=prefer_personal_upload,
        )
        if relay_source_kind and relay_client_kind:
            return {
                "relay_source_client_kind": relay_source_kind,
                "relay_client_kind": relay_client_kind,
                "relay_via": "log_channel",
            }

    if bot_pm_relay_available:
        return {
            "relay_source_client_kind": "user_session",
            "relay_client_kind": "main_bot",
            "relay_via": "bot_pm",
        }

    return None


def choose_log_copy_client_kind(destination_access: dict | None, log_access: dict | None, preferred_client_kind: str | None = None) -> str | None:
    destination_access = destination_access or {}
    log_access = log_access or {}
    priority = []
    preferred = str(preferred_client_kind or "").strip().lower()
    if preferred:
        priority.append(preferred)
    for kind in ("main_bot", "user_session", "personal_bot"):
        if kind not in priority:
            priority.append(kind)

    for kind in priority:
        dest_info = destination_access.get(kind) or {}
        log_info = log_access.get(kind) or {}
        if not dest_info.get("client"):
            continue
        if not log_info.get("writable"):
            continue
        if dest_info.get("writable") or dest_info.get("resolved"):
            return kind
    return None


def build_target_delivery_plan(
    *,
    is_media: bool,
    has_cached_file_id: bool,
    has_transforming: bool,
    is_protected: bool,
    source_access: dict | None,
    target_access: dict | None,
    allow_main_bot_direct: bool,
    allow_user_session_direct: bool,
    prefer_personal_upload: bool,
    relay_access: dict | None = None,
    relay_target_available: bool = False,
    bot_pm_relay_available: bool = False,
) -> dict:
    source_access = source_access or {}
    target_access = target_access or {}
    relay_access = relay_access or {}

    plan = {
        "mode": "upload",
        "direct_client_kind": None,
        "cached_client_kind": None,
        "relay_source_client_kind": None,
        "relay_client_kind": None,
        "relay_via": "",
        "upload_client_kind": None,
        "fallback_reason": "",
        "error": "",
    }

    direct_transfer_allowed = not has_transforming and not is_protected
    if direct_transfer_allowed:
        main_direct_ready = bool(source_access.get("main_bot")) and bool((target_access.get("main_bot") or {}).get("writable"))
        user_direct_ready = bool(source_access.get("user_session")) and bool((target_access.get("user_session") or {}).get("writable"))

        if allow_main_bot_direct and main_direct_ready:
            plan["mode"] = "direct"
            plan["direct_client_kind"] = "main_bot"
            return plan
        if allow_user_session_direct and user_direct_ready:
            plan["mode"] = "direct"
            plan["direct_client_kind"] = "user_session"
            return plan

        relay_plan = choose_relay_delivery_plan(
            source_access,
            target_access,
            relay_access,
            relay_target_available=relay_target_available,
            prefer_personal_upload=prefer_personal_upload,
            bot_pm_relay_available=bot_pm_relay_available,
        )
        if relay_plan:
            plan["mode"] = "relay"
            plan.update(relay_plan)
            return plan

        cached_client_kind = choose_fast_cached_delivery_client_kind(
            source_access,
            target_access,
            prefer_personal_upload=prefer_personal_upload,
        )
        if has_cached_file_id and cached_client_kind:
            plan["mode"] = "cached"
            plan["cached_client_kind"] = cached_client_kind
            return plan

    if has_transforming:
        plan["fallback_reason"] = "transforming_settings_enabled"
    elif is_protected:
        plan["fallback_reason"] = "protected_content"
    elif source_access.get("main_bot") or source_access.get("user_session"):
        plan["fallback_reason"] = "target_not_writable_by_source_client"
    else:
        plan["fallback_reason"] = "source_not_readable"

    if not is_media:
        plan["mode"] = "text"
        plan["upload_client_kind"] = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
        if not plan["upload_client_kind"]:
            plan["error"] = "No writable target client available"
        return plan

    if not direct_transfer_allowed:
        plan["upload_client_kind"] = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
        if not plan["upload_client_kind"]:
            plan["error"] = "No writable target client available"
        return plan

    if source_access.get("main_bot") or source_access.get("user_session"):
        plan["fallback_reason"] = "target_not_writable_by_source_client"
    else:
        plan["fallback_reason"] = "source_not_readable"

    plan["upload_client_kind"] = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
    if not plan["upload_client_kind"]:
        plan["error"] = "No writable target client available"
    return plan


def build_followup_delivery_plan_after_direct_failure(
    *,
    failed_client_kind: str,
    is_media: bool,
    has_cached_file_id: bool,
    has_transforming: bool,
    is_protected: bool,
    source_access: dict | None,
    target_access: dict | None,
    allow_main_bot_direct: bool,
    allow_user_session_direct: bool,
    prefer_personal_upload: bool,
    relay_access: dict | None = None,
    relay_target_available: bool = False,
    bot_pm_relay_available: bool = False,
) -> dict:
    failed_client_kind = str(failed_client_kind or "").strip().lower()
    return build_target_delivery_plan(
        is_media=is_media,
        has_cached_file_id=has_cached_file_id,
        has_transforming=has_transforming,
        is_protected=is_protected,
        source_access=source_access,
        target_access=target_access,
        allow_main_bot_direct=bool(allow_main_bot_direct and failed_client_kind != "main_bot"),
        allow_user_session_direct=bool(allow_user_session_direct and failed_client_kind != "user_session"),
        prefer_personal_upload=prefer_personal_upload,
        relay_access=relay_access,
        relay_target_available=relay_target_available,
        bot_pm_relay_available=bot_pm_relay_available,
    )


def build_target_access_error(target, access_map: dict) -> str:
    access_map = access_map or {}
    details = []
    for kind in ("personal_bot", "main_bot", "user_session"):
        info = access_map.get(kind) or {}
        if not info.get("client"):
            continue
        if info.get("writable"):
            continue
        error_text = str(info.get("error") or "").strip()
        if error_text:
            details.append(f"{kind}: {error_text}")
        elif info.get("resolved"):
            details.append(f"{kind}: write access not confirmed")
        else:
            details.append(f"{kind}: target access unavailable")
    detail_text = " | ".join(details[:3])
    if detail_text:
        return f"No writable target client available for {target} | {detail_text}"
    return f"No writable target client available for {target}"


def describe_delivery_path(mode: str, client_kind: str | None) -> str:
    mode = str(mode or "").strip().lower()
    client_kind = str(client_kind or "").strip().lower()
    if mode == "direct":
        if client_kind == "main_bot":
            return "direct_copy"
        if client_kind == "user_session":
            return "direct_forward"
    if mode == "cached":
        return "cached_send"
    if mode == "relay":
        return "relay_copy"
    if mode == "text":
        return "text_send"
    if mode == "upload":
        return "download_upload"
    return mode or "unknown"


def describe_target_route(target, path: str, client_kind: str | None) -> str:
    target_text = str(target)
    client_text = str(client_kind or "unknown")
    if path == "direct_copy":
        return f"{target_text}: direct via {client_text}"
    if path == "direct_forward":
        return f"{target_text}: forward via {client_text}"
    if path == "cached_send":
        return f"{target_text}: cached via {client_text}"
    if path == "relay_copy":
        return f"{target_text}: relay via {client_text}"
    if path == "text_send":
        return f"{target_text}: text via {client_text}"
    if path == "download_upload":
        return f"{target_text}: upload via {client_text}"
    return f"{target_text}: {path} via {client_text}"


def select_download_client_kind(source_access: dict, client_map: dict) -> str | None:
    source_access = source_access or {}
    client_map = client_map or {}
    for kind in ("main_bot", "user_session"):
        if source_access.get(kind) and client_map.get(kind):
            return kind
    return None


def can_direct_copy(source_msg, settings: dict, fetch_mode: str = "bot") -> bool:
    if not is_media_message(source_msg):
        return False
    if has_transforming_settings(settings):
        return False
    if source_has_protected_content(source_msg):
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


async def try_direct_copy(client, source_msg, target, settings: dict, index_no: int = 0):
    target = normalize_target(target)
    await ensure_target_peer_ready(client, target)
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    errors = []
    try:
        result = normalize_message_result(await client.copy_message(
            chat_id=target,
            from_chat_id=source_msg.chat.id,
            message_id=source_msg.id,
            message_thread_id=topic_id if topic_id else None,
        ))
        if result:
            return result
    except Exception as exc:
        errors.append(f"copy: {exc}")

    try:
        result = normalize_message_result(await client.forward_messages(
            chat_id=target,
            from_chat_id=source_msg.chat.id,
            message_ids=source_msg.id,
            message_thread_id=topic_id if topic_id else None,
            drop_author=False,
        ))
        if result:
            return result
    except Exception as exc:
        errors.append(f"forward: {exc}")

    raise RuntimeError(f"Direct copy failed for destination {target} | {' | '.join(errors) if errors else 'no direct result'}")


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
    target = normalize_target(target)
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

        if source_msg.sticker:
            result = await client.send_sticker(
                chat_id=target,
                sticker=file_path,
                message_thread_id=topic_id if topic_id else None,
            )
            if not result:
                raise RuntimeError(f"Sticker upload failed for {target}")
            return result

        if source_msg.video_note:
            result = await client.send_video_note(
                chat_id=target,
                video_note=file_path,
                message_thread_id=topic_id if topic_id else None,
                duration=getattr(source_msg.video_note, "duration", None),
                length=getattr(source_msg.video_note, "length", None),
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
            )
            if not result:
                raise RuntimeError(f"Video note upload failed for {target}")
            return result

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
    target = normalize_target(target)
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
        "video_note" if source_msg.video_note else
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
        source_msg.video_note if source_msg.video_note else
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
    if not LOG_CHANNEL:
        return None
    return await copy_result_to_target(client, delivered_message, LOG_CHANNEL, settings)


async def deliver_log_channel_with_best_effort(client, task_id: str, source_msg, telegram_settings: dict, download_path: str | None = None, index_no: int = 0, fetch_mode: str = "bot", user_client=None):
    if not LOG_CHANNEL:
        return None

    try:
        if is_media_message(source_msg) and not has_transforming_settings(telegram_settings):
            if fetch_mode == "bot" and can_direct_copy(source_msg, telegram_settings, fetch_mode="bot"):
                return await try_direct_copy(client, source_msg, LOG_CHANNEL, telegram_settings, index_no=index_no)
            if fetch_mode == "user" and user_client:
                direct = await try_direct_forward_with_user_client(user_client, source_msg, LOG_CHANNEL, telegram_settings, index_no=index_no)
                if direct:
                    return direct
    except Exception:
        pass

    if not download_path:
        return await deliver_one_target(client, task_id, source_msg, telegram_settings, LOG_CHANNEL, None, index_no=index_no)

    return await upload_file_to_target(client, task_id, LOG_CHANNEL, download_path, source_msg, telegram_settings, index_no=index_no)

async def deliver_one_target(client, task_id: str, source_msg, settings: dict, target, download_path=None, index_no: int = 0):
    if download_path:
        return await upload_file_to_target(client, task_id, target, download_path, source_msg, settings, index_no=index_no)
    if is_media_message(source_msg):
        return await try_direct_copy(client, source_msg, target, settings, index_no=index_no)
    return await send_text_to_target(client, target, source_msg, settings, index_no=index_no)


async def process_source_message_transfer(client, user_id: int, message, source_msg, task_id: str, settings: dict, destination, source_label: str, info: dict | None = None, user_client=None, fetch_mode: str = "bot", disconnect_user_client: bool = False):
    download_path = None
    delivered_to = []
    delivery_errors = []
    delivery_user_client = user_client
    disconnect_delivery_user_client = False
    delivery_summary = {}

    try:
        validation_error = get_transfer_validation_error(source_msg)
        if validation_error:
            raise RuntimeError(validation_error)

        entry = build_index_entry(user_id, source_msg, source_label, info)
        idx_no = add_index_entry(entry)
        user_count_now = increase_index_user_count(user_id)
        user_index_no = get_next_user_index(user_id) - 1 or 1

        storage_mode = get_effective_storage_mode_for_message(user_id, source_msg, settings)
        if storage_mode != "telegram":
            ensure_storage_runtime_ready({**(settings or {}), "storage_mode": storage_mode})
        telegram_settings = get_primary_telegram_settings(settings)
        source_link_type = normalize_link_type(info)
        client_map = {"main_bot": client, "user_session": None, "personal_bot": None}
        source_access = build_source_access_map(source_link_type, fetch_mode, False)
        if storage_mode == "telegram":
            delivery_user_client, disconnect_delivery_user_client = await get_or_create_delivery_user_client(user_id, user_client)
            client_map["user_session"] = delivery_user_client
            client_map["personal_bot"] = await get_or_create_personal_bot_client(user_id, settings)
            source_access = build_source_access_map(source_link_type, fetch_mode, bool(delivery_user_client))
        destination_label = destination
        if storage_mode == "gdrive":
            destination_label = str(settings.get("gdrive_folder_id", "") or "")
        elif storage_mode == "rclone":
            destination_label = str(settings.get("rclone_remote_path", "") or "")

        if not is_media_message(source_msg):
            if storage_mode == "telegram":
                touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": "Telegram text route", "is_visible": True})
                await update_task_status_message(client, task_id)
                delivered_to, delivery_errors, delivery_summary = await deliver_primary_then_log_routed(
                    client,
                    task_id,
                    source_msg,
                    telegram_settings,
                    destination,
                    user_id=user_id,
                    client_map=client_map,
                    source_access=source_access,
                    index_no=user_index_no,
                )
            else:
                text_path = create_temp_text_file(source_msg, settings, index_no=user_index_no)
                try:
                    touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": f"{storage_mode.title()} text route", "is_visible": True})
                    await update_task_status_message(client, task_id)
                    delivered_to, delivery_errors, storage_info = await upload_to_storage_target(client, task_id, source_msg, telegram_settings, user_id, text_path, storage_mode, index_no=user_index_no, fetch_mode=fetch_mode, user_client=user_client)
                    result_note = f"Index {idx_no} | Count {user_count_now} | {storage_mode.title()}"
                    if storage_info:
                        result_note += f" | {storage_info}"
                finally:
                    if os.path.exists(text_path):
                        try:
                            os.remove(text_path)
                        except Exception:
                            pass
                ensure_task_not_cancelled(task_id)
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
                    "destination": str(destination_label or ""),
                    "destination_display": str(destination_label or ""),
                    "storage_mode": storage_mode,
                })
                await update_task_status_message(client, task_id, done=True)
                if str((get_task(task_id) or {}).get("mode", "")).strip().lower() != "batch":
                    await message.reply_text(auto_index_completed_text({
                        "batch_name": entry.get("file_name") or entry.get("content_type") or "Single Link Job",
                        "valid_links": 1,
                        "success": 1,
                        "failed": 0,
                        "destination": str(destination_label or "Not Set"),
                        "index_no": idx_no,
                        "user_index_no": user_index_no,
                        "link_type": entry.get("link_type") or "unknown",
                    }), disable_web_page_preview=True)
                return
        else:
            if storage_mode == "telegram":
                delivered_to, delivery_errors, delivery_summary = await deliver_primary_then_log_routed(
                    client,
                    task_id,
                    source_msg,
                    telegram_settings,
                    destination,
                    user_id=user_id,
                    client_map=client_map,
                    source_access=source_access,
                    index_no=user_index_no,
                )
                download_path = str((delivery_summary or {}).get("download_path") or "")
            else:
                touch_task(task_id, {"status": "downloading", "current_stage": "downloading", "progress_text": f"{storage_mode.title()} fallback download path" if delivery_errors else "", "is_visible": True})
                await update_task_status_message(client, task_id)
                download_hint = get_temp_download_path(source_msg)
                source_client = user_client if user_client else client
                download_path = download_hint
                try:
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
                except Exception:
                    safe_delete_local_file(download_path)
                    if download_path != download_hint:
                        safe_delete_local_file(download_hint)
                    raise
                ensure_task_not_cancelled(task_id)
                touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": f"{storage_mode.title()} upload route", "is_visible": True})
                await update_task_status_message(client, task_id)
                delivered_to, delivery_errors, storage_info = await upload_to_storage_target(client, task_id, source_msg, telegram_settings, user_id, download_path, storage_mode, index_no=user_index_no, fetch_mode=fetch_mode, user_client=user_client)

        ensure_task_not_cancelled(task_id)
        result_note = f"Index {idx_no} | Count {user_count_now}"
        if storage_mode != "telegram":
            result_note += f" | {storage_mode.title()}"
        route_summaries = (delivery_summary or {}).get("route_summaries") or []
        if route_summaries:
            result_note += " | " + " ; ".join(route_summaries[:2])
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
            "destination": str(destination_label or destination or ""),
            "destination_display": str(destination_label or destination or ""),
            "storage_mode": storage_mode,
            "delivery_path": str((delivery_summary or {}).get("delivery_path") or ""),
            "delivery_client_kind": str((delivery_summary or {}).get("delivery_client_kind") or ""),
            "route_client_label": str((delivery_summary or {}).get("route_client_label") or ""),
            "fallback_reason": str((delivery_summary or {}).get("fallback_reason") or ""),
        })
        await update_task_status_message(client, task_id, done=True)

        user_destination_text = str(destination_label or destination or settings.get("upload_destination") or "Not Set")
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
        if disconnect_delivery_user_client and delivery_user_client and delivery_user_client is not user_client:
            try:
                await safe_close_client(delivery_user_client)
            except Exception:
                pass
        if disconnect_user_client and user_client:
            try:
                await safe_close_client(user_client)
            except Exception:
                pass
        safe_delete_local_file(download_path)


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
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    destination = get_configured_storage_destination(settings)

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
        await ask_set_destination(message, checking_message, settings)
        return False

    try:
        ensure_storage_runtime_ready(settings)
    except Exception as exc:
        if batch_mode:
            return False
        await edit_or_reply(message, f"❌ {exc}", checking_message)
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
        "upload_mode": settings.get("telegram_upload_mode", settings.get("upload_mode", "media")),
        "storage_mode": storage_mode,
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
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    destination = get_configured_storage_destination(settings)

    if not destination:
        await ask_set_destination(message, settings=settings)
        return False

    try:
        ensure_storage_runtime_ready(settings)
    except Exception as exc:
        await message.reply_text(f"❌ {exc}")
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
        "upload_mode": settings.get("telegram_upload_mode", settings.get("upload_mode", "media")),
        "storage_mode": storage_mode,
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
    batch_settings = get_user_settings(user_id)
    try:
        ensure_storage_runtime_ready(batch_settings)
    except Exception as exc:
        await message.reply_text(f"❌ Batch start nahi hua: {exc}")
        return

    user_batch_limit = get_user_batch_limit(user_id)
    if len(links) > user_batch_limit:
        links = links[:user_batch_limit]

    board = await _open_batch_board(client, message, user_id, len(links), note="", batch_name=derive_batch_name(raw_text, links))
    batch_key = board.get("batch_key", "")

    success = 0
    failed = 0

    for idx, link in enumerate(links, start=1):
        board = _get_batch_board(user_id)
        if not board or board.get("batch_key") != batch_key:
            break
        if bool(board.get("cancel_all_requested")):
            board["status"] = "Cancelled"
            board["current_stage"] = "Cancelled"
            board["current_task_id"] = ""
            board["note"] = "Batch cancelled by user"
            _save_batch_board(user_id, board)
            await _refresh_batch_board_message(client, user_id, force_done=True)
            break

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
            "destination": get_configured_storage_destination(get_user_settings(user_id)),
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
            cancel_all_requested = bool(board.get("cancel_all_requested"))
            board["current_index"] = idx
            board["current_task_id"] = ""
            if cancel_all_requested:
                board["status"] = "Cancelled"
                board["current_stage"] = "Cancelled"
                board["note"] = "Batch cancelled by user"
            _save_batch_board(user_id, board)
            await _refresh_batch_board_message(client, user_id, force_done=(idx == len(links) or cancel_all_requested))
            if cancel_all_requested:
                break

        if BATCH_DELAY > 0 and idx < len(links):
            board = _get_batch_board(user_id)
            if board and bool(board.get("cancel_all_requested")):
                break
            await asyncio.sleep(BATCH_DELAY)

    board = _get_batch_board(user_id)
    if board:
        if bool(board.get("cancel_all_requested")):
            board["status"] = "Cancelled"
            board["current_stage"] = "Cancelled"
            board["note"] = "Batch cancelled by user"
        else:
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
        await message.reply_text(admin_stats_text(get_detailed_stats()), disable_web_page_preview=True)
        return True

    if lowered.startswith("/users"):
        users = get_all_users_page(limit=50, offset=0)
        await message.reply_text(all_users_text(users, title="All Users"), disable_web_page_preview=True)
        return True

    if lowered.startswith("/recent_users"):
        await message.reply_text(all_users_text(get_recent_users(20), title="Recent Users"), disable_web_page_preview=True)
        return True

    if lowered.startswith("/set_batch_limit"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            await message.reply_text("Use: /set_batch_limit user_id 500")
            return True
        record = save_user_limit_record(int(parts[1]), {"batch_limit": int(parts[2])})
        await message.reply_text(f"✅ Batch limit updated\nUser: `{parts[1]}`\nBatch Limit: `{record.get('batch_limit', 0)}`")
        return True

    if lowered.startswith("/set_task_limit"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            await message.reply_text("Use: /set_task_limit user_id 10")
            return True
        record = save_user_limit_record(int(parts[1]), {"task_limit": int(parts[2])})
        await message.reply_text(f"✅ Task limit updated\nUser: `{parts[1]}`\nTask Limit: `{record.get('task_limit', 0)}`")
        return True

    if lowered.startswith("/set_storage_access"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /set_storage_access user_id telegram,gdrive,rclone,personal_bot")
            return True
        record = save_user_limit_record(int(parts[1]), {"allowed_storage_modes": parts[2].strip()})
        await message.reply_text(f"✅ Storage access updated\nUser: `{parts[1]}`\nModes: `{record.get('allowed_storage_modes', '')}`")
        return True

    if lowered.startswith("/premium_status"):
        parts = (message.text or "").split(maxsplit=1)
        target = user_id
        if len(parts) > 1 and parts[1].strip().isdigit():
            target = int(parts[1].strip())
        expiry = get_premium_expiry_text(target) or "No expiry"
        status = "Premium 💎" if is_premium_user(target) else "Free 🆓"
        plan_name = get_user_plan_name(target)
        features = get_user_plan_features(target)
        feature_text = "\n".join([f"- {item}" for item in features]) if features else "Admin ne custom plan features set nahi kiye."
        await message.reply_text(
            f"User `{target}`\nStatus: **{status}**\nPlan: **{plan_name}**\nExpiry: `{expiry}`\n\n**Plan Features**\n{feature_text}"
        )
        return True

    if lowered.startswith("/plan_status"):
        parts = (message.text or "").split(maxsplit=1)
        target = user_id
        if len(parts) > 1 and parts[1].strip().isdigit():
            target = int(parts[1].strip())
        expiry = get_premium_expiry_text(target) or "No expiry"
        status = "Premium 💎" if is_premium_user(target) else "Free 🆓"
        plan_name = get_user_plan_name(target)
        features = get_user_plan_features(target)
        feature_text = "\n".join([f"- {item}" for item in features]) if features else "Admin ne custom plan features set nahi kiye."
        await message.reply_text(
            f"🪪 Plan Status\n\nUser: `{target}`\nStatus: **{status}**\nPlan: **{plan_name}**\nExpiry: `{expiry}`\n\n**Plan Features**\n{feature_text}"
        )
        return True

    if lowered.startswith("/set_plan_features"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /set_plan_features user_id feature 1 | feature 2 | feature 3")
            return True
        target = int(parts[1])
        record = set_user_plan_features(target, parts[2], updated_by=user_id)
        features = get_user_plan_features(target)
        await message.reply_text(
            f"✅ Plan features updated\nUser: `{target}`\nPlan: **{get_user_plan_name(target)}**\nItems: `{len(features)}`"
        )
        return True

    if lowered.startswith("/clear_plan_features"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text("Use: /clear_plan_features user_id")
            return True
        target = int(parts[1].strip())
        set_user_plan_features(target, "", updated_by=user_id)
        await message.reply_text(f"🧹 Plan features cleared for `{target}`")
        return True

    if lowered.startswith("/set_plan"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /set_plan user_id Gold")
            return True
        target = int(parts[1])
        plan_name = parts[2].strip()
        if not plan_name:
            await message.reply_text("Plan name empty nahi ho sakta.")
            return True
        set_user_plan_name(target, plan_name, updated_by=user_id)
        await message.reply_text(
            f"✅ Plan name updated\nUser: `{target}`\nPlan: **{get_user_plan_name(target)}**"
        )
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
    storage_mode = normalize_storage_mode(s.get("storage_mode", "telegram"))

    if storage_mode != "telegram" and is_telegram_only_settings_callback(data):
        try:
            await callback_query.message.edit_text(
                settings_home_text(user_id),
                reply_markup=build_settings_home_markup(user_id),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer(build_storage_mode_locked_callback_text(storage_mode), show_alert=True)
        return

    if data == "admin_stats":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        try:
            await callback_query.message.edit_text(admin_stats_text(get_detailed_stats()), reply_markup=admin_panel_buttons(), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Stats refreshed")
        return

    if data == "show_admin_users":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        users = get_all_users_page(limit=50, offset=0)
        try:
            await callback_query.message.edit_text(all_users_text(users, title="All Users"), reply_markup=admin_panel_buttons(), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("All users shown")
        return

    if data == "admin_recent_users":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        try:
            await callback_query.message.edit_text(all_users_text(get_recent_users(20), title="Recent Users"), reply_markup=admin_panel_buttons(), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Recent users shown")
        return

    if data == "show_storage_mode":
        allowed = [mode for mode in ["telegram", "gdrive", "rclone"] if user_can_use_storage_mode(user_id, mode)] or ["telegram"]
        try:
            await callback_query.message.edit_text(
                advanced_settings_text(user_id),
                reply_markup=storage_mode_buttons(s.get("storage_mode", "telegram"), allowed_modes=allowed),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "cycle_storage_mode":
        current_mode = normalize_storage_mode(s.get("storage_mode", "telegram"))
        allowed = [mode for mode in ["telegram", "gdrive", "rclone"] if user_can_use_storage_mode(user_id, mode)] or ["telegram"]
        if len(allowed) == 1 and current_mode == allowed[0]:
            only_mode = allowed[0]
            await callback_query.answer(
                f"Storage Mode abhi {only_mode} par locked hai. Allowed: {', '.join(allowed)}",
                show_alert=True,
            )
            return
        new_mode = get_next_allowed_storage_mode(current_mode, allowed)
        update_user_settings(user_id, {"storage_mode": new_mode})
        updated_settings = get_user_settings(user_id)
        try:
            await callback_query.message.edit_text(settings_home_text(user_id), reply_markup=build_settings_home_markup(user_id), disable_web_page_preview=True)
        except Exception:
            pass
        reminder = build_missing_storage_target_text(updated_settings) if new_mode in {"gdrive", "rclone"} else ""
        answer_text = f"Storage Mode: {new_mode}"
        if reminder:
            answer_text = reminder.replace("`", "")
        await callback_query.answer(answer_text[:180], show_alert=bool(reminder))
        return

    if data.startswith("set_storage_mode:"):
        mode = normalize_storage_mode(data.split(":",1)[1])
        if not user_can_use_storage_mode(user_id, mode):
            await callback_query.answer(f"Allowed: {', '.join(get_user_allowed_storage_modes(user_id))}", show_alert=True)
            return
        update_user_settings(user_id, {"storage_mode": mode})
        updated_settings = get_user_settings(user_id)
        try:
            await callback_query.message.edit_text(settings_home_text(user_id), reply_markup=build_settings_home_markup(user_id), disable_web_page_preview=True)
        except Exception:
            pass
        reminder = build_missing_storage_target_text(updated_settings) if mode in {"gdrive", "rclone"} else ""
        answer_text = f"Storage Mode: {mode}"
        if reminder:
            answer_text = reminder.replace("`", "")
        await callback_query.answer(answer_text[:180], show_alert=bool(reminder))
        return

    if data == "show_telegram_upload_mode":
        try:
            await callback_query.message.edit_text(upload_mode_text(user_id), reply_markup=upload_mode_buttons(get_user_telegram_upload_mode(user_id)), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_gdrive_settings":
        try:
            await callback_query.message.edit_text(gdrive_text(user_id), reply_markup=gdrive_buttons(bool(s.get("gdrive_token_path")), bool(s.get("gdrive_folder_id"))), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_rclone_settings":
        try:
            await callback_query.message.edit_text(rclone_text(user_id), reply_markup=rclone_buttons(bool(s.get("rclone_config_path")), bool(s.get("rclone_remote_path"))), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "show_personal_bot_settings":
        try:
            await callback_query.message.edit_text(personal_bot_text(user_id), reply_markup=personal_bot_buttons(bool(s.get("personal_bot_token")), str(s.get("bot_delivery_mode", "main")).lower()=="personal"), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "set_personal_bot_token":
        set_user_state(user_id, "set_personal_bot_token")
        await callback_query.message.reply_text("🤖 Ab BotFather wala bot token bhejo.\nExample: `123456:ABCDEF...`\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    if data == "show_route_template":
        try:
            await callback_query.message.edit_text(route_template_text(user_id), reply_markup=route_template_buttons(s.get("route_template", "off")), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return

    if data.startswith("set_route_template:"):
        template = str(data.split(":",1)[1] or "off").strip().lower()
        if template not in {"off", "smart", "docs_to_gdrive", "media_to_telegram", "archives_to_rclone"}:
            template = "off"
        update_user_settings(user_id, {"route_template": template})
        try:
            await callback_query.message.edit_text(route_template_text(user_id), reply_markup=route_template_buttons(template), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer(f"Template: {template}")
        return

    if data == "set_gdrive_token_file":
        set_user_state(user_id, "set_gdrive_token_file")
        await callback_query.message.reply_text("☁️ Ab token.pickle file bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    if data == "set_gdrive_folder_id":
        set_user_state(user_id, "set_gdrive_folder_id")
        await callback_query.message.reply_text("☁️ Ab Google Drive folder ID bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    if data == "clear_gdrive_settings":
        update_user_settings(user_id, {"gdrive_folder_id": "", "gdrive_token_path": "", "gdrive_last_file_link": ""})
        try:
            await callback_query.message.edit_text(gdrive_text(user_id), reply_markup=gdrive_buttons(False, False), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("GDrive cleared")
        return

    if data == "validate_gdrive_settings":
        try:
            result = await validate_gdrive_settings_for_user(get_user_settings(user_id))
            await callback_query.answer(f"✅ {result.get('name','ok')}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"❌ {e}", show_alert=True)
        return

    if data == "set_rclone_config_file":
        set_user_state(user_id, "set_rclone_config_file")
        await callback_query.message.reply_text("🗂 Ab rclone.conf file bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    if data == "set_rclone_remote_path":
        set_user_state(user_id, "set_rclone_remote_path")
        await callback_query.message.reply_text("🗂 Ab remote path bhejo. Example: myremote:Telegram/Folder\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    if data == "clear_rclone_settings":
        update_user_settings(user_id, {"rclone_config_path": "", "rclone_remote_path": "", "rclone_last_file_path": ""})
        try:
            await callback_query.message.edit_text(rclone_text(user_id), reply_markup=rclone_buttons(False, False), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Rclone cleared")
        return

    if data == "validate_rclone_settings":
        try:
            result = await validate_rclone_settings_for_user(get_user_settings(user_id))
            await callback_query.answer(f"✅ {result.get('path','ok')}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"❌ {e}", show_alert=True)
        return

    if data == "validate_current_destination":
        await callback_query.answer("Ye button settings se hata diya gaya hai.", show_alert=True)
        return

    if data == "validate_personal_bot":
        token = str(s.get("personal_bot_token", "") or "").strip()
        if not token:
            await callback_query.answer("Bot token missing", show_alert=True)
            return
        try:
            me = await validate_personal_bot_token(user_id, token)
            update_user_settings(user_id, {"personal_bot_username": getattr(me, "username", "") or ""})
            await callback_query.answer(f"✅ @{getattr(me, 'username', 'unknown')}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"❌ {e}", show_alert=True)
        return

    if data == "toggle_personal_bot_mode":
        mode = "personal" if str(s.get("bot_delivery_mode", "main")).lower() != "personal" else "main"
        update_user_settings(user_id, {"bot_delivery_mode": mode})
        try:
            await callback_query.message.edit_text(personal_bot_text(user_id), reply_markup=personal_bot_buttons(bool(get_user_settings(user_id).get("personal_bot_token")), mode=="personal"), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer(f"Delivery bot: {mode}")
        return

    if data == "remove_personal_bot":
        update_user_settings(user_id, {"personal_bot_token": "", "personal_bot_username": "", "bot_delivery_mode": "main"})
        await cleanup_personal_bot_client(user_id)
        try:
            await callback_query.message.edit_text(personal_bot_text(user_id), reply_markup=personal_bot_buttons(False, False), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Personal bot removed")
        return

    if data == "show_id_help":
        await callback_query.answer("/id ko us channel/group/topic me chalao jahan bot admin ho", show_alert=True)
        return

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
        batch_key = data.split(":", 1)[1]
        cancelled_ids = _cancel_batch_tasks(user_id, batch_key, only_current=True, return_task_ids=True)
        if cancelled_ids:
            for task_id in cancelled_ids:
                await update_task_status_message(client, task_id, done=True)
            await _refresh_batch_board_message(client, user_id)
            await callback_query.answer(f"Cancelled {len(cancelled_ids)} task")
        else:
            await callback_query.answer("No running task", show_alert=True)
        return

    if data.startswith("batch_cancel_all:"):
        batch_key = data.split(":", 1)[1]
        cancelled_ids = _cancel_batch_tasks(user_id, batch_key, only_current=False, return_task_ids=True)
        if cancelled_ids:
            for task_id in cancelled_ids:
                await update_task_status_message(client, task_id, done=True)
            await _refresh_batch_board_message(client, user_id)
            await callback_query.answer(f"Cancelled {len(cancelled_ids)} task(s)")
        else:
            await callback_query.answer("No active batch task", show_alert=True)
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
            new_mode = "media"
        update_user_settings(user_id, {"upload_mode": new_mode, "telegram_upload_mode": new_mode})
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("✅ Telegram upload mode updated")
        return

    if data == "show_advanced_settings":
        try:
            await callback_query.message.edit_text(
                advanced_settings_text(user_id),
                reply_markup=advanced_settings_buttons(
                    has_session=has_user_session(user_id),
                    has_personal_bot=bool(s.get("personal_bot_token")),
                    is_admin=is_admin(user_id),
                    storage_mode=s.get("storage_mode", "telegram"),
                ),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    if data == "clear_replace_words_file":
        updated = update_replace_rule_settings(user_id, s, file_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(bool(get_file_replace_rules(updated)), bool(get_caption_replace_rules(updated)))
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("File rules cleared")
        return

    if data == "clear_replace_words_caption":
        updated = update_replace_rule_settings(user_id, s, caption_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(bool(get_file_replace_rules(updated)), bool(get_caption_replace_rules(updated)))
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Caption rules cleared")
        return

    if data == "toggle_replace_words":
        await callback_query.answer("File aur caption rules alag set/clear karo")
        return

    if data == "clear_replace_words":
        update_replace_rule_settings(user_id, s, file_rules="", caption_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(False, False)
        try:
            await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Rules cleared")
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
        if task and _cancel_task_record(task_id):
            await update_task_status_message(client, task_id, done=True)
            if str(task.get("mode") or "").strip().lower() == "batch" and str(task.get("batch_key") or "").strip():
                await _refresh_batch_board_message(client, user_id)
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

    if data == "show_settings_home":
        try:
            await callback_query.message.edit_text(
                settings_home_text(user_id),
                reply_markup=build_settings_home_markup(user_id),
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
        users = get_all_users_page(limit=50, offset=0)
        text = all_users_text(users, title="All Users")
        try:
            await callback_query.message.edit_text(text, reply_markup=admin_panel_buttons(), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("All users shown")
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

    if data == "show_upload_mode":
        text = build_upload_mode_message(user_id)
        kb = upload_mode_buttons(get_user_telegram_upload_mode(user_id))

    elif data == "toggle_upload_mode":
        current = str(s.get("telegram_upload_mode", s.get("upload_mode", "media")) or "media").strip().lower()
        new_mode = "document" if current == "media" else "media"
        update_user_settings(user_id, {"upload_mode": new_mode, "telegram_upload_mode": new_mode})
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
        kb = replace_words_buttons(bool(get_file_replace_rules(s)), bool(get_caption_replace_rules(s)))

    elif data == "set_replace_words":
        set_user_state(user_id, "set_replace_words")
        await callback_query.message.reply_text("🔁 Ab combined remove/replace rules bhejo.\nYe file aur caption dono par apply hongi.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "admin_plan_help":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return
        try:
            await callback_query.message.edit_text(
                admin_plan_help_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    elif data == "set_replace_words_file":
        set_user_state(user_id, "set_replace_words_file")
        await callback_query.message.reply_text("🔁 Ab file remove/replace rules bhejo.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "set_replace_words_caption":
        set_user_state(user_id, "set_replace_words_caption")
        await callback_query.message.reply_text("🔁 Ab caption remove/replace rules bhejo.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return

    elif data == "remove_replace_words":
        update_replace_rule_settings(user_id, s, file_rules="", caption_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(False, False)

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

    elif data == "toggle_upload_mode_legacy":
        current_mode = str(s.get("telegram_upload_mode", s.get("upload_mode", "media")) or "media").strip().lower()
        new_mode = "media" if current_mode == "document" else "document"
        update_user_settings(user_id, {"upload_mode": new_mode, "telegram_upload_mode": new_mode})
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

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


@app.on_message(filters.command("id") & (filters.group | filters.channel))
async def id_command_in_chat(client, message):
    topic_id = getattr(message, "message_thread_id", None)
    try:
        chat = await client.get_chat(message.chat.id)
        await message.reply_text(id_info_text(chat, topic_id), disable_web_page_preview=True)
    except Exception as e:
        await message.reply_text(f"❌ ID fetch failed: {e}")


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

    if lowered.startswith("/set_bot"):
        token = (message.text or "").split(maxsplit=1)
        if len(token) < 2:
            await message.reply_text("Use: /set_bot <bot_token>")
            return
        bot_token = token[1].strip()
        try:
            me = await validate_personal_bot_token(user_id, bot_token)
            await cleanup_personal_bot_client(user_id)
            update_user_settings(user_id, {"personal_bot_token": bot_token, "personal_bot_username": getattr(me, "username", "") or "", "bot_delivery_mode": "personal"})
            await message.reply_text(f"✅ Personal bot saved: @{getattr(me, 'username', 'unknown')}")
        except Exception as e:
            await message.reply_text(f"❌ Personal bot invalid: {e}")
        return

    if lowered.startswith("/bot_status"):
        s = get_user_settings(user_id)
        await message.reply_text(personal_bot_text(user_id), disable_web_page_preview=True)
        return

    if lowered.startswith("/remove_bot"):
        update_user_settings(user_id, {"personal_bot_token": "", "personal_bot_username": "", "bot_delivery_mode": "main"})
        await cleanup_personal_bot_client(user_id)
        await message.reply_text("🗑 Personal bot removed.")
        return

    if lowered.startswith("/id"):
        try:
            chat = await client.get_chat(message.chat.id)
            await message.reply_text(id_info_text(chat, getattr(message, 'message_thread_id', None)), disable_web_page_preview=True)
        except Exception as e:
            await message.reply_text(f"❌ ID fetch failed: {e}")
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
        "/cancelall",
        "/cancel_all",
        "/start",
        "/help",
        "/plan",
        "/terms",
        "/ping",
        "/login",
        "/login_status",
        "/logout",
        "/my_tasks",
        "/set_bot",
        "/bot_status",
        "/remove_bot",
        "/id",
        "/recent_users",
        "/set_batch_limit",
        "/set_task_limit",
        "/set_storage_access",
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

    if state in {"set_gdrive_token_file", "set_rclone_config_file"} and message.document and not lowered.startswith("/cancel"):
        dest_path = derive_gdrive_token_dest(user_id, message.document.file_name or "token.pickle") if state == "set_gdrive_token_file" else derive_rclone_config_dest(user_id, message.document.file_name or "rclone.conf")
        try:
            result = await message.download(file_name=dest_path)
            final_path = resolve_downloaded_path(dest_path, result)
            ensure_valid_downloaded_file(final_path)
            if state == "set_gdrive_token_file":
                update_user_settings(user_id, {"gdrive_token_path": final_path})
                success_text = "✅ token.pickle save ho gayi.\n\n/settings bhejo dekhne ke liye."
            else:
                update_user_settings(user_id, {"rclone_config_path": final_path})
                success_text = "✅ rclone config file save ho gayi.\n\n/settings bhejo dekhne ke liye."
            clear_user_state(user_id)
            await message.reply_text(success_text)
        except Exception as e:
            await message.reply_text(f"❌ File save failed: {e}")
        return

    if not state and is_media_message(message):
        if capture_relay_bridge_message(user_id, message):
            debug_log(f"Captured relay bridge message {getattr(message, 'id', 0)} for user {user_id}")
            return
        if should_ignore_direct_message_payload(user_id, message):
            debug_log(f"Ignored relay bridge message {getattr(message, 'id', 0)} for user {user_id}")
            return
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

            if setting_key == "personal_bot_token":
                try:
                    me = await validate_personal_bot_token(user_id, value)
                    await cleanup_personal_bot_client(user_id)
                    update_user_settings(
                        user_id,
                        {
                            "personal_bot_token": value,
                            "personal_bot_username": getattr(me, "username", "") or "",
                            "bot_delivery_mode": "personal",
                        },
                    )
                    clear_user_state(user_id)
                    await message.reply_text(f"✅ Personal bot save ho gaya: @{getattr(me, 'username', 'unknown')}\n\n/settings bhejo dekhne ke liye.")
                except Exception as e:
                    await message.reply_text(f"❌ Personal bot invalid: {e}\n\n/cancel bhej kar cancel kar sakte ho.")
                return

            if setting_key == "replace_words":
                update_replace_rule_settings(user_id, get_user_settings(user_id), file_rules=value, caption_rules=value)
            elif setting_key == "replace_words_file":
                update_replace_rule_settings(user_id, get_user_settings(user_id), file_rules=value)
            elif setting_key == "replace_words_caption":
                update_replace_rule_settings(user_id, get_user_settings(user_id), caption_rules=value)
            else:
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

    if lowered.startswith("/cancelall") or lowered.startswith("/cancel_all"):
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        cancelled_ids = []
        board = _get_batch_board(user_id)
        if board and str(board.get("batch_key") or "").strip():
            cancelled_ids.extend(_cancel_batch_tasks(user_id, board.get("batch_key"), only_current=False, return_task_ids=True))
        cancelled_ids.extend(_cancel_active_tasks_for_user(user_id, limit=2000, return_task_ids=True))
        cancelled_ids = list(dict.fromkeys([task_id for task_id in cancelled_ids if str(task_id).strip()]))
        for task_id in cancelled_ids:
            await update_task_status_message(client, task_id, done=True)
        if _get_batch_board(user_id):
            await _refresh_batch_board_message(client, user_id)
        if cancelled_ids:
            await message.reply_text(f"🧹 {len(cancelled_ids)} active task(s) cancel kar diye gaye.")
        else:
            await message.reply_text("❌ Koi active task nahi mila.")
        return

    if lowered.startswith("/cancel"):
        had_input_state = bool(state)
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        cancelled_ids = []
        board = _get_batch_board(user_id)
        if board and str(board.get("current_task_id") or "").strip():
            cancelled_ids.extend(_cancel_batch_tasks(user_id, board.get("batch_key"), only_current=True, return_task_ids=True))
        cancelled_ids.extend(_cancel_active_tasks_for_user(user_id, limit=1, return_task_ids=True))
        cancelled_ids = list(dict.fromkeys([task_id for task_id in cancelled_ids if str(task_id).strip()]))
        for task_id in cancelled_ids:
            await update_task_status_message(client, task_id, done=True)
        if cancelled_ids and _get_batch_board(user_id):
            await _refresh_batch_board_message(client, user_id)
        if had_input_state and cancelled_ids:
            await message.reply_text("❌ Current input mode aur current running task cancel kar diya gaya.")
        elif had_input_state:
            await message.reply_text("❌ Current input mode cancel kar diya gaya.")
        elif cancelled_ids:
            await message.reply_text("🛑 Current running task cancel kar diya gaya.")
        else:
            await message.reply_text("❌ Koi active input mode ya running task nahi mila.")
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
        await message.reply_text(help_text(is_admin(user_id)))
        return

    if lowered.startswith("/plan"):
        await message.reply_text(plan_text(user_id))
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
