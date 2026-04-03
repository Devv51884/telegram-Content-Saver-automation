
import json
import os
import re
from copy import deepcopy
from datetime import datetime, timedelta, timezone
from threading import Lock
from urllib import error as urllib_error
from urllib import parse as urllib_parse
from urllib import request as urllib_request

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
    DATA_DIR,
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
    SUPABASE_TIMEOUT,
    SUPABASE_SCHEMA,
    SUPABASE_USERS_TABLE,
    SUPABASE_SETTINGS_TABLE,
    SUPABASE_STATE_TABLE,
    SUPABASE_PREMIUM_TABLE,
    SUPABASE_TASKS_TABLE,
    SUPABASE_STATS_TABLE,
    SUPABASE_BROADCAST_TABLE,
    PREMIUM_GRACE_HOURS,
    TASK_STATUS_TTL_MINUTES,
)

_LOCK = Lock()
DATA_DIR = DATA_DIR or (os.path.dirname(SETTINGS_FILE) or "data")


DEFAULT_SETTINGS = {
    "upload_mode": DEFAULT_UPLOAD_MODE if str(DEFAULT_UPLOAD_MODE).lower() in {"media", "document"} else "document",
    "thumbnail_enabled": False,
    "thumbnail_file_id": "",
    "caption_enabled": False,
    "caption_text": "",
    "caption_parse_mode": "html",
    "caption_index_enabled": True,
    "caption_index_padding": 2,
    "caption_index_start": 1,
    "prefix": "",
    "suffix": "",
    "replace_words": "",
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
    "upload_destination": "",
    "topic_id": "",
    "index_mode": False,
    "authorized_mode": False,
    "last_login_user_id": 0,
    "batch_mode": False,
    "batch_last_input": "",
}

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
    "set_topic_id": "topic_id",
    "set_replace_words": "replace_words",
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


# =========================================================
# GENERIC HELPERS
# =========================================================
def load_json(path, default):
    if not os.path.exists(path):
        return deepcopy(default)
    try:
        with open(path, "r", encoding="utf-8") as file:
            return json.load(file)
    except Exception:
        return deepcopy(default)


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        json.dump(data, file, indent=2, ensure_ascii=False)


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


def _normalize_upload_mode(value) -> str:
    value = str(value or "").strip().lower()
    if value in {"document", "doc", "file"}:
        return "document"
    if value in {"media", "video", "telegram", "photo", "audio"}:
        return "media"
    return "document"


def _now_utc():
    return datetime.now(timezone.utc)


def _now_iso() -> str:
    return _now_utc().isoformat()


def _utcnow_naive_iso() -> str:
    return datetime.utcnow().isoformat()


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


def _task_last_seen_dt(task: dict):
    if not isinstance(task, dict):
        return None
    for key in ("updated_at", "created_at"):
        parsed = _parse_iso(task.get(key, ""))
        if parsed:
            return parsed
    return None


def _is_task_stale(task: dict) -> bool:
    if not isinstance(task, dict):
        return False
    status = str(task.get("status", "") or "").strip().lower()
    if status not in _ACTIVE_TASK_STATUSES:
        return False
    last_seen = _task_last_seen_dt(task)
    if not last_seen:
        return False
    age = _now_utc() - last_seen
    return age > timedelta(minutes=_TASK_STATUS_TTL)


def cleanup_stale_active_tasks():
    tasks = get_all_tasks()
    changed = False
    for task_id, task in list(tasks.items()):
        if not isinstance(task, dict):
            continue
        if _is_task_stale(task):
            task = dict(task)
            task["status"] = "failed"
            task["current_stage"] = "failed"
            task["error"] = task.get("error") or "Auto-closed stale task"
            task["updated_at"] = _utcnow_naive_iso()
            tasks[str(task_id)] = _normalize_task_record(task_id, task)
            changed = True
    if changed:
        save_all_tasks(tasks)
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


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


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
def _supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _supabase_headers(prefer: str = "return=representation"):
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
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
    return _supabase_request("GET", f"/rest/v1/{table}?select=*{_build_supabase_filters(filters)}")


def _delete_rows(table: str, filters=None):
    return _supabase_request("DELETE", f"/rest/v1/{table}?{_build_supabase_filters(filters).lstrip('&')}", prefer="return=minimal")


def _upsert_rows(table: str, rows, conflict_columns="id"):
    if not isinstance(rows, list):
        rows = [rows]
    if not rows:
        return []
    return _supabase_request(
        "POST",
        f"/rest/v1/{table}?on_conflict={conflict_columns}",
        rows,
    )


# =========================================================
# NORMALIZERS
# =========================================================
def _normalize_settings(data: dict):
    merged = deepcopy(DEFAULT_SETTINGS)
    if isinstance(data, dict):
        merged.update(data)
    merged["upload_mode"] = _normalize_upload_mode(merged.get("upload_mode", DEFAULT_SETTINGS["upload_mode"]))
    merged["caption_index_padding"] = max(1, _to_int(merged.get("caption_index_padding", 2), 2))
    merged["caption_index_start"] = max(0, _to_int(merged.get("caption_index_start", 1), 1))
    merged["filename_index_padding"] = max(1, _to_int(merged.get("filename_index_padding", 2), 2))
    merged["filename_index_start"] = max(0, _to_int(merged.get("filename_index_start", 1), 1))
    merged["last_login_user_id"] = _to_int(merged.get("last_login_user_id", 0), 0)

    bool_keys = {
        "thumbnail_enabled",
        "caption_enabled",
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


def _sync_full_local_map_to_supabase(path: str, table: str, key_name: str, normalizer):
    if not (_supabase_enabled() and ENABLE_LOCAL_FALLBACK and SYNC_LOCAL_TO_SUPABASE):
        return
    try:
        local_map = _load_local_map(path)
        rows = []
        for raw_key, raw_value in local_map.items():
            try:
                rows.append(normalizer(int(raw_key), raw_value))
            except Exception:
                continue
        if rows:
            _upsert_rows(table, rows, conflict_columns=key_name)
    except Exception:
        pass


def _get_hybrid_map(path: str, table: str, key_name: str, normalizer):
    local_map = _load_local_map(path)
    if _supabase_enabled():
        try:
            rows = _select_rows(table) or []
            remote_map = {}
            for row in rows:
                row_key = str(row.get(key_name))
                if row_key:
                    remote_map[row_key] = normalizer(int(row.get(key_name, 0) or 0), row)
            if ENABLE_LOCAL_FALLBACK:
                merged = dict(local_map)
                merged.update(remote_map)
                _save_local_map(path, merged)
                return merged
            return remote_map
        except Exception:
            _sync_full_local_map_to_supabase(path, table, key_name, normalizer)
    return local_map


def _upsert_hybrid_map_record(path: str, table: str, key_name: str, key_value: int, row: dict, normalizer):
    normalized = normalizer(int(key_value), row)
    local_map = _load_local_map(path)
    local_map[str(key_value)] = normalized
    _save_local_map(path, local_map)
    if _supabase_enabled():
        try:
            _upsert_rows(table, normalized, conflict_columns=key_name)
        except Exception:
            pass
    return normalized


def _delete_hybrid_map_record(path: str, table: str, key_name: str, key_value: int):
    local_map = _load_local_map(path)
    local_map.pop(str(key_value), None)
    _save_local_map(path, local_map)
    if _supabase_enabled():
        try:
            _delete_rows(table, {key_name: int(key_value)})
        except Exception:
            pass


# =========================================================
# SETTINGS
# =========================================================
def get_all_settings():
    return _get_hybrid_map(SETTINGS_FILE, SUPABASE_SETTINGS_TABLE, "user_id", _normalize_settings_record)


def _normalize_settings_record(user_id: int, data=None):
    normalized = _normalize_settings(data or {})
    normalized["user_id"] = int(user_id)
    normalized["updated_at"] = str((data or {}).get("updated_at", "") or "")
    return normalized


def save_all_settings(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(SETTINGS_FILE, data)
    if _supabase_enabled():
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
        merged = _normalize_settings(current)
        if uid not in all_settings or any(current.get(k) != merged.get(k) for k in merged.keys() if k != "user_id"):
            save_single_user_settings(user_id, merged)
        return _normalize_settings(merged)


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
    return _get_hybrid_map(STATE_FILE, SUPABASE_STATE_TABLE, "user_id", _normalize_state_record)


def save_all_states(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(STATE_FILE, data)
    if _supabase_enabled():
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
    current = get_all_states().get(str(user_id), {})
    if not isinstance(current, dict):
        current = {}
    current[key] = value
    current["last_updated_at"] = _now_iso()
    _upsert_hybrid_map_record(STATE_FILE, SUPABASE_STATE_TABLE, "user_id", user_id, current, _normalize_state_record)


def get_login_temp(user_id: int, key: str, default=None):
    current = get_all_states().get(str(user_id), {})
    if isinstance(current, dict):
        return current.get(key, default)
    return default


def clear_login_temp(user_id: int, *keys):
    current = get_all_states().get(str(user_id), {})
    if not isinstance(current, dict):
        return
    if keys:
        for key in keys:
            current.pop(str(key), None)
    else:
        for key in ["phone", "phone_code_hash", "login_phone", "login_code", "login_password"]:
            current.pop(key, None)
    current["last_updated_at"] = _now_iso()
    _upsert_hybrid_map_record(STATE_FILE, SUPABASE_STATE_TABLE, "user_id", user_id, current, _normalize_state_record)


# =========================================================
# USERS
# =========================================================
def get_all_users():
    users = _load_local_map(USERS_FILE)
    if _supabase_enabled():
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
                _save_local_map(USERS_FILE, merged)
                return merged
            return remote
        except Exception:
            pass
    return users


def save_all_users(data):
    data = data if isinstance(data, dict) else {}
    _save_local_map(USERS_FILE, data)
    if _supabase_enabled():
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
    users[str(user_id)] = _normalize_user_record(
        user_id,
        {
            "first_name": getattr(user, "first_name", "") or "",
            "username": getattr(user, "username", "") or "",
            "last_seen": _utcnow_naive_iso(),
            "is_banned": is_banned(user_id),
        },
    )
    save_all_users(users)
    increment_stat("users_registered", 1)
    touch_last_activity()


def user_count() -> int:
    return len(get_all_users())


def get_recent_users(limit: int = 10):
    users = list(get_all_users().values())
    users.sort(key=lambda item: str(item.get("last_seen", "")), reverse=True)
    return users[: max(1, int(limit))]


# =========================================================
# BANNED USERS
# =========================================================
def get_banned_users():
    data = load_json(BANNED_FILE, [])
    return set(int(item) for item in data if str(item).lstrip("-").isdigit())


def save_banned_users(data):
    clean = sorted({int(item) for item in data if str(item).lstrip("-").isdigit()})
    save_json(BANNED_FILE, clean)
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
    if _supabase_enabled():
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
    return DEFAULT_PREMIUM_PLAN_NAME if is_premium_user(user_id) else DEFAULT_PLAN_NAME


def get_user_batch_limit(user_id: int) -> int:
    return PREMIUM_MAX_BATCH_LINKS if is_premium_user(user_id) else FREE_MAX_BATCH_LINKS


def get_user_task_limit(user_id: int) -> int:
    return PREMIUM_MAX_TASKS_PER_USER if is_premium_user(user_id) else FREE_MAX_TASKS_PER_USER


def cleanup_expired_premium_users():
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
    mode = get_user_settings(user_id).get("upload_mode", "document")
    return "Document" if mode == "document" else "Media"


def get_settings_marks(user_id: int):
    settings = get_user_settings(user_id)
    return {
        "upload_mode": "📄" if settings.get("upload_mode") == "document" else "🎞",
        "thumbnail": setting_mark(settings.get("thumbnail_file_id")),
        "caption": "✅" if settings.get("caption_enabled") and settings.get("caption_text") else "❌",
        "prefix": setting_mark(settings.get("prefix")),
        "suffix": setting_mark(settings.get("suffix")),
        "auto_rename": setting_mark(
            settings.get("auto_rename")
            or settings.get("rename_template")
            or settings.get("filename_prefix")
            or settings.get("filename_suffix")
        ),
        "metadata": "✅" if settings.get("metadata_enabled") else "❌",
        "destination": setting_mark(settings.get("upload_destination")),
        "topic_id": setting_mark(settings.get("topic_id")),
        "replace_words": setting_mark(settings.get("replace_words")),
        "index_mode": "✅" if is_index_mode(user_id) else "❌",
        "login": "✅" if has_user_session(user_id) else "❌",
        "batch_mode": "✅" if settings.get("batch_mode") else "❌",
        "premium": "💎" if is_premium_user(user_id) else "🆓",
    }


# =========================================================
# INDEX STORAGE
# =========================================================
def get_all_index_entries():
    return _load_local_list(INDEX_FILE)


def save_all_index_entries(data):
    _save_local_list(INDEX_FILE, data)


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
    data = load_json(INDEX_STATE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_index_state(data):
    save_json(INDEX_STATE_FILE, data if isinstance(data, dict) else {})


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
    token = token.strip("[](){}<>")
    return token.rstrip(".,;")


def _expand_tme_range_link(link: str):
    link = _normalize_batch_token(link)
    link = link.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    if not link.startswith("https://t.me/"):
        return []

    private_range = re.fullmatch(r"(https://t\.me/c/\d+/)(\d+)-(\d+)", link)
    private_topic_range = re.fullmatch(r"(https://t\.me/c/\d+/\d+/)(\d+)-(\d+)", link)
    public_range = re.fullmatch(r"(https://t\.me/[A-Za-z0-9_]+/)(\d+)-(\d+)", link)
    public_topic_range = re.fullmatch(r"(https://t\.me/[A-Za-z0-9_]+/\d+/)(\d+)-(\d+)", link)

    private_single = re.fullmatch(r"https://t\.me/c/\d+/\d+", link)
    private_topic_single = re.fullmatch(r"https://t\.me/c/\d+/\d+/\d+", link)
    public_single = re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+/\d+", link)
    public_topic_single = re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+/\d+/\d+", link)

    for match in (private_range, private_topic_range, public_range, public_topic_range):
        if match:
            prefix = match.group(1)
            start = int(match.group(2))
            end = int(match.group(3))
            if start > end:
                start, end = end, start
            return [f"{prefix}{message_id}" for message_id in range(start, end + 1)]

    if private_single or private_topic_single or public_single or public_topic_single:
        return [link]
    return []
    private_range = re.fullmatch(r"(https://t\.me/c/\d+/)(\d+)-(\d+)", link)
    public_range = re.fullmatch(r"(https://t\.me/[A-Za-z0-9_]+/)(\d+)-(\d+)", link)
    private_single = re.fullmatch(r"https://t\.me/c/\d+/\d+", link)
    public_single = re.fullmatch(r"https://t\.me/[A-Za-z0-9_]+/\d+", link)

    if private_range:
        prefix = private_range.group(1)
        start = int(private_range.group(2))
        end = int(private_range.group(3))
        if start > end:
            start, end = end, start
        return [f"{prefix}{message_id}" for message_id in range(start, end + 1)]

    if public_range:
        prefix = public_range.group(1)
        start = int(public_range.group(2))
        end = int(public_range.group(3))
        if start > end:
            start, end = end, start
        return [f"{prefix}{message_id}" for message_id in range(start, end + 1)]

    if private_single or public_single:
        return [link]
    return []


def parse_batch_links(raw_text: str):
    if not raw_text:
        return []
    tokens = []
    for line in str(raw_text).splitlines():
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
    data = _load_local_map(SESSION_STORE_FILE)
    return data if isinstance(data, dict) else {}


def save_all_user_sessions(data):
    _save_local_map(SESSION_STORE_FILE, data if isinstance(data, dict) else {})


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
def get_all_tasks():
    local_tasks = _load_local_map(TASKS_FILE)
    normalized_local = {}
    local_changed = False
    for task_id, row in local_tasks.items():
        normalized = _normalize_task_record(task_id, row)
        normalized_local[str(task_id)] = normalized
        if normalized != row:
            local_changed = True
    if local_changed:
        _save_local_map(TASKS_FILE, normalized_local)
    else:
        normalized_local = local_tasks

    def _rank(status: str) -> int:
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

    if _supabase_enabled():
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
                    elif _rank(remote_task.get("status")) > _rank(local_task.get("status")):
                        merged[task_id] = remote_task
                    else:
                        merged[task_id] = local_task

                _save_local_map(TASKS_FILE, merged)
                return merged

            return remote
        except Exception:
            pass

    return normalized_local


def save_all_tasks(data):
    data = data if isinstance(data, dict) else {}
    normalized = {str(task_id): _normalize_task_record(task_id, row) for task_id, row in data.items()}
    _save_local_map(TASKS_FILE, normalized)
    if _supabase_enabled():
        try:
            rows = []
            for task_id, row in normalized.items():
                rows.append(_normalize_task_record(task_id, row))
            if rows:
                _upsert_rows(SUPABASE_TASKS_TABLE, rows, conflict_columns="id")
        except Exception:
            pass


def set_task(task_id: str, data: dict):
    all_tasks = get_all_tasks()
    current = all_tasks.get(str(task_id), {})
    if not isinstance(current, dict):
        current = {}
    incoming = dict(data or {})
    current.update(incoming)
    if not current.get("created_at"):
        current["created_at"] = _utcnow_naive_iso()
        increment_stat("tasks_created", 1)
    current["updated_at"] = _utcnow_naive_iso()

    normalized = _normalize_task_record(task_id, current)
    all_tasks[str(task_id)] = normalized
    save_all_tasks(all_tasks)
    touch_last_activity()

    if normalized.get("status") == "completed":
        increment_stat("tasks_completed", 1)
    elif normalized.get("status") == "failed":
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
    save_all_tasks(tasks)
    if _supabase_enabled():
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
    running_statuses = {"queued", "fetching", "downloading", "uploading", "processing", "retrying", "copying", "validating"}
    return sum(1 for task in get_user_tasks(user_id, limit=1000) if task.get("status") in running_statuses)


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
        save_all_tasks(tasks)
    return changed


# =========================================================
# STATS / FAILED TASKS / BROADCAST LOGS
# =========================================================
def get_stats():
    local = _normalize_stats(load_json(STATS_FILE, DEFAULT_STATS))
    if _supabase_enabled():
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
    if _supabase_enabled():
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


def touch_last_activity():
    stats = get_stats()
    if not stats.get("started_at"):
        stats["started_at"] = _utcnow_naive_iso()
    stats["last_activity_at"] = _utcnow_naive_iso()
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
    data = load_json(FAILED_TASKS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_failed_tasks(data):
    save_json(FAILED_TASKS_FILE, data if isinstance(data, dict) else {})


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
    if _supabase_enabled():
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
    if _supabase_enabled():
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
    ]:
        if not os.path.exists(path):
            save_json(path, default)


def initialize_storage():
    hydrate_local_files()
    normalize_existing_tasks_inplace()
    cleanup_stale_active_tasks()
    touch_last_activity()
    cleanup_expired_premium_users()
    sync_premium_stats()


def get_admin_overview(limit_recent_users: int = 5):
    return {
        "total_users": user_count(),
        "banned_users": banned_count(),
        "premium_users": sync_premium_stats(),
        "recent_users": get_recent_users(limit_recent_users),
        "running_tasks": len([task for task in get_all_tasks().values() if _is_countable_running_task(task)]),
        "failed_tasks": len(get_failed_tasks()),
        "stats": get_stats(),
    }
