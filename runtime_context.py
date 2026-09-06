from __future__ import annotations

import contextlib
import os
import re
import uuid
import time
import asyncio
import sys
import site
from pathlib import Path
import config as cfg

from pyrogram import Client, filters
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
    FORCE_SUB_STRICT,
    OWNER_ID,
    ADMIN_IDS,
    LOG_CHANNEL,
    TEMP_DIR,
    BATCH_DELAY,
    DEFAULT_DESTINATION,
    ENABLE_DIRECT_PUBLIC_COPY,
    ENABLE_DIRECT_PRIVATE_COPY,
    ENABLE_LOG_FROM_DESTINATION,
    AUTO_RETRY_FAILED_TASKS,
    MAX_RETRY_ATTEMPTS,
    RETRY_DELAY_SECONDS,
    ENABLE_UPLOAD_PROGRESS,
)

from keyboards import (
    join_required_buttons,
    start_buttons,
    settings_home_buttons,
    advanced_settings_buttons,
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
    admin_plans_list_markup,
    admin_plan_action_markup,
    admin_payment_gateway_markup,
    admin_pending_orders_markup,
    admin_order_detail_markup,
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
    admin_manage_plans_text,
    admin_plan_detail_text,
    admin_payment_gateway_text,
    admin_premium_help_text,
    admin_plan_help_text,
    gdrive_text,
    rclone_text,
    personal_bot_text,
    route_template_text,
    admin_stats_text,
    all_users_text,
    id_info_text,
)

from storage import (
    WAITING_KEYS,
    add_index_entry,
    ban_user,
    cleanup_runtime_artifacts,
    clear_user_state,
    get_caption_settings_for_mode,
    get_recent_users,
    get_storage_runtime_status,
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
    save_user_limit_record,
    get_user_allowed_storage_modes,
    user_can_use_storage_mode,
    get_user_telegram_upload_mode,
    create_backup_snapshot,
    restore_backup_snapshot,
    get_supabase_status,
)
from features.delivery_planner import (
    build_followup_delivery_plan_after_direct_failure,
    build_source_access_map,
    build_target_access_error,
    build_target_delivery_plan,
    choose_cached_client_kind,
    choose_fast_cached_delivery_client_kind,
    choose_log_copy_client_kind,
    choose_relay_delivery_plan,
    choose_relay_route_kinds,
    choose_upload_client_kind,
    describe_delivery_path,
    describe_target_route,
    get_transfer_validation_error,
    has_transferable_content,
    is_positive_writable_target,
    normalize_chat_type,
    normalize_link_type,
    normalize_member_status,
    select_download_client_kind,
    source_has_protected_content,
)
from features.format_helpers import human_bytes, human_eta, human_speed, progress_bar
from features.media_transforms import (
    build_final_caption,
    build_final_filename,
    build_final_text,
    build_storage_annotation,
    build_template_context,
    ensure_non_empty_text,
    ensure_valid_downloaded_file,
    get_parse_mode,
    has_transforming_settings,
    is_media_like_message,
    is_media_message,
    render_template,
    resolve_downloaded_path,
)
from features.message_helpers import (
    IGNORED_DIRECT_MESSAGES,
    IGNORED_DIRECT_SIGNATURES,
    RELAY_BRIDGE_WAITERS,
    RECENT_PRIVATE_UPDATES,
    RECENT_CALLBACK_UPDATES,
    UPDATE_DEDUPE_TTL_SECONDS,
    is_duplicate_private_update,
    is_duplicate_callback_update,
    mark_ignored_direct_message,
    should_ignore_direct_message,
    get_message_media_kind,
    get_message_unique_id,
    build_message_relay_signature,
    mark_ignored_direct_signature,
    should_ignore_direct_message_payload,
    capture_relay_bridge_message,
    wait_for_relay_bridge_message,
    get_message_file_name,
    get_message_file_size,
    get_message_duration,
    get_message_file_id,
)
from features.settings_helpers import (
    normalize_target,
    safe_topic_id,
    make_task_id,
    sanitize_filename,
    get_file_replace_rules,
    get_caption_replace_rules,
    update_replace_rule_settings,
)
from features.storage_mode_helpers import (
    analyze_telegram_media_delivery,
    build_missing_storage_target_text,
    ensure_storage_runtime_ready,
    get_configured_storage_destination,
    get_effective_storage_mode_for_message,
    get_next_allowed_storage_mode,
    get_primary_telegram_settings,
    normalize_storage_mode,
)

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
    workers=8,
)

TEMP_LOGIN_CLIENTS = {}
FORCE_SUB_CACHE_TTL_SECONDS = 600.0
FORCE_SUB_BLOCKED_CACHE_TTL_SECONDS = 120.0
FORCE_SUB_STATUS_CACHE: dict[int, dict[str, float | bool]] = {}
TARGET_ACCESS_CACHE: dict[tuple[int, str, str], dict] = {}
TARGET_PEER_READY_CACHE: dict[tuple[int, str], float] = {}

GLOBAL_MAX_RUNNING_TASKS = int(getattr(cfg, "GLOBAL_MAX_RUNNING_TASKS", 3) or 3)
QUEUE_POLL_INTERVAL = float(getattr(cfg, "QUEUE_POLL_INTERVAL", 2.0) or 2.0)
ENABLE_TASK_DEBUG = bool(getattr(cfg, "ENABLE_TASK_DEBUG", False))
TASK_CARD_HIDE_DELAY = int(getattr(cfg, "TASK_CARD_HIDE_DELAY", 8) or 8)
PROGRESS_UPDATE_INTERVAL = float(getattr(cfg, "PROGRESS_UPDATE_INTERVAL", 5.0) or 5.0)
PROGRESS_BAR_LENGTH = int(getattr(cfg, "PROGRESS_BAR_LENGTH", 10) or 10)
SHOW_PROGRESS_BAR = bool(getattr(cfg, "SHOW_PROGRESS_BAR", True))
ENABLE_UPLOAD_PROGRESS = bool(getattr(cfg, "ENABLE_UPLOAD_PROGRESS", SHOW_PROGRESS_BAR))
SHOW_REALTIME_SPEED = bool(getattr(cfg, "SHOW_REALTIME_SPEED", True))
SHOW_REALTIME_ETA = bool(getattr(cfg, "SHOW_REALTIME_ETA", True))
SHOW_TRANSFERRED_SIZE = bool(getattr(cfg, "SHOW_TRANSFERRED_SIZE", True))
TARGET_ACCESS_CACHE_TTL = float(getattr(cfg, "TARGET_ACCESS_CACHE_TTL", 45.0) or 45.0)
TARGET_PEER_READY_TTL = float(getattr(cfg, "TARGET_PEER_READY_TTL", 90.0) or 90.0)

TASK_QUEUE: asyncio.Queue = asyncio.Queue(maxsize=300)
TASK_WORKERS = []
TASK_WORKERS_STARTED = False
TASK_WORKER_LOCK = None
STORAGE_MAINTENANCE_TASK = None


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


def is_admin(user_id: int) -> bool:
    return user_id == OWNER_ID or user_id in ADMIN_IDS


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


def iter_optional_topic_ids(topic_id) -> list[int | None]:
    normalized = safe_topic_id(topic_id)
    if normalized:
        return [normalized, None]
    return [None]


async def execute_topic_aware_send(send_factory, topic_id):
    last_error = None
    for message_thread_id in iter_optional_topic_ids(topic_id):
        kwargs = {}
        if message_thread_id:
            kwargs["message_thread_id"] = message_thread_id
        try:
            return await send_factory(**kwargs)
        except Exception as exc:
            last_error = exc
    if last_error:
        raise last_error
    return None
