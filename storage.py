
import base64
import json
import os
import re
import time
import threading
import atexit
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from pathlib import Path
from threading import Lock
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request
from features.storage_caption_helpers import (
    CAPTION_MODE_KEYS as _CAPTION_MODE_KEYS,
    get_caption_setting_keys as _get_caption_setting_keys_impl,
    get_caption_settings_for_mode as _get_caption_settings_for_mode_impl,
    normalize_storage_mode_key as _normalize_storage_mode_key_impl,
)
from features.storage_marks_helpers import (
    get_settings_marks_from_settings as _get_settings_marks_from_settings_impl,
    get_user_storage_mode_from_settings as _get_user_storage_mode_from_settings_impl,
    get_user_telegram_upload_mode_from_settings as _get_user_telegram_upload_mode_from_settings_impl,
)
from features.storage_reporting_helpers import (
    analyze_batch_input_impl as _analyze_batch_input_impl,
    get_admin_overview_impl as _get_admin_overview_impl,
)
from features.storage_stats_helpers import get_detailed_stats_impl as _get_detailed_stats_impl

from config import (
    SETTINGS_FILE,
    STATE_FILE,
    USERS_FILE,
    BANNED_FILE,
    INDEX_FILE,
    INDEX_STATE_FILE,
    SESSION_STORE_FILE,
    TASKS_FILE,
    PREMIUM_FILE,
    STATS_FILE,
    FAILED_TASKS_FILE,
    BROADCAST_LOG_FILE,
    USER_LIMITS_FILE,
    DATA_DIR,
    TEMP_DIR,
    CACHE_DIR,
    BACKUP_DIR,
    DEFAULT_UPLOAD_MODE,
    DEFAULT_PLAN_NAME,
    DEFAULT_PREMIUM_PLAN_NAME,
    FREE_MAX_BATCH_LINKS,
    PREMIUM_MAX_BATCH_LINKS,
    FREE_MAX_TASKS_PER_USER,
    PREMIUM_MAX_TASKS_PER_USER,
    ENABLE_LOCAL_FALLBACK,
    SYNC_LOCAL_TO_SUPABASE,
    SUPABASE_URL,
    SUPABASE_KEY,
    SUPABASE_SERVICE_ROLE_KEY,
    SUPABASE_DB_URL,
    SUPABASE_TIMEOUT,
    SUPABASE_SCHEMA,
    SUPABASE_USERS_TABLE,
    SUPABASE_SETTINGS_TABLE,
    SUPABASE_STATE_TABLE,
    SUPABASE_PREMIUM_TABLE,
    SUPABASE_TASKS_TABLE,
    SUPABASE_STATS_TABLE,
    SUPABASE_BROADCAST_TABLE,
    SUPABASE_BANNED_TABLE,
    SUPABASE_INDEX_TABLE,
    SUPABASE_FAILED_TASKS_TABLE,
    SUPABASE_USER_LIMITS_TABLE,
    SUPABASE_SESSIONS_TABLE,
    SUPABASE_INDEX_STATE_TABLE,
    PREMIUM_GRACE_HOURS,
    TASK_STATUS_TTL_MINUTES,
    TASK_CLEANUP_AFTER_HOURS,
    TEMP_FILE_RETENTION_HOURS,
    BACKUP_RETENTION_COUNT,
    PERSISTENT_DATA_DIR,
    DEFAULT_STORAGE_MODE,
    FREE_STORAGE_MODES,
    PREMIUM_STORAGE_MODES,
    PRO_STORAGE_MODES,
)

_LOCK = Lock()
DATA_DIR = DATA_DIR or (os.path.dirname(SETTINGS_FILE) or "data")


DEFAULT_SETTINGS = {
    "upload_mode": DEFAULT_UPLOAD_MODE if str(DEFAULT_UPLOAD_MODE).lower() in {"media", "document"} else "media",
    "telegram_upload_mode": DEFAULT_UPLOAD_MODE if str(DEFAULT_UPLOAD_MODE).lower() in {"media", "document"} else "media",
    "storage_mode": DEFAULT_STORAGE_MODE if str(DEFAULT_STORAGE_MODE).lower() in {"telegram", "gdrive", "rclone"} else "telegram",
    "thumbnail_enabled": False,
    "thumbnail_file_id": "",
    "caption_enabled": False,
    "caption_text": "",
    "telegram_caption_enabled": False,
    "telegram_caption_text": "",
    "gdrive_caption_enabled": False,
    "gdrive_caption_text": "",
    "rclone_caption_enabled": False,
    "rclone_caption_text": "",
    "caption_parse_mode": "html",
    "caption_index_enabled": True,
    "caption_index_padding": 2,
    "caption_index_start": 1,
    "prefix": "",
    "suffix": "",
    "replace_words": "",
    "replace_words_file": "",
    "replace_words_caption": "",
    "auto_rename": "",
    "auto_rename_enabled": False,
    "rename_template": "",
    "rename_parse_mode": "text",
    "filename_prefix": "",
    "filename_suffix": "",
    "filename_index_enabled": False,
    "filename_index_padding": 2,
    "filename_index_start": 1,
    "metadata_enabled": False,
    "metadata_video_title": "",
    "metadata_video_author": "",
    "metadata_audio_title": "",
    "metadata_subtitle_title": "",
    "gdrive_folder_id": "",
    "gdrive_token_path": "",
    "gdrive_last_file_link": "",
    "rclone_config_path": "",
    "rclone_remote_path": "",
    "rclone_last_file_path": "",
    "personal_bot_token": "",
    "personal_bot_username": "",
    "bot_delivery_mode": "main",
    "route_template": "off",
    "upload_destination": "",
    "topic_id": "",
    "index_mode": False,
    "authorized_mode": False,
    "last_login_user_id": 0,
    "batch_mode": False,
    "batch_last_input": "",
}


DEFAULT_USER_LIMITS = {
    "batch_limit": 0,
    "task_limit": 0,
    "allowed_storage_modes": "",
}

CAPTION_MODE_KEYS = dict(_CAPTION_MODE_KEYS)

DEFAULT_STATS = {
    "started_at": "",
    "last_activity_at": "",
    "users_registered": 0,
    "tasks_created": 0,
    "tasks_completed": 0,
    "tasks_failed": 0,
    "uploads_completed": 0,
    "batch_runs": 0,
    "broadcast_runs": 0,
    "premium_users": 0,
}

WAITING_KEYS = {
    "set_prefix": "prefix",
    "set_suffix": "suffix",
    "set_auto_rename": "auto_rename",
    "set_destination": "upload_destination",
    "set_gdrive_folder_id": "gdrive_folder_id",
    "set_rclone_remote_path": "rclone_remote_path",
    "set_route_template": "route_template",
    "set_personal_bot_token": "personal_bot_token",
    "set_topic_id": "topic_id",
    "set_replace_words": "replace_words",
    "set_replace_words_file": "replace_words_file",
    "set_replace_words_caption": "replace_words_caption",
    "set_caption_text": "caption_text",
    "set_metadata_video_title": "metadata_video_title",
    "set_metadata_video_author": "metadata_video_author",
    "set_metadata_audio_title": "metadata_audio_title",
    "set_metadata_subtitle_title": "metadata_subtitle_title",
    "set_thumbnail_photo": "thumbnail_file_id",
    "set_rename_template": "rename_template",
    "set_filename_prefix": "filename_prefix",
    "set_filename_suffix": "filename_suffix",
    "set_caption_index_padding": "caption_index_padding",
    "set_caption_index_start": "caption_index_start",
    "set_filename_index_padding": "filename_index_padding",
    "set_filename_index_start": "filename_index_start",
    "login_phone": "login_phone",
    "login_code": "login_code",
    "login_password": "login_password",
    "set_batch_links": "batch_last_input",
}


def _normalize_storage_mode_key(value: str) -> str:
    return _normalize_storage_mode_key_impl(value)


def get_caption_setting_keys(storage_mode: str | None = None):
    return _get_caption_setting_keys_impl(storage_mode)


def get_caption_settings_for_mode(settings: dict | None, storage_mode: str | None = None):
    return _get_caption_settings_for_mode_impl(settings, storage_mode)


# =========================================================
# GENERIC HELPERS
# =========================================================
def _json_cache_key(path: str) -> str:
    try:
        return str(Path(path).resolve())
    except Exception:
        return str(path or "")


def clear_local_json_cache(path: str | None = None):
    if path is None:
        _LOCAL_JSON_CACHE.clear()
        return
    _LOCAL_JSON_CACHE.pop(_json_cache_key(path), None)


try:
    import orjson

    def _fast_json_loads(data_bytes):
        return orjson.loads(data_bytes)

    def _fast_json_dumps(data_obj):
        return orjson.dumps(data_obj, option=orjson.OPT_NON_STR_KEYS)
except Exception:
    def _fast_json_loads(data_bytes):
        return json.loads(data_bytes)

    def _fast_json_dumps(data_obj):
        return json.dumps(data_obj, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def load_json(path, default):
    cache_key = _json_cache_key(path)
    cached = _LOCAL_JSON_CACHE.get(cache_key)
    if cached is not None:
        return deepcopy(cached)
    if not os.path.exists(path):
        return deepcopy(default)
    try:
        with open(path, "rb") as file:
            data = _fast_json_loads(file.read())
            _LOCAL_JSON_CACHE[cache_key] = deepcopy(data)
            return data
    except Exception:
        return deepcopy(default)


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    payload = _fast_json_dumps(data)
    with open(path, "wb") as file:
        file.write(payload)
    _LOCAL_JSON_CACHE[_json_cache_key(path)] = deepcopy(data)


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _to_float(value, default=0.0):
    try:
        return float(value)
    except Exception:
        return default


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"true", "1", "yes", "on"}:
            return True
        if value in {"false", "0", "no", "off"}:
            return False
    try:
        return bool(value)
    except Exception:
        return default


def _normalize_upload_mode(value, default: str = "media") -> str:
    value = str(value or "").strip().lower()
    if value in {"document", "doc", "file"}:
        return "document"
    if value in {"media", "video", "telegram", "photo", "audio"}:
        return "media"
    return "document" if str(default or "media").strip().lower() == "document" else "media"


def _now_utc():
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _utcnow_naive_iso() -> str:
    return _now_utc().replace(tzinfo=None).isoformat()


def _parse_iso(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except Exception:
        return None


_ACTIVE_TASK_STATUSES = {"queued", "fetching", "downloading", "uploading", "processing", "retrying", "copying", "validating", "checking"}
_TERMINAL_TASK_STATUSES = {"completed", "failed", "cancelled"}
_TASK_STATUS_TTL = max(5, _to_int(TASK_STATUS_TTL_MINUTES, 180))
_TASK_CACHE_TTL_SECONDS = 300.0
_TASK_LOCAL_FLUSH_INTERVAL_SECONDS = 25.0
_TASK_REMOTE_SYNC_INTERVAL_SECONDS = 300.0
_LAST_ACTIVITY_FLUSH_INTERVAL_SECONDS = 30.0
_TASKS_CACHE = None
_TASKS_CACHE_LOADED_AT = 0.0
_TASKS_LAST_LOCAL_SAVE_AT = 0.0
_TASKS_LAST_REMOTE_SYNC_AT = 0.0
_LAST_ACTIVITY_SAVE_AT = 0.0
_SUPABASE_BOOTSTRAP_ATTEMPTED = False
_SUPABASE_BOOTSTRAP_STATE = {"enabled": False, "ready": False, "message": "Supabase not configured"}
_SUPABASE_REST_DISABLED_UNTIL = 0.0
_SUPABASE_REST_BACKOFF_SECONDS = 300.0
_SUPABASE_OFFLINE_UNTIL = 0.0
_SUPABASE_OFFLINE_BACKOFF_SECONDS = 300.0
_SUPABASE_SELECT_CACHE = {}
_SUPABASE_SELECT_CACHE_TTL_SECONDS = 30.0
_HYBRID_REMOTE_REFRESH_AT = {}
_HYBRID_REMOTE_REFRESH_INTERVAL_SECONDS = 60.0
_REGISTER_USER_WRITE_INTERVAL_SECONDS = 60.0
_PREMIUM_CLEANUP_INTERVAL_SECONDS = 300.0
_LAST_PREMIUM_CLEANUP_AT = 0.0
_LOCAL_JSON_CACHE = {}

SUPABASE_PAYLOAD_TABLE_KEYS = {
    SUPABASE_USERS_TABLE: "id",
    SUPABASE_SETTINGS_TABLE: "user_id",
    SUPABASE_STATE_TABLE: "user_id",
    SUPABASE_PREMIUM_TABLE: "user_id",
    SUPABASE_TASKS_TABLE: "id",
    SUPABASE_STATS_TABLE: "id",
    SUPABASE_BROADCAST_TABLE: "created_at",
    SUPABASE_BANNED_TABLE: "user_id",
    SUPABASE_INDEX_TABLE: "index_no",
    SUPABASE_FAILED_TASKS_TABLE: "task_id",
    SUPABASE_USER_LIMITS_TABLE: "user_id",
    SUPABASE_SESSIONS_TABLE: "user_id",
    SUPABASE_INDEX_STATE_TABLE: "user_id",
}

SUPABASE_PAYLOAD_TABLE_TYPES = {
    SUPABASE_USERS_TABLE: "bigint",
    SUPABASE_SETTINGS_TABLE: "bigint",
    SUPABASE_STATE_TABLE: "bigint",
    SUPABASE_PREMIUM_TABLE: "bigint",
    SUPABASE_TASKS_TABLE: "text",
    SUPABASE_STATS_TABLE: "bigint",
    SUPABASE_BROADCAST_TABLE: "text",
    SUPABASE_BANNED_TABLE: "bigint",
    SUPABASE_INDEX_TABLE: "bigint",
    SUPABASE_FAILED_TASKS_TABLE: "text",
    SUPABASE_USER_LIMITS_TABLE: "bigint",
    SUPABASE_SESSIONS_TABLE: "bigint",
    SUPABASE_INDEX_STATE_TABLE: "bigint",
}


def _task_last_seen_dt(task: dict):
    if not isinstance(task, dict):
        return None
    for key in ("updated_at", "created_at"):
        parsed = _parse_iso(task.get(key, ""))
        if parsed:
            return parsed
    return None


def _is_task_stale(task: dict, max_age_minutes: int | None = None) -> bool:
    if not isinstance(task, dict):
        return False
    status = str(task.get("status", "") or "").strip().lower()
    if status not in _ACTIVE_TASK_STATUSES:
        return False
    last_seen = _task_last_seen_dt(task)
    if not last_seen:
        return True
    timeout = max_age_minutes if max_age_minutes is not None else (10 if status in {"checking", "queued", "validating", "processing"} else 15)
    age = _now_utc() - last_seen
    return age > timedelta(minutes=timeout)


def cleanup_stale_active_tasks(on_startup: bool = False):
    tasks = get_all_tasks()
    changed = False
    for task_id, task in list(tasks.items()):
        if not isinstance(task, dict):
            continue
        status = str(task.get("status", "") or "").strip().lower()
        if status in _ACTIVE_TASK_STATUSES:
            if on_startup:
                task = dict(task)
                task["status"] = "cancelled"
                task["current_stage"] = "cancelled"
                task["error"] = "Interrupted by bot restart"
                task["updated_at"] = _utcnow_naive_iso()
                tasks[str(task_id)] = _normalize_task_record(task_id, task)
                changed = True
            elif _is_task_stale(task):
                task = dict(task)
                task["status"] = "failed"
                task["current_stage"] = "failed"
                task["error"] = task.get("error") or "Auto-closed stale task (timeout)"
                task["updated_at"] = _utcnow_naive_iso()
                tasks[str(task_id)] = _normalize_task_record(task_id, task)
                changed = True
    if changed:
        save_all_tasks(tasks, force_local=True)
    return changed


def _is_countable_running_task(task: dict) -> bool:
    if not isinstance(task, dict):
        return False
    status = str(task.get("status", "") or "").strip().lower()
    if status not in _ACTIVE_TASK_STATUSES:
        return False
    if _is_task_stale(task):
        return False
    return True


def _task_status_rank(status: str) -> int:
    order = {
        "checking": 1,
        "queued": 2,
        "processing": 3,
        "fetching": 4,
        "downloading": 5,
        "uploading": 6,
        "copying": 7,
        "completed": 8,
        "failed": 8,
        "cancelled": 8,
    }
    return order.get(str(status or "").lower(), 0)


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def _is_subpath(path: str, parent: str) -> bool:
    path = str(path or "").strip()
    parent = str(parent or "").strip()
    if not path or not parent:
        return False
    try:
        Path(path).resolve().relative_to(Path(parent).resolve())
        return True
    except Exception:
        return False


def _directory_usage(path: str):
    root = Path(str(path or "").strip())
    stats = {
        "path": str(root),
        "exists": root.exists(),
        "files": 0,
        "bytes": 0,
    }
    if not root.exists():
        return stats

    for item in root.rglob("*"):
        try:
            if item.is_file():
                stats["files"] += 1
                stats["bytes"] += int(item.stat().st_size)
        except Exception:
            continue
    return stats


def _cleanup_old_files_in_dir(path: str, older_than_hours: int):
    root = Path(str(path or "").strip())
    if not root.exists() or older_than_hours <= 0:
        return 0

    cutoff = time.time() - (max(1, int(older_than_hours)) * 3600)
    deleted = 0
    for item in sorted(root.rglob("*"), reverse=True):
        try:
            if item.is_file() and float(item.stat().st_mtime) <= cutoff:
                item.unlink()
                deleted += 1
        except Exception:
            continue

    for item in sorted(root.rglob("*"), reverse=True):
        try:
            if item.is_dir():
                item.rmdir()
        except Exception:
            continue
    return deleted


def cleanup_temp_artifacts(hours: int | None = None):
    retention_hours = max(1, int(hours or TEMP_FILE_RETENTION_HOURS or 12))
    return {
        "temp_deleted": _cleanup_old_files_in_dir(TEMP_DIR, retention_hours),
        "cache_deleted": _cleanup_old_files_in_dir(CACHE_DIR, retention_hours),
    }


def prune_backup_snapshots(max_keep: int | None = None):
    keep = max(1, int(max_keep or BACKUP_RETENTION_COUNT or 15))
    root = Path(str(BACKUP_DIR or "").strip())
    if not root.exists():
        return 0

    snapshots = []
    for item in root.glob("*.json"):
        try:
            snapshots.append((float(item.stat().st_mtime), item))
        except Exception:
            continue

    snapshots.sort(reverse=True)
    deleted = 0
    for _, item in snapshots[keep:]:
        try:
            item.unlink()
            deleted += 1
        except Exception:
            continue
    return deleted


def cleanup_runtime_artifacts():
    temp_info = cleanup_temp_artifacts()
    backup_deleted = prune_backup_snapshots()
    tasks_trimmed = cleanup_old_tasks(TASK_CLEANUP_AFTER_HOURS)
    return {
        "temp_deleted": temp_info.get("temp_deleted", 0),
        "cache_deleted": temp_info.get("cache_deleted", 0),
        "backup_deleted": backup_deleted,
        "tasks_trimmed": bool(tasks_trimmed),
    }


def get_storage_runtime_status():
    persistent_root = str(PERSISTENT_DATA_DIR or "").strip()
    data_usage = _directory_usage(DATA_DIR)
    temp_usage = _directory_usage(TEMP_DIR)
    backup_usage = _directory_usage(BACKUP_DIR)
    cache_usage = _directory_usage(CACHE_DIR)
    return {
        "persistent_data_dir": persistent_root,
        "data_dir": data_usage,
        "temp_dir": temp_usage,
        "backup_dir": backup_usage,
        "cache_dir": cache_usage,
        "data_on_persistent_dir": _is_subpath(DATA_DIR, persistent_root) if persistent_root else False,
        "temp_on_persistent_dir": _is_subpath(TEMP_DIR, persistent_root) if persistent_root else False,
    }


def _first_non_empty(*values):
    for value in values:
        if isinstance(value, str):
            if value.strip():
                return value.strip()
        elif value not in (None, "", [], {}, ()):
            return value
    return ""


def _looks_like_chat_id(value) -> bool:
    value = str(value or "").strip()
    if not value:
        return False
    return bool(re.fullmatch(r"-?\d+", value))


def _clean_topic_id(value) -> str:
    value = str(value or "").strip()
    if not value:
        return ""
    if re.fullmatch(r"-?\d+", value):
        return value
    return ""


def _format_destination_display(destination: str, topic_id: str = "") -> str:
    destination = str(destination or "").strip()
    topic_id = _clean_topic_id(topic_id)
    if not destination:
        return ""
    if topic_id:
        return f"{destination} | Topic {topic_id}"
    return destination


# =========================================================
# SUPABASE HELPERS
# =========================================================
def _is_safe_sql_identifier(value: str) -> bool:
    return bool(re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", str(value or "").strip()))


def _sql_ident(value: str) -> str:
    value = str(value or "").strip()
    if not _is_safe_sql_identifier(value):
        raise RuntimeError(f"Unsafe SQL identifier: {value}")
    return f'"{value}"'


def _supabase_payload_key(table: str) -> str:
    return str(SUPABASE_PAYLOAD_TABLE_KEYS.get(table, "id"))


def _prepare_supabase_row(table: str, row: dict):
    row = dict(row or {})
    key_name = _supabase_payload_key(table)
    if table not in SUPABASE_PAYLOAD_TABLE_KEYS:
        return row
    return {
        key_name: row.get(key_name),
        "payload": row,
    }


def _decode_supabase_row(table: str, row: dict):
    row = dict(row or {})
    if table not in SUPABASE_PAYLOAD_TABLE_KEYS:
        return row
    payload = row.get("payload", {})
    if not isinstance(payload, dict):
        payload = {}
    merged = dict(payload)
    key_name = _supabase_payload_key(table)
    if row.get(key_name) is not None:
        merged[key_name] = row.get(key_name)
    return merged


def _create_payload_table_sql(table: str, key_name: str, key_type: str) -> str:
    table_ident = _sql_ident(table)
    key_ident = _sql_ident(key_name)
    return (
        f"create table if not exists {_sql_ident(SUPABASE_SCHEMA)}.{table_ident} ("
        f"{key_ident} {key_type} primary key, "
        "payload jsonb not null default '{}'::jsonb, "
        "row_created_at timestamptz not null default timezone('utc', now()), "
        "row_updated_at timestamptz not null default timezone('utc', now())"
        ");"
    )


def ensure_supabase_schema(force: bool = False):
    global _SUPABASE_BOOTSTRAP_ATTEMPTED, _SUPABASE_BOOTSTRAP_STATE, _SUPABASE_OFFLINE_UNTIL

    if force:
        _SUPABASE_OFFLINE_UNTIL = 0.0

    if _SUPABASE_BOOTSTRAP_ATTEMPTED and not force:
        return dict(_SUPABASE_BOOTSTRAP_STATE)

    _SUPABASE_BOOTSTRAP_ATTEMPTED = True
    state = {
        "enabled": _supabase_enabled(),
        "ready": False,
        "message": "Supabase not configured",
    }

    if not _supabase_enabled():
        _SUPABASE_BOOTSTRAP_STATE = state
        return dict(state)

    if not SUPABASE_DB_URL:
        state["ready"] = True
        state["message"] = "SUPABASE_DB_URL missing hai. Existing REST tables hongi to sync chalega, warna tables pehle create karni hongi."
        _SUPABASE_BOOTSTRAP_STATE = state
        return dict(state)

    try:
        import psycopg
    except Exception as error:
        state["message"] = f"psycopg import failed: {error}"
        _SUPABASE_BOOTSTRAP_STATE = state
        _SUPABASE_OFFLINE_UNTIL = time.time() + _SUPABASE_OFFLINE_BACKOFF_SECONDS
        return dict(state)

    statements = [f"create schema if not exists {_sql_ident(SUPABASE_SCHEMA)};"]
    for table, key_name in SUPABASE_PAYLOAD_TABLE_KEYS.items():
        key_type = SUPABASE_PAYLOAD_TABLE_TYPES.get(table, "text")
        statements.append(_create_payload_table_sql(table, key_name, key_type))

    try:
        with psycopg.connect(SUPABASE_DB_URL, connect_timeout=min(2, max(1, int(SUPABASE_TIMEOUT or 2))), autocommit=True) as conn:
            with conn.cursor() as cursor:
                for statement in statements:
                    cursor.execute(statement)
        state["ready"] = True
        state["message"] = "Supabase schema ready"
        _SUPABASE_OFFLINE_UNTIL = 0.0
        try:
            hydrate_local_files_from_supabase()
        except Exception:
            pass
    except Exception as error:
        state["message"] = f"Supabase schema bootstrap failed: {error}"
        _SUPABASE_OFFLINE_UNTIL = time.time() + _SUPABASE_OFFLINE_BACKOFF_SECONDS

    _SUPABASE_BOOTSTRAP_STATE = state
    return dict(state)


def get_supabase_status():
    state = ensure_supabase_schema(force=False)
    has_url = bool(str(SUPABASE_URL or "").strip())
    has_key = bool(str(_supabase_auth_key() or "").strip())
    has_db_url = bool(str(SUPABASE_DB_URL or "").strip())
    role = "unknown"
    token = str(_supabase_auth_key() or "").strip()
    parts = token.split(".")
    if len(parts) == 3:
        try:
            payload = json.loads(base64.urlsafe_b64decode(parts[1] + "=" * (-len(parts[1]) % 4)).decode("utf-8"))
            role = str(payload.get("role", "unknown") or "unknown")
        except Exception:
            role = "unknown"
    return {
        "enabled": _supabase_enabled(),
        "has_url": has_url,
        "has_key": has_key,
        "has_db_url": has_db_url,
        "key_role": role,
        "schema_state": state,
    }


def _supabase_enabled() -> bool:
    return bool(SUPABASE_URL and (SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY))


def _supabase_operational() -> bool:
    if not _supabase_enabled():
        return False
    if not _SUPABASE_BOOTSTRAP_ATTEMPTED:
        return False
    if not _SUPABASE_BOOTSTRAP_STATE.get("ready"):
        return False
    if time.time() < float(_SUPABASE_OFFLINE_UNTIL or 0.0):
        return False
    return True


def _mark_supabase_offline(error=None):
    global _SUPABASE_OFFLINE_UNTIL
    _SUPABASE_OFFLINE_UNTIL = time.time() + _SUPABASE_OFFLINE_BACKOFF_SECONDS


def _supabase_auth_key() -> str:
    return str(SUPABASE_SERVICE_ROLE_KEY or SUPABASE_KEY or "").strip()


def _supabase_headers(prefer: str = "return=representation"):
    auth_key = _supabase_auth_key()
    return {
        "apikey": auth_key,
        "Authorization": f"Bearer {auth_key}",
        "Content-Type": "application/json",
        "Accept-Profile": SUPABASE_SCHEMA,
        "Content-Profile": SUPABASE_SCHEMA,
        "Prefer": prefer,
    }


def _supabase_url(path: str) -> str:
    return f"{str(SUPABASE_URL).rstrip('/')}{path}"


def _supabase_request(method: str, path: str, payload=None, prefer: str = "return=representation"):
    if not _supabase_enabled():
        raise RuntimeError("Supabase not configured")
    data = None if payload is None else json.dumps(payload, ensure_ascii=False).encode("utf-8")
    request_obj = urllib_request.Request(
        url=_supabase_url(path),
        data=data,
        method=method.upper(),
        headers=_supabase_headers(prefer=prefer),
    )
    try:
        with urllib_request.urlopen(request_obj, timeout=float(SUPABASE_TIMEOUT)) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib_error.HTTPError as error:
        try:
            body = error.read().decode("utf-8")
        except Exception:
            body = ""
        raise RuntimeError(f"Supabase HTTPError {error.code}: {body}")
    except Exception as error:
        raise RuntimeError(f"Supabase request failed: {error}")


def _load_psycopg():
    try:
        import psycopg
        return psycopg
    except Exception as error:
        raise RuntimeError(f"psycopg import failed: {error}")


def _supabase_db_fallback_available(table: str) -> bool:
    return bool(str(SUPABASE_DB_URL or "").strip()) and table in SUPABASE_PAYLOAD_TABLE_KEYS


def _should_try_supabase_rest(table: str) -> bool:
    disabled_until = float(_SUPABASE_REST_DISABLED_UNTIL or 0.0)
    if _supabase_db_fallback_available(table) and disabled_until > time.time():
        return False
    return True


def _mark_supabase_rest_failure(table: str):
    global _SUPABASE_REST_DISABLED_UNTIL
    if _supabase_db_fallback_available(table):
        _SUPABASE_REST_DISABLED_UNTIL = time.time() + _SUPABASE_REST_BACKOFF_SECONDS


def _mark_supabase_rest_success():
    global _SUPABASE_REST_DISABLED_UNTIL
    _SUPABASE_REST_DISABLED_UNTIL = 0.0


def _select_cache_key(table: str, filters=None):
    normalized_filters = tuple(sorted((str(key), str(value)) for key, value in (filters or {}).items()))
    return (str(table or ""), normalized_filters)


def _get_cached_select_rows(table: str, filters=None):
    cache_key = _select_cache_key(table, filters)
    cached = _SUPABASE_SELECT_CACHE.get(cache_key)
    if not cached:
        return None
    if (time.time() - float(cached.get("loaded_at", 0.0) or 0.0)) > _SUPABASE_SELECT_CACHE_TTL_SECONDS:
        _SUPABASE_SELECT_CACHE.pop(cache_key, None)
        return None
    return list(cached.get("rows", []) or [])


def _store_cached_select_rows(table: str, filters, rows):
    _SUPABASE_SELECT_CACHE[_select_cache_key(table, filters)] = {
        "loaded_at": time.time(),
        "rows": list(rows or []),
    }


def _invalidate_select_cache(table: str):
    stale_keys = [key for key in _SUPABASE_SELECT_CACHE if key and key[0] == str(table or "")]
    for key in stale_keys:
        _SUPABASE_SELECT_CACHE.pop(key, None)


def _hybrid_refresh_key(path: str, table: str, key_name: str) -> str:
    return f"{path}|{table}|{key_name}"


def _should_use_local_hybrid_fast_path(path: str, table: str, key_name: str, local_has_data: bool) -> bool:
    if not (ENABLE_LOCAL_FALLBACK and local_has_data):
        return False
    refresh_key = _hybrid_refresh_key(path, table, key_name)
    now = time.time()
    last_refresh = float(_HYBRID_REMOTE_REFRESH_AT.get(refresh_key, 0.0) or 0.0)
    if last_refresh <= 0.0:
        _HYBRID_REMOTE_REFRESH_AT[refresh_key] = now
        return True
    if (now - last_refresh) < _HYBRID_REMOTE_REFRESH_INTERVAL_SECONDS:
        return True
    _HYBRID_REMOTE_REFRESH_AT[refresh_key] = now
    return False


def _mark_hybrid_remote_refresh(path: str, table: str, key_name: str):
    _HYBRID_REMOTE_REFRESH_AT[_hybrid_refresh_key(path, table, key_name)] = time.time()


def _supabase_db_read_rows(table: str, filters=None):
    if not _supabase_db_fallback_available(table):
        raise RuntimeError("Supabase DB fallback not available")
    psycopg = _load_psycopg()
    key_name = _supabase_payload_key(table)
    conditions = []
    params = []
    for column, value in (filters or {}).items():
        conditions.append(f"{_sql_ident(column)} = %s")
        params.append(_coerce_supabase_key_value(table, value) if column == key_name else value)
    where_sql = f" where {' and '.join(conditions)}" if conditions else ""
    query = (
        f"select {_sql_ident(key_name)}, payload "
        f"from {_sql_ident(SUPABASE_SCHEMA)}.{_sql_ident(table)}"
        f"{where_sql}"
    )
    with psycopg.connect(SUPABASE_DB_URL, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)
            rows = cursor.fetchall() or []
    return [{key_name: row[0], "payload": row[1]} for row in rows]


def _supabase_db_delete_rows(table: str, filters=None):
    if not _supabase_db_fallback_available(table):
        raise RuntimeError("Supabase DB fallback not available")
    psycopg = _load_psycopg()
    conditions = []
    params = []
    for column, value in (filters or {}).items():
        conditions.append(f"{_sql_ident(column)} = %s")
        key_name = _supabase_payload_key(table)
        params.append(_coerce_supabase_key_value(table, value) if column == key_name else value)
    if not conditions:
        raise RuntimeError("Delete without filters is not allowed")
    query = (
        f"delete from {_sql_ident(SUPABASE_SCHEMA)}.{_sql_ident(table)} "
        f"where {' and '.join(conditions)}"
    )
    with psycopg.connect(SUPABASE_DB_URL, autocommit=True) as conn:
        with conn.cursor() as cursor:
            cursor.execute(query, params)


def _supabase_db_upsert_rows(table: str, rows, conflict_columns="id"):
    if not _supabase_db_fallback_available(table):
        raise RuntimeError("Supabase DB fallback not available")
    rows = rows if isinstance(rows, list) else [rows]
    rows = [dict(_prepare_supabase_row(table, row) or {}) for row in rows if row]
    if not rows:
        return []
    psycopg = _load_psycopg()
    key_name = _supabase_payload_key(table)
    conflict_idents = [part.strip() for part in str(conflict_columns or key_name).split(",") if part.strip()]
    query = (
        f"insert into {_sql_ident(SUPABASE_SCHEMA)}.{_sql_ident(table)} ({_sql_ident(key_name)}, payload) "
        f"values (%s, %s::jsonb) "
        f"on conflict ({', '.join(_sql_ident(part) for part in conflict_idents)}) "
        f"do update set payload = excluded.payload"
    )
    with psycopg.connect(SUPABASE_DB_URL, autocommit=True) as conn:
        with conn.cursor() as cursor:
            for row in rows:
                payload = row.get("payload", {})
                cursor.execute(query, [row.get(key_name), json.dumps(payload, ensure_ascii=False)])
    return rows


def _quote(value) -> str:
    return urllib_parse.quote(str(value), safe="")


def _build_supabase_filters(filters=None) -> str:
    if not filters:
        return ""
    parts = []
    for key, value in filters.items():
        if value is None:
            continue
        if isinstance(value, bool):
            encoded = "true" if value else "false"
        else:
            encoded = _quote(value)
        parts.append(f"{key}=eq.{encoded}")
    return ("&" + "&".join(parts)) if parts else ""


def _select_rows(table: str, filters=None):
    if not _supabase_operational():
        return []
    cached_rows = _get_cached_select_rows(table, filters)
    if cached_rows is not None:
        return [_decode_supabase_row(table, row) for row in cached_rows]
    select_clause = "*"
    if table in SUPABASE_PAYLOAD_TABLE_KEYS:
        select_clause = f"{_supabase_payload_key(table)},payload"
    rows = []
    if not _should_try_supabase_rest(table):
        try:
            rows = _supabase_db_read_rows(table, filters=filters)
        except Exception as exc:
            _mark_supabase_offline(exc)
            return []
    else:
        try:
            rows = _supabase_request("GET", f"/rest/v1/{table}?select={select_clause}{_build_supabase_filters(filters)}") or []
            _mark_supabase_rest_success()
        except Exception:
            _mark_supabase_rest_failure(table)
            try:
                rows = _supabase_db_read_rows(table, filters=filters)
            except Exception as exc:
                _mark_supabase_offline(exc)
                return []
    if not isinstance(rows, list):
        return []
    _store_cached_select_rows(table, filters, rows)
    return [_decode_supabase_row(table, row) for row in rows]


def _delete_rows(table: str, filters=None):
    if not _supabase_operational():
        return None
    _invalidate_select_cache(table)
    if not _should_try_supabase_rest(table):
        try:
            return _supabase_db_delete_rows(table, filters=filters)
        except Exception as exc:
            _mark_supabase_offline(exc)
            return None
    try:
        result = _supabase_request("DELETE", f"/rest/v1/{table}?{_build_supabase_filters(filters).lstrip('&')}", prefer="return=minimal")
        _mark_supabase_rest_success()
        return result
    except Exception:
        _mark_supabase_rest_failure(table)
        try:
            return _supabase_db_delete_rows(table, filters=filters)
        except Exception as exc:
            _mark_supabase_offline(exc)
            return None


def _upsert_rows(table: str, rows, conflict_columns="id"):
    if not _supabase_operational():
        return []
    if not isinstance(rows, list):
        rows = [rows]
    if not rows:
        return []
    _invalidate_select_cache(table)
    payload_rows = [_prepare_supabase_row(table, row) for row in rows]
    if not _should_try_supabase_rest(table):
        try:
            return _supabase_db_upsert_rows(table, rows, conflict_columns=conflict_columns)
        except Exception as exc:
            _mark_supabase_offline(exc)
            return []
    try:
        result = _supabase_request(
            "POST",
            f"/rest/v1/{table}?on_conflict={conflict_columns}",
            payload_rows,
        )
        _mark_supabase_rest_success()
        return result
    except Exception:
        _mark_supabase_rest_failure(table)
        try:
            return _supabase_db_upsert_rows(table, rows, conflict_columns=conflict_columns)
        except Exception as exc:
            _mark_supabase_offline(exc)
            return []


def _replace_table_rows(table: str, rows):
    if not _supabase_operational():
        return
    _invalidate_select_cache(table)
    key_name = _supabase_payload_key(table)
    rows = rows if isinstance(rows, list) else [rows]
    normalized_rows = []
    wanted_keys = set()
    for row in rows:
        row = dict(row or {})
        typed_key = _coerce_supabase_key_value(table, row.get(key_name))
        if str(typed_key) == "":
            continue
        row[key_name] = typed_key
        normalized_rows.append(row)
        wanted_keys.add(str(typed_key))

    try:
        remote_rows = _select_rows(table) or []
    except Exception:
        remote_rows = []

    if normalized_rows:
        _upsert_rows(table, normalized_rows, conflict_columns=key_name)

    for remote_row in remote_rows:
        typed_key = _coerce_supabase_key_value(table, remote_row.get(key_name))
        if str(typed_key) not in wanted_keys:
            try:
                _delete_rows(table, {key_name: typed_key})
            except Exception:
                pass


# =========================================================
# NORMALIZERS
# =========================================================
def _normalize_settings(data: dict):
    merged = deepcopy(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)

    legacy_replace_words = str(merged.get("replace_words", "") or "").strip()
    file_replace_words = str(merged.get("replace_words_file", "") or "").strip()
    caption_replace_words = str(merged.get("replace_words_caption", "") or "").strip()
    if not file_replace_words and legacy_replace_words:
        file_replace_words = legacy_replace_words
    if not caption_replace_words and legacy_replace_words:
        caption_replace_words = legacy_replace_words

    merged["replace_words"] = legacy_replace_words
    merged["replace_words_file"] = file_replace_words
    merged["replace_words_caption"] = caption_replace_words

    merged["upload_mode"] = _normalize_upload_mode(merged.get("telegram_upload_mode", merged.get("upload_mode", DEFAULT_SETTINGS["upload_mode"])))
    merged["telegram_upload_mode"] = _normalize_upload_mode(merged.get("telegram_upload_mode", merged.get("upload_mode", DEFAULT_SETTINGS["upload_mode"])))
    storage_mode = str(merged.get("storage_mode", DEFAULT_SETTINGS["storage_mode"]) or DEFAULT_SETTINGS["storage_mode"]).strip().lower()
    if storage_mode not in {"telegram", "gdrive", "rclone"}:
        storage_mode = DEFAULT_SETTINGS["storage_mode"]
    merged["storage_mode"] = storage_mode

    raw_data = data if isinstance(data, dict) else {}
    has_explicit_caption_mode_fields = any(
        key in raw_data
        for pair in CAPTION_MODE_KEYS.values()
        for key in pair
    )
    legacy_caption_text = str(merged.get("caption_text", "") or "").strip()
    legacy_caption_enabled = _to_bool(merged.get("caption_enabled", False), False)
    if not has_explicit_caption_mode_fields:
        if legacy_caption_text and not any(str(merged.get(text_key, "") or "").strip() for _, text_key in CAPTION_MODE_KEYS.values()):
            merged["telegram_caption_text"] = legacy_caption_text
        if legacy_caption_enabled and not any(_to_bool(merged.get(enabled_key, False), False) for enabled_key, _ in CAPTION_MODE_KEYS.values()):
            merged["telegram_caption_enabled"] = True

    bot_delivery_mode = str(merged.get("bot_delivery_mode", "main") or "main").strip().lower()
    merged["bot_delivery_mode"] = bot_delivery_mode if bot_delivery_mode in {"main", "personal"} else "main"
    route_template = str(merged.get("route_template", "off") or "off").strip().lower()
    merged["route_template"] = route_template if route_template in {"off", "smart", "docs_to_gdrive", "media_to_telegram", "archives_to_rclone"} else "off"
    merged["caption_index_padding"] = max(1, _to_int(merged.get("caption_index_padding", 2), 2))
    merged["caption_index_start"] = max(0, _to_int(merged.get("caption_index_start", 1), 1))
    merged["filename_index_padding"] = max(1, _to_int(merged.get("filename_index_padding", 2), 2))
    merged["filename_index_start"] = max(0, _to_int(merged.get("filename_index_start", 1), 1))
    merged["last_login_user_id"] = _to_int(merged.get("last_login_user_id", 0), 0)

    bool_keys = {
        "thumbnail_enabled",
        "caption_enabled",
        "telegram_caption_enabled",
        "gdrive_caption_enabled",
        "rclone_caption_enabled",
        "caption_index_enabled",
        "auto_rename_enabled",
        "filename_index_enabled",
        "metadata_enabled",
        "index_mode",
        "authorized_mode",
        "batch_mode",
    }
    for key in bool_keys:
        merged[key] = _to_bool(merged.get(key, False), False)

    for key, value in list(merged.items()):
        if key not in bool_keys and key not in {
            "caption_index_padding",
            "caption_index_start",
            "filename_index_padding",
            "filename_index_start",
            "last_login_user_id",
        }:
            merged[key] = str(value or "")

    caption_state = get_caption_settings_for_mode(merged, storage_mode)
    merged["caption_enabled"] = bool(caption_state["enabled"])
    merged["caption_text"] = str(caption_state["text"] or "")
    return merged


def _normalize_state_record(user_id: int, data=None):
    data = data if isinstance(data, dict) else {"state": data or ""}
    normalized = {
        "user_id": int(user_id),
        "state": str(data.get("state", "") or ""),
        "login_phone": str(data.get("login_phone", "") or ""),
        "login_code": str(data.get("login_code", "") or ""),
        "login_password": str(data.get("login_password", "") or ""),
        "phone": str(data.get("phone", "") or ""),
        "phone_code_hash": str(data.get("phone_code_hash", "") or ""),
        "last_updated_at": str(data.get("last_updated_at", "") or ""),
    }
    for key, value in data.items():
        if key not in normalized:
            normalized[key] = value
    return normalized


def _normalize_user_record(user_id: int, data=None):
    data = data or {}
    return {
        "id": int(user_id),
        "first_name": str(data.get("first_name", "") or ""),
        "username": str(data.get("username", "") or ""),
        "last_seen": str(data.get("last_seen", "") or ""),
        "is_banned": _to_bool(data.get("is_banned", False), False),
    }


def _normalize_premium_record(user_id: int, data=None):
    data = data or {}
    return {
        "user_id": int(user_id),
        "is_premium": _to_bool(data.get("is_premium", False), False),
        "plan_name": str(data.get("plan_name", "") or ""),
        "premium_expires_at": str(data.get("premium_expires_at", "") or ""),
        "granted_by": _to_int(data.get("granted_by", 0), 0),
        "granted_at": str(data.get("granted_at", "") or ""),
        "notes": str(data.get("notes", "") or ""),
        "updated_at": str(data.get("updated_at", "") or ""),
    }


def _normalize_task_record(task_id: str, data=None):
    data = dict(data or {})

    destination = _first_non_empty(
        data.get("destination"),
        data.get("destination_chat_id"),
        data.get("destination_id"),
        data.get("dest"),
        data.get("target"),
        data.get("target_chat"),
        data.get("target_chat_id"),
        data.get("upload_destination"),
        data.get("chat_id"),
        data.get("forward_chat_id"),
    )
    destination = str(destination or "").strip()
    if destination and not _looks_like_chat_id(destination):
        destination = str(destination).strip()

    topic_id = _first_non_empty(
        data.get("topic_id"),
        data.get("destination_topic_id"),
        data.get("thread_id"),
        data.get("message_thread_id"),
    )
    topic_id = _clean_topic_id(topic_id)

    source = _first_non_empty(
        data.get("source"),
        data.get("source_link"),
        data.get("msg_link"),
        data.get("message_link"),
        data.get("url"),
    )

    file_name = _first_non_empty(
        data.get("file_name"),
        data.get("filename"),
        data.get("name"),
        data.get("title"),
    )

    upload_mode = _normalize_upload_mode(
        _first_non_empty(
            data.get("upload_mode"),
            data.get("send_mode"),
            data.get("mode"),
        )
    )

    status = str(data.get("status", "queued") or "queued").strip().lower()
    aliases = {
        "running": "processing",
        "in_progress": "processing",
        "waiting": "queued",
        "checking": "checking",
    }
    status = aliases.get(status, status)

    progress = max(0.0, min(100.0, _to_float(data.get("progress", 0.0), 0.0)))
    retries = max(0, _to_int(data.get("retries", data.get("retry_count", 0)), 0))

    extra = data.get("extra", {})
    if not isinstance(extra, dict):
        extra = {}

    normalized = {
        "id": str(task_id),
        "user_id": _to_int(data.get("user_id", 0), 0),
        "status": status,
        "type": str(data.get("type", "") or ""),
        "source": str(source or ""),
        "file_name": str(file_name or ""),
        "message": str(data.get("message", "") or ""),
        "progress": progress,
        "progress_percent": _to_float(data.get("progress_percent", progress), progress),
        "progress_bar_text": str(data.get("progress_bar_text", "") or ""),
        "speed": str(data.get("speed", "") or ""),
        "speed_bps": _to_float(data.get("speed_bps", 0.0), 0.0),
        "eta": str(data.get("eta", "") or ""),
        "eta_seconds": _to_float(data.get("eta_seconds", 0.0), 0.0),
        "elapsed_seconds": _to_float(data.get("elapsed_seconds", 0.0), 0.0),
        "current_bytes": _to_int(data.get("current_bytes", 0), 0),
        "total_bytes": _to_int(data.get("total_bytes", 0), 0),
        "retries": retries,
        "retry_count": retries,
        "created_at": str(data.get("created_at", "") or ""),
        "updated_at": str(data.get("updated_at", "") or ""),
        "destination": destination,
        "destination_raw": destination,
        "destination_display": str(data.get("destination_display") or _format_destination_display(destination, topic_id)),
        "user_destination": str(data.get("user_destination") or destination or ""),
        "topic_id": topic_id,
        "upload_mode": upload_mode,
        "current_stage": str(data.get("current_stage", "") or ""),
        "progress_text": str(data.get("progress_text", "") or ""),
        "error": str(data.get("error", "") or ""),
        "queue_position": _to_int(data.get("queue_position", 0), 0),
        "worker_id": _to_int(data.get("worker_id", 0), 0),
        "status_chat_id": _to_int(data.get("status_chat_id", 0), 0),
        "status_message_id": _to_int(data.get("status_message_id", 0), 0),
        "checking_chat_id": _to_int(data.get("checking_chat_id", 0), 0),
        "checking_message_id": _to_int(data.get("checking_message_id", 0), 0),
        "pinned_ui": _to_bool(data.get("pinned_ui", False), False),
        "is_visible": _to_bool(data.get("is_visible", False), False),
        "last_ui_update": _to_float(data.get("last_ui_update", 0.0), 0.0),
        "delivered_to": data.get("delivered_to", []),
        "delivery_errors": data.get("delivery_errors", []),
        "index_id": _to_int(data.get("index_id", 0), 0),
        "user_index_no": _to_int(data.get("user_index_no", 0), 0),
        "extra": extra,
    }

    normalized["upload_destination"] = normalized["destination"]
    normalized["destination_chat_id"] = normalized["destination"]
    normalized["dest"] = normalized["destination"]
    normalized["target"] = normalized["destination"]
    normalized["target_chat_id"] = normalized["destination"]
    normalized["message_thread_id"] = normalized["topic_id"]
    normalized["thread_id"] = normalized["topic_id"]

    for key, value in data.items():
        if key not in normalized:
            normalized[key] = value

    return normalized


def normalize_task_payload(task_id: str, data=None):
    return _normalize_task_record(task_id, data)


def normalize_existing_tasks_inplace():
    tasks = get_all_tasks()
    changed = False
    normalized_map = {}
    for task_id, task in tasks.items():
        normalized = _normalize_task_record(task_id, task)
        normalized_map[str(task_id)] = normalized
        if normalized != task:
            changed = True
    if changed:
        save_all_tasks(normalized_map)
    return changed


def get_task_destination(task) -> str:
    if not isinstance(task, dict):
        return ""
    normalized = _normalize_task_record(task.get("id", ""), task)
    return normalized.get("destination", "")


def get_task_destination_display(task) -> str:
    if not isinstance(task, dict):
        return ""
    normalized = _normalize_task_record(task.get("id", ""), task)
    return normalized.get("destination_display", "")


def _normalize_session_record(user_id: int, data=None):
    data = data or {}
    return {
        "user_id": int(user_id),
        "session_string": str(data.get("session_string", "") or ""),
        "tg_user_id": _to_int(data.get("tg_user_id", 0), 0),
        "phone": str(data.get("phone", "") or ""),
        "saved_at": str(data.get("saved_at", "") or ""),
    }


def _normalize_banned_user_record(user_id: int, data=None):
    data = data if isinstance(data, dict) else {}
    return {
        "user_id": int(user_id),
        "is_banned": True,
        "updated_at": str(data.get("updated_at", "") or ""),
    }


def _normalize_index_entry_record(index_no: int, data=None):
    normalized = dict(data or {}) if isinstance(data, dict) else {}
    normalized["index_no"] = max(1, _to_int(index_no, _to_int(normalized.get("index_no", 1), 1)))
    normalized["indexed_at"] = str(normalized.get("indexed_at", "") or "")
    return normalized


def _normalize_failed_task_record(task_id: str, data=None):
    data = data if isinstance(data, dict) else {}
    task_payload = data.get("task", {})
    return {
        "task_id": str(task_id or ""),
        "task": _normalize_task_record(task_id, task_payload) if isinstance(task_payload, dict) else {},
        "logged_at": str(data.get("logged_at", "") or ""),
    }


def _normalize_index_state_record(user_id: int, data=None):
    normalized = _default_index_state()
    if isinstance(data, dict):
        normalized.update(data)
    normalized["user_id"] = int(user_id)
    normalized["enabled"] = _to_bool(normalized.get("enabled", False), False)
    normalized["count"] = max(0, _to_int(normalized.get("count", 0), 0))
    normalized["user_start_offset"] = max(0, _to_int(normalized.get("user_start_offset", 0), 0))
    normalized["user_current_index"] = max(0, _to_int(normalized.get("user_current_index", 0), 0))
    normalized["last_reset_at"] = str(normalized.get("last_reset_at", "") or "")
    return normalized


def _normalize_index_state(data=None):
    data = data or {}
    return {
        "enabled": _to_bool(data.get("enabled", False), False),
        "count": max(0, _to_int(data.get("count", 0), 0)),
        "user_start_offset": max(0, _to_int(data.get("user_start_offset", 0), 0)),
        "user_current_index": max(0, _to_int(data.get("user_current_index", 0), 0)),
        "last_reset_at": str(data.get("last_reset_at", "") or ""),
    }


def _normalize_stats(data=None):
    merged = deepcopy(DEFAULT_STATS)
    if isinstance(data, dict):
        merged.update(data)
    for key in DEFAULT_STATS:
        if key.endswith("_at"):
            merged[key] = str(merged.get(key, "") or "")
        else:
            merged[key] = max(0, _to_int(merged.get(key, 0), 0))
    return merged


# =========================================================
# LOCAL + HYBRID TABLE HELPERS
# =========================================================
def _load_local_map(path):
    data = load_json(path, {})
    return data if isinstance(data, dict) else {}


def _save_local_map(path, data):
    save_json(path, data if isinstance(data, dict) else {})


def _load_local_list(path):
    data = load_json(path, [])
    return data if isinstance(data, list) else []


def _save_local_list(path, data):
    save_json(path, data if isinstance(data, list) else [])


def _coerce_supabase_key_value(table: str, value):
    key_type = str(SUPABASE_PAYLOAD_TABLE_TYPES.get(table, "text") or "text").strip().lower()
    if "int" in key_type:
        return _to_int(value, 0)
    return str(value or "")


def _sync_full_local_map_to_supabase(path: str, table: str, key_name: str, normalizer):
    if not (_supabase_operational() and ENABLE_LOCAL_FALLBACK and SYNC_LOCAL_TO_SUPABASE):
        return {"total": 0, "prepared": 0, "skipped": 0, "synced": 0, "disabled": True}
    local_map = _load_local_map(path)
    rows = []
    skipped = 0
    for raw_key, raw_value in local_map.items():
        try:
            typed_key = _coerce_supabase_key_value(table, raw_key)
            rows.append(normalizer(typed_key, raw_value))
        except Exception:
            skipped += 1
            continue
    if rows:
        _upsert_rows(table, rows, conflict_columns=key_name)
    return {
        "total": len(local_map),
        "prepared": len(rows),
        "skipped": skipped,
        "synced": len(rows),
        "disabled": False,
    }


def _replace_full_local_map_on_supabase(path: str, table: str, normalizer):
    if not (_supabase_operational() and ENABLE_LOCAL_FALLBACK and SYNC_LOCAL_TO_SUPABASE):
        return {"total": 0, "prepared": 0, "skipped": 0, "synced": 0, "disabled": True}
    local_map = _load_local_map(path)
    rows = []
    skipped = 0
    for raw_key, raw_value in local_map.items():
        try:
            typed_key = _coerce_supabase_key_value(table, raw_key)
            rows.append(normalizer(typed_key, raw_value))
        except Exception:
            skipped += 1
            continue
    _replace_table_rows(table, rows)
    return {
        "total": len(local_map),
        "prepared": len(rows),
        "skipped": skipped,
        "synced": len(rows),
        "disabled": False,
    }


def _get_hybrid_map(path: str, table: str, key_name: str, normalizer, prefer_local: bool = False, prefer_newer_by: str | None = None):
    local_map = _load_local_map(path)
    if _should_use_local_hybrid_fast_path(path, table, key_name, bool(local_map)):
        return local_map
    if _supabase_operational():
        try:
            rows = _select_rows(table) or []
            remote_map = {}
            for row in rows:
                typed_key = _coerce_supabase_key_value(table, row.get(key_name))
                row_key = str(typed_key)
                if row_key:
                    remote_map[row_key] = normalizer(typed_key, row)
            if ENABLE_LOCAL_FALLBACK:
                if prefer_newer_by:
                    merged = {}
                    all_keys = set(local_map.keys()) | set(remote_map.keys())
                    for row_key in all_keys:
                        local_row = local_map.get(row_key)
                        remote_row = remote_map.get(row_key)
                        if local_row is None:
                            merged[row_key] = remote_row
                            continue
                        if remote_row is None:
                            merged[row_key] = local_row
                            continue
                        local_dt = _parse_iso((local_row or {}).get(prefer_newer_by, ""))
                        remote_dt = _parse_iso((remote_row or {}).get(prefer_newer_by, ""))
                        if local_dt and remote_dt:
                            merged[row_key] = local_row if local_dt >= remote_dt else remote_row
                        elif local_dt:
                            merged[row_key] = local_row
                        elif remote_dt:
                            merged[row_key] = remote_row
                        else:
                            merged[row_key] = local_row if prefer_local else remote_row
                else:
                    merged = dict(remote_map) if prefer_local else dict(local_map)
                    merged.update(local_map if prefer_local else remote_map)
                if merged != local_map:
                    _save_local_map(path, merged)
                _mark_hybrid_remote_refresh(path, table, key_name)
                return merged
            _mark_hybrid_remote_refresh(path, table, key_name)
            return remote_map
        except Exception:
            try:
                _sync_full_local_map_to_supabase(path, table, key_name, normalizer)
            except Exception:
                pass
    return local_map


def _upsert_hybrid_map_record(path: str, table: str, key_name: str, key_value: int, row: dict, normalizer):
    typed_key = _coerce_supabase_key_value(table, key_value)
    normalized = normalizer(typed_key, row)
    local_map = _load_local_map(path)
    local_map[str(typed_key)] = normalized
    _save_local_map(path, local_map)
    _mark_hybrid_remote_refresh(path, table, key_name)
    if _supabase_operational():
        try:
            _upsert_rows(table, normalized, conflict_columns=key_name)
        except Exception:
            pass
    return normalized


def _delete_hybrid_map_record(path: str, table: str, key_name: str, key_value: int):
    typed_key = _coerce_supabase_key_value(table, key_value)
    local_map = _load_local_map(path)
    local_map.pop(str(typed_key), None)
    _save_local_map(path, local_map)
    _mark_hybrid_remote_refresh(path, table, key_name)
    if _supabase_operational():
        try:
            _delete_rows(table, {key_name: typed_key})
        except Exception:
            pass


# =========================================================
# SETTINGS
# =========================================================
def get_all_settings():
    return _get_hybrid_map(SETTINGS_FILE, SUPABASE_SETTINGS_TABLE, "user_id", _normalize_settings_record, prefer_newer_by="updated_at")


def _normalize_settings_record(user_id: int, data=None):
    normalized = _normalize_settings(data or {})
    normalized["user_id"] = int(user_id)
    normalized["updated_at"] = str((data or {}).get("updated_at", "") or "")
    return normalized


def save_all_settings(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(SETTINGS_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_settings_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_SETTINGS_TABLE, rows, conflict_columns="user_id")
        except Exception:
            pass


def get_user_settings(user_id: int):
    with _LOCK:
        all_settings = get_all_settings()
        uid = str(user_id)
        current = all_settings.get(uid, {})
        return _normalize_settings(current)


def save_single_user_settings(user_id: int, data: dict):
    row = _normalize_settings_record(user_id, data or {})
    row["updated_at"] = _now_iso()
    return _upsert_hybrid_map_record(SETTINGS_FILE, SUPABASE_SETTINGS_TABLE, "user_id", user_id, row, _normalize_settings_record)


def update_user_settings(user_id: int, new_data: dict):
    current = get_user_settings(user_id)
    if isinstance(new_data, dict):
        current.update(new_data)
    return save_single_user_settings(user_id, current)


def reset_user_settings(user_id: int):
    return save_single_user_settings(user_id, deepcopy(DEFAULT_SETTINGS))


# =========================================================
# STATE
# =========================================================
def get_all_states():
    return _load_local_map(STATE_FILE)


def save_all_states(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(STATE_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_state_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_STATE_TABLE, rows, conflict_columns="user_id")
        except Exception:
            pass


def get_user_state(user_id: int):
    raw = get_all_states().get(str(user_id), {})
    if isinstance(raw, dict):
        return str(raw.get("state", "") or "")
    return str(raw or "")


def set_user_state(user_id: int, state: str):
    current = get_all_states().get(str(user_id), {})
    if not isinstance(current, dict):
        current = {}
    current["state"] = str(state or "")
    current["last_updated_at"] = _now_iso()
    _upsert_hybrid_map_record(STATE_FILE, SUPABASE_STATE_TABLE, "user_id", user_id, current, _normalize_state_record)


def clear_user_state(user_id: int):
    _delete_hybrid_map_record(STATE_FILE, SUPABASE_STATE_TABLE, "user_id", user_id)


def set_login_temp(user_id: int, key: str, value):
    states = _load_local_map(STATE_FILE)

    current = states.get(str(user_id), {})

    if not isinstance(current, dict):
        current = {}

    current[key] = value
    current["last_updated_at"] = _now_iso()

    states[str(user_id)] = current

    save_json(STATE_FILE, states)


def get_login_temp(user_id: int, key: str, default=None):
    states = _load_local_map(STATE_FILE)

    current = states.get(str(user_id), {})

    if isinstance(current, dict):
        return current.get(key, default)

    return default


def clear_login_temp(user_id: int, *keys):
    states = _load_local_map(STATE_FILE)

    current = states.get(str(user_id), {})

    if not isinstance(current, dict):
        return

    if keys:
        for key in keys:
            current.pop(str(key), None)
    else:
        for key in [
            "phone",
            "phone_code_hash",
            "login_phone",
            "login_code",
            "login_password"
        ]:
            current.pop(key, None)

    current["last_updated_at"] = _now_iso()

    states[str(user_id)] = current

    save_json(STATE_FILE, states)


# =========================================================
# USERS
# =========================================================
def get_all_users():
    users = _load_local_map(USERS_FILE)
    if _should_use_local_hybrid_fast_path(USERS_FILE, SUPABASE_USERS_TABLE, "id", bool(users)):
        return users
    if _supabase_operational():
        try:
            rows = _select_rows(SUPABASE_USERS_TABLE) or []
            remote = {}
            for row in rows:
                uid = str(int(row.get("id", 0) or 0))
                if uid != "0":
                    remote[uid] = _normalize_user_record(int(uid), row)
            if ENABLE_LOCAL_FALLBACK:
                merged = dict(users)
                merged.update(remote)
                if merged != users:
                    _save_local_map(USERS_FILE, merged)
                _mark_hybrid_remote_refresh(USERS_FILE, SUPABASE_USERS_TABLE, "id")
                return merged
            _mark_hybrid_remote_refresh(USERS_FILE, SUPABASE_USERS_TABLE, "id")
            return remote
        except Exception:
            pass
    return users


def save_all_users(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(USERS_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_user_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_USERS_TABLE, rows, conflict_columns="id")
        except Exception:
            pass


def register_user(user):
    if not user:
        return
    user_id = int(getattr(user, "id", 0) or 0)
    if user_id <= 0:
        return
    users = get_all_users()
    uid = str(user_id)
    is_new_user = uid not in users
    first_name = getattr(user, "first_name", "") or ""
    username = getattr(user, "username", "") or ""
    is_currently_banned = is_banned(user_id)
    current = _normalize_user_record(user_id, users.get(uid, {}))
    last_seen_dt = _parse_iso(current.get("last_seen", ""))
    recently_saved = bool(last_seen_dt and (_now_utc() - last_seen_dt).total_seconds() < _REGISTER_USER_WRITE_INTERVAL_SECONDS)
    should_skip_write = (
        not is_new_user
        and recently_saved
        and str(current.get("first_name", "") or "") == first_name
        and str(current.get("username", "") or "") == username
        and bool(current.get("is_banned", False)) == bool(is_currently_banned)
    )
    if not should_skip_write:
        users[uid] = _normalize_user_record(
            user_id,
            {
                "first_name": first_name,
                "username": username,
                "last_seen": _utcnow_naive_iso(),
                "is_banned": is_currently_banned,
            },
        )
        save_all_users(users)
    if is_new_user:
        increment_stat("users_registered", 1)
    touch_last_activity()


def user_count() -> int:
    return len(get_all_users())


def get_recent_users(limit: int = 10):
    users = list(get_all_users().values())
    users.sort(key=lambda item: str(item.get("last_seen", "")), reverse=True)
    return users[: max(1, int(limit))]


def get_all_users_sorted():
    users = list(get_all_users().values())
    users.sort(key=lambda item: (str(item.get("last_seen", "")), int(item.get("id", 0))), reverse=True)
    return users


def get_all_users_page(limit: int = 20, offset: int = 0):
    users = get_all_users_sorted()
    start = max(0, int(offset or 0))
    end = start + max(1, int(limit or 20))
    return users[start:end]


# =========================================================
# BANNED USERS
# =========================================================
def get_banned_users():
    data = load_json(BANNED_FILE, [])
    local = set(int(item) for item in data if str(item).lstrip("-").isdigit())
    if _should_use_local_hybrid_fast_path(BANNED_FILE, SUPABASE_BANNED_TABLE, "user_id", bool(local)):
        return local
    if _supabase_operational():
        try:
            rows = _select_rows(SUPABASE_BANNED_TABLE) or []
            remote = set()
            for row in rows:
                user_id = _to_int(row.get("user_id", 0), 0)
                if user_id > 0:
                    remote.add(user_id)
            if ENABLE_LOCAL_FALLBACK:
                merged = set(local)
                merged.update(remote)
                if merged != local:
                    save_json(BANNED_FILE, sorted(merged))
                _mark_hybrid_remote_refresh(BANNED_FILE, SUPABASE_BANNED_TABLE, "user_id")
                return merged
            _mark_hybrid_remote_refresh(BANNED_FILE, SUPABASE_BANNED_TABLE, "user_id")
            return remote
        except Exception:
            pass
    return local


def save_banned_users(data):
    clean = sorted({int(item) for item in data if str(item).lstrip("-").isdigit()})
    save_json(BANNED_FILE, clean)
    if _supabase_operational():
        try:
            rows = [_normalize_banned_user_record(user_id, {"updated_at": _now_iso()}) for user_id in clean]
            _replace_table_rows(SUPABASE_BANNED_TABLE, rows)
        except Exception:
            pass
    users = get_all_users()
    changed = False
    for uid, row in list(users.items()):
        row["is_banned"] = int(uid) in set(clean)
        changed = True
    if changed:
        save_all_users(users)


def is_banned(user_id: int) -> bool:
    return int(user_id) in get_banned_users()


def ban_user(user_id: int):
    banned = get_banned_users()
    banned.add(int(user_id))
    save_banned_users(banned)


def unban_user(user_id: int):
    banned = get_banned_users()
    banned.discard(int(user_id))
    save_banned_users(banned)


def banned_count() -> int:
    return len(get_banned_users())


# =========================================================
# PREMIUM SYSTEM
# =========================================================
def get_all_premium_users():
    return _get_hybrid_map(PREMIUM_FILE, SUPABASE_PREMIUM_TABLE, "user_id", _normalize_premium_record)


def save_all_premium_users(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(PREMIUM_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_premium_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_PREMIUM_TABLE, rows, conflict_columns="user_id")
        except Exception:
            pass
    sync_premium_stats()


def get_premium_record(user_id: int):
    all_users = get_all_premium_users()
    raw = all_users.get(str(user_id), {})
    return _normalize_premium_record(user_id, raw)


def save_premium_record(user_id: int, data: dict):
    current = get_premium_record(user_id)
    if isinstance(data, dict):
        current.update(data)
    current = _normalize_premium_record(user_id, current)
    current["updated_at"] = _now_iso()
    _upsert_hybrid_map_record(PREMIUM_FILE, SUPABASE_PREMIUM_TABLE, "user_id", user_id, current, _normalize_premium_record)
    sync_premium_stats()
    return get_premium_record(user_id)


def delete_premium_record(user_id: int):
    _delete_hybrid_map_record(PREMIUM_FILE, SUPABASE_PREMIUM_TABLE, "user_id", user_id)
    sync_premium_stats()


def _compute_expiry_from_duration(duration_text: str):
    duration_text = str(duration_text or "").strip().lower()
    if not duration_text:
        return ""
    match = re.fullmatch(r"(\d+)\s*([dhmwy]|day|days|hour|hours|month|months|week|weeks|year|years)", duration_text)
    if not match:
        return ""
    value = int(match.group(1))
    unit = match.group(2)
    now = _now_utc()
    if unit in {"h", "hour", "hours"}:
        return (now + timedelta(hours=value)).isoformat()
    if unit in {"d", "day", "days"}:
        return (now + timedelta(days=value)).isoformat()
    if unit in {"w", "week", "weeks"}:
        return (now + timedelta(weeks=value)).isoformat()
    if unit in {"m", "month", "months"}:
        return (now + timedelta(days=30 * value)).isoformat()
    if unit in {"y", "year", "years"}:
        return (now + timedelta(days=365 * value)).isoformat()
    return ""


def is_premium_expired(user_id: int) -> bool:
    record = get_premium_record(user_id)
    if not record.get("is_premium"):
        return True
    expiry = _parse_iso(record.get("premium_expires_at", ""))
    if not expiry:
        return False
    if PREMIUM_GRACE_HOURS > 0:
        expiry = expiry + timedelta(hours=int(PREMIUM_GRACE_HOURS))
    return _now_utc() >= expiry


def is_premium_user(user_id: int) -> bool:
    record = get_premium_record(user_id)
    if not record.get("is_premium"):
        return False
    if is_premium_expired(user_id):
        remove_premium(user_id)
        return False
    return True


def add_premium(user_id: int, duration_text: str = "", granted_by: int = 0, plan_name: str = DEFAULT_PREMIUM_PLAN_NAME, notes: str = ""):
    expires_at = _compute_expiry_from_duration(duration_text) if duration_text else ""
    return save_premium_record(
        user_id,
        {
            "is_premium": True,
            "plan_name": str(plan_name or DEFAULT_PREMIUM_PLAN_NAME),
            "premium_expires_at": expires_at,
            "granted_by": int(granted_by or 0),
            "granted_at": _now_iso(),
            "notes": str(notes or ""),
        },
    )


def remove_premium(user_id: int):
    return save_premium_record(
        user_id,
        {
            "is_premium": False,
            "plan_name": "",
            "premium_expires_at": "",
            "notes": "",
        },
    )


def get_premium_expiry_text(user_id: int) -> str:
    return str(get_premium_record(user_id).get("premium_expires_at", "") or "")


def get_user_plan_name(user_id: int) -> str:
    record = get_premium_record(user_id)
    plan_name = str(record.get("plan_name", "") or "").strip()
    if plan_name:
        return plan_name
    return DEFAULT_PREMIUM_PLAN_NAME if is_premium_user(user_id) else DEFAULT_PLAN_NAME


def _split_plan_features(value) -> list[str]:
    if isinstance(value, (list, tuple, set)):
        raw_parts = [str(item or "") for item in value]
    else:
        raw_text = str(value or "").replace("\r", "\n")
        raw_parts = []
        for line in raw_text.splitlines():
            raw_parts.extend(line.split("|"))

    items = []
    seen = set()
    for part in raw_parts:
        cleaned = str(part or "").strip().lstrip("-").lstrip("•").strip()
        if not cleaned:
            continue
        lowered = cleaned.lower()
        if lowered in seen:
            continue
        seen.add(lowered)
        items.append(cleaned)
    return items


def get_user_plan_features(user_id: int) -> list[str]:
    record = get_premium_record(user_id)
    return _split_plan_features(record.get("notes", ""))


def set_user_plan_name(user_id: int, plan_name: str, updated_by: int = 0):
    payload = {"plan_name": str(plan_name or "").strip()}
    if updated_by:
        payload["granted_by"] = int(updated_by)
    return save_premium_record(user_id, payload)


def set_user_plan_features(user_id: int, features_text, updated_by: int = 0):
    normalized = "\n".join(_split_plan_features(features_text))
    payload = {"notes": normalized}
    if updated_by:
        payload["granted_by"] = int(updated_by)
    return save_premium_record(user_id, payload)



# =========================================================
# CUSTOM USER LIMITS / STORAGE ACCESS
# =========================================================
def get_all_user_limits():
    return _get_hybrid_map(USER_LIMITS_FILE, SUPABASE_USER_LIMITS_TABLE, "user_id", _normalize_user_limit_record)


def save_all_user_limits(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(USER_LIMITS_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_user_limit_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_USER_LIMITS_TABLE, rows, conflict_columns="user_id")
        except Exception:
            pass


def _normalize_user_limit_record(user_id: int, data=None):
    data = data or {}
    return {
        "user_id": int(user_id),
        "batch_limit": max(0, _to_int(data.get("batch_limit", 0), 0)),
        "task_limit": max(0, _to_int(data.get("task_limit", 0), 0)),
        "allowed_storage_modes": str(data.get("allowed_storage_modes", "") or ""),
    }


def get_user_limit_record(user_id: int):
    return _normalize_user_limit_record(user_id, get_all_user_limits().get(str(user_id), {}))


def save_user_limit_record(user_id: int, data: dict):
    limits = get_all_user_limits()
    current = get_user_limit_record(user_id)
    if isinstance(data, dict):
        current.update(data)
    limits[str(user_id)] = _normalize_user_limit_record(user_id, current)
    save_all_user_limits(limits)
    return limits[str(user_id)]


def get_user_allowed_storage_modes(user_id: int):
    record = get_user_limit_record(user_id)
    raw = [item.strip().lower() for item in str(record.get("allowed_storage_modes", "")).split(",") if item.strip()]
    if raw:
        return raw
    plan_name = str(get_premium_record(user_id).get("plan_name", "") or "").strip().lower()
    if plan_name == "pro":
        return list(dict.fromkeys([*PRO_STORAGE_MODES, "telegram", "gdrive", "rclone", "personal_bot"]))
    if is_premium_user(user_id):
        return list(dict.fromkeys([*PREMIUM_STORAGE_MODES, "telegram", "gdrive", "rclone"]))
    # Keep the core storage routes available by default so UI toggles do not look broken
    # when a deployment forgets to expose the newer storage-mode env values.
    return list(dict.fromkeys([*FREE_STORAGE_MODES, "telegram", "gdrive", "rclone"]))


def user_can_use_storage_mode(user_id: int, storage_mode: str) -> bool:
    storage_mode = str(storage_mode or "telegram").strip().lower()
    if storage_mode == "personal_bot":
        return "personal_bot" in get_user_allowed_storage_modes(user_id)
    return storage_mode in get_user_allowed_storage_modes(user_id)


def get_user_batch_limit(user_id: int) -> int:
    custom = get_user_limit_record(user_id).get("batch_limit", 0)
    if custom:
        return custom
    return PREMIUM_MAX_BATCH_LINKS if is_premium_user(user_id) else FREE_MAX_BATCH_LINKS


def get_user_task_limit(user_id: int) -> int:
    custom = get_user_limit_record(user_id).get("task_limit", 0)
    if custom:
        return custom
    return PREMIUM_MAX_TASKS_PER_USER if is_premium_user(user_id) else FREE_MAX_TASKS_PER_USER



def cleanup_expired_premium_users(force: bool = False):
    global _LAST_PREMIUM_CLEANUP_AT
    now = time.time()
    if not force and (now - float(_LAST_PREMIUM_CLEANUP_AT or 0.0)) < _PREMIUM_CLEANUP_INTERVAL_SECONDS:
        return False
    _LAST_PREMIUM_CLEANUP_AT = now
    changed = False
    all_users = get_all_premium_users()
    for uid in list(all_users.keys()):
        record = _normalize_premium_record(int(uid), all_users.get(uid, {}))
        if record.get("is_premium") and is_premium_expired(int(uid)):
            record["is_premium"] = False
            record["plan_name"] = ""
            record["premium_expires_at"] = ""
            record["updated_at"] = _now_iso()
            all_users[uid] = record
            changed = True
    if changed:
        save_all_premium_users(all_users)
    return changed


# =========================================================
# SETTINGS MARKS / UI HELPERS
# =========================================================
def is_value_set(value) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value != 0
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return value is not None


def setting_mark(value) -> str:
    return "✅" if is_value_set(value) else "❌"


def get_upload_mode_label(user_id: int) -> str:
    mode = get_user_settings(user_id).get("upload_mode", "media")
    return "Document" if mode == "document" else "Media"


# =========================================================
# INDEX STORAGE
# =========================================================
def get_all_index_entries():
    local = _load_local_list(INDEX_FILE)
    local_rows = {}
    for offset, row in enumerate(local, start=1):
        if not isinstance(row, dict):
            continue
        index_no = max(1, _to_int(row.get("index_no", offset), offset))
        local_rows[index_no] = _normalize_index_entry_record(index_no, row)
    if _should_use_local_hybrid_fast_path(INDEX_FILE, SUPABASE_INDEX_TABLE, "index_no", bool(local_rows)):
        return [local_rows[key] for key in sorted(local_rows)]

    if _supabase_operational():
        try:
            rows = _select_rows(SUPABASE_INDEX_TABLE) or []
            remote_rows = {}
            for row in rows:
                index_no = _to_int(row.get("index_no", 0), 0)
                if index_no > 0:
                    remote_rows[index_no] = _normalize_index_entry_record(index_no, row)
            if ENABLE_LOCAL_FALLBACK:
                merged_rows = dict(local_rows)
                merged_rows.update(remote_rows)
                merged = [merged_rows[key] for key in sorted(merged_rows)]
                if merged != local:
                    _save_local_list(INDEX_FILE, merged)
                _mark_hybrid_remote_refresh(INDEX_FILE, SUPABASE_INDEX_TABLE, "index_no")
                return merged
            _mark_hybrid_remote_refresh(INDEX_FILE, SUPABASE_INDEX_TABLE, "index_no")
            return [remote_rows[key] for key in sorted(remote_rows)]
        except Exception:
            pass

    return [local_rows[key] for key in sorted(local_rows)]


def save_all_index_entries(data):
    normalized = []
    for offset, row in enumerate(data if isinstance(data, list) else [], start=1):
        if not isinstance(row, dict):
            continue
        index_no = max(1, _to_int(row.get("index_no", offset), offset))
        normalized.append(_normalize_index_entry_record(index_no, row))
    normalized.sort(key=lambda item: int(item.get("index_no", 0) or 0))
    _save_local_list(INDEX_FILE, normalized)
    if _supabase_operational():
        try:
            _replace_table_rows(SUPABASE_INDEX_TABLE, normalized)
        except Exception:
            pass


def add_index_entry(entry: dict):
    entries = get_all_index_entries()
    clean_entry = dict(entry) if isinstance(entry, dict) else {}
    clean_entry["index_no"] = len(entries) + 1
    clean_entry["indexed_at"] = _utcnow_naive_iso()
    entries.append(clean_entry)
    save_all_index_entries(entries)
    return clean_entry["index_no"]


def index_count() -> int:
    return len(get_all_index_entries())


def get_last_index_no(user_id: int = None) -> int:
    entries = get_all_index_entries()
    if not entries:
        return 0
    if user_id is None:
        return int(entries[-1].get("index_no", 0) or 0)
    user_entries = [row for row in entries if str(row.get("user_id")) == str(user_id)]
    if not user_entries:
        return 0
    return int(user_entries[-1].get("index_no", 0) or 0)


def format_index_number(index_no: int, padding: int = 2) -> str:
    try:
        return str(max(0, int(index_no))).zfill(max(1, int(padding)))
    except Exception:
        return str(max(0, _to_int(index_no, 0))).zfill(max(1, _to_int(padding, 2)))


def get_index_state():
    return _get_hybrid_map(INDEX_STATE_FILE, SUPABASE_INDEX_STATE_TABLE, "user_id", _normalize_index_state_record)


def save_index_state(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(INDEX_STATE_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_index_state_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_INDEX_STATE_TABLE, rows, conflict_columns="user_id")
        except Exception:
            pass


def _default_index_state():
    return {"enabled": False, "count": 0, "user_start_offset": 0, "user_current_index": 0, "last_reset_at": ""}


def set_index_mode(user_id: int, enabled: bool):
    state = get_index_state()
    current = _normalize_index_state(state.get(str(user_id), _default_index_state()))
    current["enabled"] = bool(enabled)
    state[str(user_id)] = current
    save_index_state(state)
    update_user_settings(user_id, {"index_mode": bool(enabled)})


def is_index_mode(user_id: int) -> bool:
    state_enabled = bool(get_index_state().get(str(user_id), {}).get("enabled", False))
    settings_enabled = bool(get_user_settings(user_id).get("index_mode", False))
    return state_enabled or settings_enabled


def increase_index_user_count(user_id: int):
    state = get_index_state()
    current = _normalize_index_state(state.get(str(user_id), _default_index_state()))
    current["count"] += 1
    current["user_current_index"] += 1
    state[str(user_id)] = current
    save_index_state(state)
    return current["count"]


def get_index_user_count(user_id: int) -> int:
    return int(get_index_state().get(str(user_id), {}).get("count", 0) or 0)


def reset_user_index_counter(user_id: int):
    state = get_index_state()
    current = _normalize_index_state(state.get(str(user_id), _default_index_state()))
    current["user_current_index"] = 0
    current["last_reset_at"] = _utcnow_naive_iso()
    state[str(user_id)] = current
    save_index_state(state)
    return 0


def reset_index_user_count(user_id: int):
    state = get_index_state()
    current = _normalize_index_state(state.get(str(user_id), _default_index_state()))
    current["count"] = 0
    current["user_current_index"] = 0
    current["last_reset_at"] = _utcnow_naive_iso()
    state[str(user_id)] = current
    save_index_state(state)
    return 0


def get_user_current_index(user_id: int) -> int:
    return int(get_index_state().get(str(user_id), {}).get("user_current_index", 0) or 0)


def get_next_user_index(user_id: int) -> int:
    return get_user_current_index(user_id) + 1


# =========================================================
# BATCH HELPERS
# =========================================================
def set_batch_mode(user_id: int, enabled: bool):
    update_user_settings(user_id, {"batch_mode": bool(enabled)})


def is_batch_mode(user_id: int) -> bool:
    return bool(get_user_settings(user_id).get("batch_mode", False))


def save_batch_input(user_id: int, raw_text: str):
    update_user_settings(user_id, {"batch_last_input": str(raw_text or "")})


def get_batch_input(user_id: int) -> str:
    return str(get_user_settings(user_id).get("batch_last_input", "") or "")


def clear_batch_input(user_id: int):
    update_user_settings(user_id, {"batch_last_input": ""})


def _normalize_batch_token(token: str) -> str:
    token = str(token or "").strip()
    token = token.strip("[](){}<>\"'")
    return token.rstrip(".,;")


def _expand_tme_range_link(link: str):
    link = _normalize_batch_token(link)
    if not link:
        return []
    link = link.split("?", 1)[0].split("#", 1)[0].rstrip("/")

    # Normalize schema and domains
    if link.startswith("t.me/"):
        link = "https://" + link
    elif link.startswith("http://"):
        link = "https://" + link[7:]
    link = re.sub(r"^https://(?:telegram\.(?:me|dog))/+", "https://t.me/", link)

    if not link.startswith("https://t.me/"):
        return []

    # Support range patterns with -, .., or :
    # E.g. https://t.me/c/123456/10-20 or 10..20 or 10:20
    private_range = re.fullmatch(r"(https://t\.me/c/\d+/)(\d+)(?:-|\.\.|:)(\d+)", link)
    private_topic_range = re.fullmatch(r"(https://t\.me/c/\d+/\d+/)(\d+)(?:-|\.\.|:)(\d+)", link)
    public_range = re.fullmatch(r"(https://t\.me/[A-Za-z0-9_]+/)(\d+)(?:-|\.\.|:)(\d+)", link)
    public_topic_range = re.fullmatch(r"(https://t\.me/[A-Za-z0-9_]+/\d+/)(\d+)(?:-|\.\.|:)(\d+)", link)
    bot_range = re.fullmatch(r"(https://t\.me/b/[A-Za-z0-9_]+/)(\d+)(?:-|\.\.|:)(\d+)", link)

    private_single = re.fullmatch(r"https://t\.me/c/\d+/\d+", link)
    private_topic_single = re.fullmatch(r"https://t\.me/c/\d+/\d+/\d+", link)
    public_single = re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+/\d+", link)
    public_topic_single = re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+/\d+/\d+", link)
    bot_single = re.fullmatch(r"https://t\.me/b/[A-Za-z0-9_]+/\d+", link)

    for match in (private_range, private_topic_range, public_range, public_topic_range, bot_range):
        if match:
            prefix = match.group(1)
            start = int(match.group(2))
            end = int(match.group(3))
            if start > end:
                start, end = end, start
            # Safety limit: max 2000 links per range
            if end - start > 2000:
                end = start + 2000
            return [f"{prefix}{message_id}" for message_id in range(start, end + 1)]

    if private_single or private_topic_single or public_single or public_topic_single or bot_single:
        return [link]
    return []


def parse_batch_links(raw_text: str):
    if not raw_text:
        return []
    tokens = []
    # Support comma, tab, space, newline separation
    for line in str(raw_text).replace(",", "\n").splitlines():
        line = line.strip()
        if not line:
            continue
        tokens.extend(part.strip() for part in line.split() if part.strip())

    links = []
    seen = set()
    for token in tokens:
        for link in _expand_tme_range_link(token):
            if link not in seen:
                seen.add(link)
                links.append(link)
    return links



# =========================================================
# USER SESSIONS
# =========================================================
def get_all_user_sessions():
    return _get_hybrid_map(SESSION_STORE_FILE, SUPABASE_SESSIONS_TABLE, "user_id", _normalize_session_record)


def save_all_user_sessions(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(SESSION_STORE_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for uid, row in data.items():
                rows.append(_normalize_session_record(int(uid), row))
            if rows:
                _upsert_rows(SUPABASE_SESSIONS_TABLE, rows, conflict_columns="user_id")
        except Exception:
            pass


def save_user_session(user_id: int, session_string: str, tg_user_id: int = 0, phone: str = ""):
    sessions = get_all_user_sessions()
    sessions[str(user_id)] = _normalize_session_record(
        user_id,
        {
            "session_string": session_string,
            "tg_user_id": tg_user_id,
            "phone": phone,
            "saved_at": _utcnow_naive_iso(),
        },
    )
    save_all_user_sessions(sessions)
    update_user_settings(user_id, {"authorized_mode": True, "last_login_user_id": int(tg_user_id or 0)})


def get_user_session(user_id: int):
    return get_all_user_sessions().get(str(user_id), {})


def get_user_session_string(user_id: int) -> str:
    return str(get_user_session(user_id).get("session_string", "") or "")


def has_user_session(user_id: int) -> bool:
    return bool(get_user_session_string(user_id))


def delete_user_session(user_id: int):
    sessions = get_all_user_sessions()
    sessions.pop(str(user_id), None)
    save_all_user_sessions(sessions)
    update_user_settings(user_id, {"authorized_mode": False, "last_login_user_id": 0})


# =========================================================
# TASKS
# =========================================================
def _set_tasks_cache(data):
    global _TASKS_CACHE, _TASKS_CACHE_LOADED_AT
    _TASKS_CACHE = data if isinstance(data, dict) else {}
    _TASKS_CACHE_LOADED_AT = time.time()
    return _TASKS_CACHE


def _normalize_task_map(data):
    raw_map = data if isinstance(data, dict) else {}
    normalized_map = {}
    changed = False
    for task_id, row in raw_map.items():
        normalized = _normalize_task_record(task_id, row)
        normalized_map[str(task_id)] = normalized
        if normalized != row:
            changed = True
    return normalized_map, changed


def _should_use_cached_tasks(force_refresh: bool = False):
    if force_refresh:
        return False
    if not isinstance(_TASKS_CACHE, dict):
        return False
    if not _TASKS_CACHE:
        return True
    return (time.time() - float(_TASKS_CACHE_LOADED_AT or 0.0)) < _TASK_CACHE_TTL_SECONDS


def get_all_tasks(force_refresh: bool = False):
    if _should_use_cached_tasks(force_refresh=force_refresh):
        return _TASKS_CACHE

    local_tasks = _load_local_map(TASKS_FILE)
    normalized_local, local_changed = _normalize_task_map(local_tasks)
    if local_changed:
        _save_local_map(TASKS_FILE, normalized_local)
    else:
        normalized_local = local_tasks

    if _supabase_operational():
        try:
            rows = _select_rows(SUPABASE_TASKS_TABLE) or []
            remote = {}
            for row in rows:
                task_id = str(row.get("id", "") or "")
                if task_id:
                    remote[task_id] = _normalize_task_record(task_id, row)

            if ENABLE_LOCAL_FALLBACK:
                merged = dict(normalized_local)
                for task_id, remote_task in remote.items():
                    local_task = merged.get(task_id)
                    if not local_task:
                        merged[task_id] = remote_task
                        continue

                    local_dt = _parse_iso(local_task.get("updated_at") or local_task.get("created_at"))
                    remote_dt = _parse_iso(remote_task.get("updated_at") or remote_task.get("created_at"))

                    if local_dt and remote_dt:
                        if remote_dt > local_dt:
                            merged[task_id] = remote_task
                        else:
                            merged[task_id] = local_task
                    elif _task_status_rank(remote_task.get("status")) > _task_status_rank(local_task.get("status")):
                        merged[task_id] = remote_task
                    else:
                        merged[task_id] = local_task

                _save_local_map(TASKS_FILE, merged)
                return _set_tasks_cache(merged)

            return _set_tasks_cache(remote)
        except Exception:
            pass

    return _set_tasks_cache(normalized_local)


def _sync_local_banned_users_to_supabase(prune_missing: bool = False):
    data = load_json(BANNED_FILE, [])
    clean = sorted({int(item) for item in data if str(item).lstrip("-").isdigit()})
    rows = [_normalize_banned_user_record(user_id, {"updated_at": _now_iso()}) for user_id in clean]
    if prune_missing:
        _replace_table_rows(SUPABASE_BANNED_TABLE, rows)
    elif rows:
        _upsert_rows(SUPABASE_BANNED_TABLE, rows, conflict_columns="user_id")
    return {"total": len(clean), "prepared": len(rows), "skipped": 0, "synced": len(rows), "disabled": False}


def _sync_local_index_entries_to_supabase(prune_missing: bool = False):
    data = _load_local_list(INDEX_FILE)
    rows = []
    skipped = 0
    for offset, row in enumerate(data, start=1):
        if not isinstance(row, dict):
            skipped += 1
            continue
        index_no = max(1, _to_int(row.get("index_no", offset), offset))
        rows.append(_normalize_index_entry_record(index_no, row))
    if prune_missing:
        _replace_table_rows(SUPABASE_INDEX_TABLE, rows)
    elif rows:
        _upsert_rows(SUPABASE_INDEX_TABLE, rows, conflict_columns="index_no")
    return {"total": len(data), "prepared": len(rows), "skipped": skipped, "synced": len(rows), "disabled": False}


def _sync_local_stats_to_supabase():
    stats = _normalize_stats(load_json(STATS_FILE, DEFAULT_STATS))
    payload = dict(stats or {})
    payload["id"] = 1
    _upsert_rows(SUPABASE_STATS_TABLE, payload, conflict_columns="id")
    return {"total": 1, "prepared": 1, "skipped": 0, "synced": 1, "disabled": False}


def _sync_local_broadcast_logs_to_supabase(prune_missing: bool = False):
    logs = load_json(BROADCAST_LOG_FILE, [])
    if not isinstance(logs, list):
        logs = []
    rows = []
    skipped = 0
    for row in logs:
        try:
            clean = dict(row or {})
            clean["created_at"] = str(clean.get("created_at") or _utcnow_naive_iso())
            rows.append(clean)
        except Exception:
            skipped += 1
            continue
    if prune_missing:
        _replace_table_rows(SUPABASE_BROADCAST_TABLE, rows)
    elif rows:
        _upsert_rows(SUPABASE_BROADCAST_TABLE, rows, conflict_columns="created_at")
    return {"total": len(logs), "prepared": len(rows), "skipped": skipped, "synced": len(rows), "disabled": False}


def sync_local_persistent_data_to_supabase(force: bool = False, prune_missing: bool = False):
    if not (_supabase_operational() and ENABLE_LOCAL_FALLBACK and SYNC_LOCAL_TO_SUPABASE):
        return {"enabled": False, "synced": []}

    schema_state = ensure_supabase_schema(force=force)
    if not (isinstance(schema_state, dict) and schema_state.get("ready")):
        return {
            "enabled": True,
            "ready": False,
            "synced": [],
            "errors": [schema_state.get("message", "Supabase schema not ready")] if isinstance(schema_state, dict) else ["Supabase schema not ready"],
            "details": {},
        }

    synced = []
    errors = []
    details = {}

    def _run_map_sync(path: str, table: str, key_name: str, normalizer):
        if prune_missing:
            return _replace_full_local_map_on_supabase(path, table, normalizer)
        return _sync_full_local_map_to_supabase(path, table, key_name, normalizer)

    sync_jobs = [
        ("users", _run_map_sync, USERS_FILE, SUPABASE_USERS_TABLE, "id", _normalize_user_record),
        ("settings", _run_map_sync, SETTINGS_FILE, SUPABASE_SETTINGS_TABLE, "user_id", _normalize_settings_record),
        ("state", _run_map_sync, STATE_FILE, SUPABASE_STATE_TABLE, "user_id", _normalize_state_record),
        ("premium", _run_map_sync, PREMIUM_FILE, SUPABASE_PREMIUM_TABLE, "user_id", _normalize_premium_record),
        ("tasks", _run_map_sync, TASKS_FILE, SUPABASE_TASKS_TABLE, "id", _normalize_task_record),
        ("user_limits", _run_map_sync, USER_LIMITS_FILE, SUPABASE_USER_LIMITS_TABLE, "user_id", _normalize_user_limit_record),
        ("sessions", _run_map_sync, SESSION_STORE_FILE, SUPABASE_SESSIONS_TABLE, "user_id", _normalize_session_record),
        ("index_state", _run_map_sync, INDEX_STATE_FILE, SUPABASE_INDEX_STATE_TABLE, "user_id", _normalize_index_state_record),
        ("failed_tasks", _run_map_sync, FAILED_TASKS_FILE, SUPABASE_FAILED_TASKS_TABLE, "task_id", _normalize_failed_task_record),
        ("stats", _sync_local_stats_to_supabase),
        ("broadcast_logs", _sync_local_broadcast_logs_to_supabase, prune_missing),
        ("banned", _sync_local_banned_users_to_supabase, prune_missing),
        ("index_entries", _sync_local_index_entries_to_supabase, prune_missing),
    ]

    for job in sync_jobs:
        label, sync_fn, *args = job
        try:
            result = sync_fn(*args)
            if isinstance(result, dict):
                details[label] = result
            else:
                details[label] = {"synced": 0}
            synced.append(label)
        except Exception as error:
            errors.append(f"{label}: {error}")
            details[label] = {"error": str(error)}

    try:
        summary_bits = []
        for label in synced:
            info = details.get(label, {}) if isinstance(details.get(label, {}), dict) else {}
            summary_bits.append(f"{label}={int(info.get('synced', 0) or 0)}")
        debug_log("Supabase sync summary: " + ", ".join(summary_bits))
        if errors:
            debug_log("Supabase sync errors: " + " | ".join(errors[:10]))
    except Exception:
        pass

    return {"enabled": True, "synced": synced, "errors": errors, "schema_state": schema_state, "details": details}


def hydrate_local_files_from_supabase():
    if not _supabase_operational():
        return {"enabled": False, "hydrated": []}

    hydrated = []
    map_tables = [
        (USERS_FILE, SUPABASE_USERS_TABLE, "id", _normalize_user_record),
        (SETTINGS_FILE, SUPABASE_SETTINGS_TABLE, "user_id", _normalize_settings_record),
        (STATE_FILE, SUPABASE_STATE_TABLE, "user_id", _normalize_state_record),
        (PREMIUM_FILE, SUPABASE_PREMIUM_TABLE, "user_id", _normalize_premium_record),
        (TASKS_FILE, SUPABASE_TASKS_TABLE, "id", _normalize_task_record),
        (SESSION_STORE_FILE, SUPABASE_SESSIONS_TABLE, "user_id", _normalize_session_record),
        (USER_LIMITS_FILE, SUPABASE_USER_LIMITS_TABLE, "user_id", _normalize_user_limit_record),
        (INDEX_STATE_FILE, SUPABASE_INDEX_STATE_TABLE, "user_id", _normalize_index_state_record),
        (FAILED_TASKS_FILE, SUPABASE_FAILED_TASKS_TABLE, "task_id", _normalize_failed_task_record),
    ]

    for file_path, table, key_name, normalizer in map_tables:
        try:
            rows = _select_rows(table) or []
            if rows:
                local_map = _load_local_map(file_path)
                changed = False
                for row in rows:
                    typed_key = _coerce_supabase_key_value(table, row.get(key_name))
                    row_key = str(typed_key)
                    if row_key and row_key not in local_map:
                        local_map[row_key] = normalizer(typed_key, row)
                        changed = True
                if changed:
                    _save_local_map(file_path, local_map)
                    hydrated.append(table)
        except Exception:
            pass

    try:
        rows = _select_rows(SUPABASE_STATS_TABLE, {"id": 1}) or []
        if rows:
            save_json(STATS_FILE, _normalize_stats(rows[0]))
            hydrated.append(SUPABASE_STATS_TABLE)
    except Exception:
        pass

    try:
        rows = _select_rows(SUPABASE_BANNED_TABLE) or []
        if rows:
            local_banned = set(load_json(BANNED_FILE, []))
            for row in rows:
                uid = _to_int(row.get("user_id"), 0)
                if uid:
                    local_banned.add(uid)
            save_json(BANNED_FILE, sorted(local_banned))
            hydrated.append(SUPABASE_BANNED_TABLE)
    except Exception:
        pass

    return {"enabled": True, "hydrated": hydrated}


def flush_all_storage_caches():
    global _TASKS_CACHE, _TASKS_LAST_LOCAL_SAVE_AT, _LAST_ACTIVITY_SAVE_AT
    with _LOCK:
        if isinstance(_TASKS_CACHE, dict) and _TASKS_CACHE:
            _save_local_map(TASKS_FILE, _TASKS_CACHE)
            _TASKS_LAST_LOCAL_SAVE_AT = time.time()
        touch_last_activity(force=True)
        if _supabase_operational():
            try:
                _sync_tasks_to_supabase(prune_missing=False)
                _sync_stats_to_supabase()
            except Exception:
                pass


atexit.register(flush_all_storage_caches)


def save_all_tasks(data, *, sync_remote: bool = True, force_local: bool = True):
    global _TASKS_LAST_LOCAL_SAVE_AT, _TASKS_LAST_REMOTE_SYNC_AT
    data = data if isinstance(data, dict) else {}
    normalized = {str(task_id): _normalize_task_record(task_id, row) for task_id, row in data.items()}
    _set_tasks_cache(normalized)

    now = time.time()
    has_terminal = any(str((row or {}).get("status", "")).strip().lower() in _TERMINAL_TASK_STATUSES for row in normalized.values())
    should_write_local = force_local or has_terminal or (now - float(_TASKS_LAST_LOCAL_SAVE_AT or 0.0)) >= _TASK_LOCAL_FLUSH_INTERVAL_SECONDS
    if should_write_local:
        _save_local_map(TASKS_FILE, normalized)
        _TASKS_LAST_LOCAL_SAVE_AT = now

    should_sync_remote = (
        sync_remote
        and _supabase_operational()
        and (force_local or has_terminal or (now - float(_TASKS_LAST_REMOTE_SYNC_AT or 0.0)) >= _TASK_REMOTE_SYNC_INTERVAL_SECONDS)
    )
    if should_sync_remote:
        try:
            rows = []
            for task_id, row in normalized.items():
                rows.append(_normalize_task_record(task_id, row))
            if rows:
                _upsert_rows(SUPABASE_TASKS_TABLE, rows, conflict_columns="id")
                _TASKS_LAST_REMOTE_SYNC_AT = now
        except Exception:
            pass
    return normalized


def set_task(task_id: str, data: dict):
    all_tasks = get_all_tasks()
    current = all_tasks.get(str(task_id), {})
    if not isinstance(current, dict):
        current = {}
    previous_status = str(current.get("status", "") or "").strip().lower()
    incoming = dict(data or {})
    current.update(incoming)
    created = not current.get("created_at")
    if not current.get("created_at"):
        current["created_at"] = _utcnow_naive_iso()
        increment_stat("tasks_created", 1)
    current["updated_at"] = _utcnow_naive_iso()

    normalized = _normalize_task_record(task_id, current)
    all_tasks[str(task_id)] = normalized
    status = str(normalized.get("status", "") or "").strip().lower()
    is_terminal = status in _TERMINAL_TASK_STATUSES
    force_local = created or is_terminal or status != previous_status
    save_all_tasks(all_tasks, sync_remote=is_terminal, force_local=force_local)
    touch_last_activity(force=is_terminal)

    if status == "completed" and previous_status != "completed":
        increment_stat("tasks_completed", 1)
    elif status == "failed" and previous_status != "failed":
        increment_stat("tasks_failed", 1)
        log_failed_task(task_id, normalized)
    return normalized


def get_task(task_id: str):
    task = get_all_tasks().get(str(task_id), {})
    if not isinstance(task, dict):
        return {}
    return _normalize_task_record(task_id, task)


def delete_task(task_id: str):
    task_id = str(task_id)
    tasks = get_all_tasks()
    tasks.pop(task_id, None)
    save_all_tasks(tasks, sync_remote=True, force_local=True)
    if _supabase_operational():
        try:
            _delete_rows(SUPABASE_TASKS_TABLE, {"id": task_id})
        except Exception:
            pass


def get_user_tasks(user_id: int, limit: int = 20):
    tasks = list(get_all_tasks().values())
    tasks = [_normalize_task_record(task.get("id", ""), task) for task in tasks if str(task.get("user_id")) == str(user_id)]
    tasks.sort(key=lambda item: str(item.get("updated_at", "")), reverse=True)
    return tasks[: max(1, int(limit))]


def count_running_tasks(user_id: int) -> int:
    cleanup_stale_active_tasks()
    target_user_id = str(user_id)
    running = 0
    for task_id, task in get_all_tasks().items():
        if not isinstance(task, dict):
            continue
        normalized = _normalize_task_record(task_id, task)
        if str(normalized.get("user_id")) != target_user_id:
            continue
        if _is_countable_running_task(normalized):
            running += 1
    return running


def cleanup_old_tasks(hours: int = 24):
    tasks = get_all_tasks()
    cutoff = _now_utc() - timedelta(hours=max(1, int(hours)))
    changed = False
    for task_id, task in list(tasks.items()):
        updated = _parse_iso(task.get("updated_at") or task.get("created_at"))
        if updated and updated < cutoff:
            tasks.pop(task_id, None)
            changed = True
    if changed:
        save_all_tasks(tasks, sync_remote=True, force_local=True)
    return changed


# =========================================================
# STATS / FAILED TASKS / BROADCAST LOGS
# =========================================================
def get_stats():
    local = _normalize_stats(load_json(STATS_FILE, DEFAULT_STATS))
    if _supabase_operational():
        try:
            rows = _select_rows(SUPABASE_STATS_TABLE, {"id": 1}) or []
            if rows:
                remote = _normalize_stats(rows[0])
                if ENABLE_LOCAL_FALLBACK:
                    save_json(STATS_FILE, remote)
                return remote
        except Exception:
            pass
    return local


def save_stats(data: dict):
    clean = _normalize_stats(data or {})
    save_json(STATS_FILE, clean)
    if _supabase_operational():
        try:
            payload = dict(clean)
            payload["id"] = 1
            _upsert_rows(SUPABASE_STATS_TABLE, payload, conflict_columns="id")
        except Exception:
            pass
    return clean


def increment_stat(key: str, amount: int = 1):
    stats = get_stats()
    stats[key] = max(0, _to_int(stats.get(key, 0), 0) + int(amount))
    if not stats.get("started_at"):
        stats["started_at"] = _utcnow_naive_iso()
    stats["last_activity_at"] = _utcnow_naive_iso()
    return save_stats(stats)


def touch_last_activity(force: bool = False):
    global _LAST_ACTIVITY_SAVE_AT
    now = time.time()
    if not force and (now - float(_LAST_ACTIVITY_SAVE_AT or 0.0)) < _LAST_ACTIVITY_FLUSH_INTERVAL_SECONDS:
        return None
    stats = get_stats()
    if not stats.get("started_at"):
        stats["started_at"] = _utcnow_naive_iso()
    stats["last_activity_at"] = _utcnow_naive_iso()
    _LAST_ACTIVITY_SAVE_AT = now
    return save_stats(stats)


def sync_premium_stats():
    premium_users = 0
    for uid, row in get_all_premium_users().items():
        record = _normalize_premium_record(int(uid), row)
        if record.get("is_premium") and not is_premium_expired(int(uid)):
            premium_users += 1
    stats = get_stats()
    stats["premium_users"] = premium_users
    save_stats(stats)
    return premium_users


def get_failed_tasks():
    return _get_hybrid_map(FAILED_TASKS_FILE, SUPABASE_FAILED_TASKS_TABLE, "task_id", _normalize_failed_task_record)


def save_failed_tasks(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(FAILED_TASKS_FILE, data)
    if _supabase_operational():
        try:
            rows = []
            for task_id, row in data.items():
                rows.append(_normalize_failed_task_record(task_id, row))
            _replace_table_rows(SUPABASE_FAILED_TASKS_TABLE, rows)
        except Exception:
            pass


def log_failed_task(task_id: str, task_data: dict):
    failed = get_failed_tasks()
    failed[str(task_id)] = {
        "task": _normalize_task_record(task_id, task_data),
        "logged_at": _utcnow_naive_iso(),
    }
    save_failed_tasks(failed)


def clear_failed_task(task_id: str):
    failed = get_failed_tasks()
    failed.pop(str(task_id), None)
    save_failed_tasks(failed)


def get_broadcast_logs():
    local = load_json(BROADCAST_LOG_FILE, [])
    if not isinstance(local, list):
        local = []
    if _supabase_operational():
        try:
            rows = _select_rows(SUPABASE_BROADCAST_TABLE) or []
            rows.sort(key=lambda item: str(item.get("created_at", "")), reverse=True)
            if ENABLE_LOCAL_FALLBACK:
                save_json(BROADCAST_LOG_FILE, rows)
            return rows
        except Exception:
            pass
    return local


def add_broadcast_log(entry: dict):
    logs = get_broadcast_logs()
    clean = dict(entry) if isinstance(entry, dict) else {}
    clean["created_at"] = clean.get("created_at") or _utcnow_naive_iso()
    logs.insert(0, clean)
    save_json(BROADCAST_LOG_FILE, logs[:500])
    if _supabase_operational():
        try:
            _upsert_rows(SUPABASE_BROADCAST_TABLE, clean, conflict_columns="created_at")
        except Exception:
            pass
    increment_stat("broadcast_runs", 1)
    return clean


# =========================================================
# SYSTEM HELPERS
# =========================================================
def hydrate_local_files():
    _ensure_dir()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    for path, default in [
        (SETTINGS_FILE, {}),
        (STATE_FILE, {}),
        (USERS_FILE, {}),
        (BANNED_FILE, []),
        (INDEX_FILE, []),
        (INDEX_STATE_FILE, {}),
        (SESSION_STORE_FILE, {}),
        (TASKS_FILE, {}),
        (PREMIUM_FILE, {}),
        (STATS_FILE, DEFAULT_STATS),
        (FAILED_TASKS_FILE, {}),
        (BROADCAST_LOG_FILE, []),
        (USER_LIMITS_FILE, {}),
    ]:
        if not os.path.exists(path):
            save_json(path, default)


def _persistent_backup_sources():
    return [
        ("settings", SETTINGS_FILE, {}),
        ("state", STATE_FILE, {}),
        ("users", USERS_FILE, {}),
        ("banned", BANNED_FILE, []),
        ("index_entries", INDEX_FILE, []),
        ("index_state", INDEX_STATE_FILE, {}),
        ("sessions", SESSION_STORE_FILE, {}),
        ("tasks", TASKS_FILE, {}),
        ("premium", PREMIUM_FILE, {}),
        ("stats", STATS_FILE, DEFAULT_STATS),
        ("failed_tasks", FAILED_TASKS_FILE, {}),
        ("broadcast_logs", BROADCAST_LOG_FILE, []),
        ("user_limits", USER_LIMITS_FILE, {}),
    ]


def clear_runtime_storage_cache():
    global _TASKS_CACHE, _TASKS_CACHE_LOADED_AT, _TASKS_LAST_LOCAL_SAVE_AT, _TASKS_LAST_REMOTE_SYNC_AT
    _TASKS_CACHE = None
    _TASKS_CACHE_LOADED_AT = 0.0
    _TASKS_LAST_LOCAL_SAVE_AT = 0.0
    _TASKS_LAST_REMOTE_SYNC_AT = 0.0
    clear_local_json_cache()


def create_backup_snapshot(label: str = "manual"):
    hydrate_local_files()
    os.makedirs(BACKUP_DIR, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(label or "manual")).strip("_") or "manual"
    path = os.path.join(BACKUP_DIR, f"code_devil_backup_{stamp}_{slug}.json")

    files = {}
    summary = {}
    for name, file_path, default in _persistent_backup_sources():
        payload = load_json(file_path, default)
        files[name] = payload
        if isinstance(payload, dict):
            summary[name] = len(payload)
        elif isinstance(payload, list):
            summary[name] = len(payload)
        else:
            summary[name] = 1 if payload else 0

    snapshot = {
        "version": 1,
        "created_at": _now_iso(),
        "label": slug,
        "files": files,
        "summary": summary,
        "supabase": get_supabase_status(),
    }
    save_json(path, snapshot)
    return {"path": path, "summary": summary, "created_at": snapshot["created_at"]}


def restore_backup_snapshot(path: str, sync_remote: bool = True):
    snapshot = load_json(path, {})
    files = snapshot.get("files", {}) if isinstance(snapshot, dict) else {}
    if not isinstance(files, dict) or not files:
        raise RuntimeError("Backup snapshot invalid hai ya files payload missing hai.")

    for name, file_path, default in _persistent_backup_sources():
        payload = files.get(name, deepcopy(default))
        save_json(file_path, payload)

    clear_runtime_storage_cache()

    sync_info = {"enabled": False, "synced": []}
    if sync_remote:
        sync_info = sync_local_persistent_data_to_supabase(force=True, prune_missing=True)

    return {
        "restored": [name for name, _, _ in _persistent_backup_sources()],
        "sync": sync_info,
    }


def initialize_storage():
    hydrate_local_files()
    if _supabase_enabled() and not _SUPABASE_BOOTSTRAP_ATTEMPTED:
        threading.Thread(target=ensure_supabase_schema, kwargs={"force": False}, daemon=True, name="supabase-bootstrap").start()
    normalize_existing_tasks_inplace()
    cleanup_stale_active_tasks(on_startup=True)
    cleanup_runtime_artifacts()
    touch_last_activity()
    cleanup_expired_premium_users(force=True)
    sync_premium_stats()



def get_detailed_stats():
    return _get_detailed_stats_impl(
        get_stats_fn=get_stats,
        get_all_users_sorted_fn=get_all_users_sorted,
        get_all_settings_fn=get_all_settings,
        get_all_tasks_fn=get_all_tasks,
        now_utc_fn=_now_utc,
        parse_iso_fn=_parse_iso,
        normalize_settings_fn=_normalize_settings,
        active_statuses=_ACTIVE_TASK_STATUSES,
        get_recent_users_fn=get_recent_users,
        has_user_session_fn=has_user_session,
        sync_premium_stats_fn=sync_premium_stats,
        timedelta_cls=timedelta,
    )


def analyze_batch_input(raw_text: str):
    return _analyze_batch_input_impl(
        raw_text,
        expand_range_fn=_expand_tme_range_link,
        parse_links_fn=parse_batch_links,
    )


def get_admin_overview(limit_recent_users: int = 5):
    return _get_admin_overview_impl(
        limit_recent_users,
        user_count_fn=user_count,
        banned_count_fn=banned_count,
        sync_premium_stats_fn=sync_premium_stats,
        recent_users_fn=get_recent_users,
        all_tasks_fn=get_all_tasks,
        is_running_task_fn=_is_countable_running_task,
        failed_tasks_fn=get_failed_tasks,
        stats_fn=get_stats,
    )


# =========================================================
# V13/V14/V15 HELPERS (APPENDED OVERRIDES)
# =========================================================
def get_user_storage_mode(user_id: int) -> str:
    return _get_user_storage_mode_from_settings_impl(get_user_settings(user_id))


def get_user_telegram_upload_mode(user_id: int) -> str:
    return _get_user_telegram_upload_mode_from_settings_impl(get_user_settings(user_id))


def get_settings_marks(user_id: int):
    settings = get_user_settings(user_id)
    storage_mode = str(settings.get("storage_mode", "telegram") or "telegram").strip().lower()
    caption_state = get_caption_settings_for_mode(settings, storage_mode)
    # Primary modular path (features/storage_marks_helpers.py)
    return _get_settings_marks_from_settings_impl(
        settings,
        caption_state=caption_state,
        has_session=has_user_session(user_id),
        is_premium=is_premium_user(user_id),
        setting_mark_fn=setting_mark,
    )
