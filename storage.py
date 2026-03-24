import json
import os
import re
from datetime import datetime, timedelta, timezone
from urllib import request as urllib_request
from urllib import error as urllib_error

from config import (
    SETTINGS_FILE,
    STATE_FILE,
    USERS_FILE,
    BANNED_FILE,
    INDEX_FILE,
    INDEX_STATE_FILE,
    SESSION_STORE_FILE,
    TASKS_FILE,
)

# ================= PREMIUM / SUPABASE CONFIG =================

DATA_DIR = os.path.dirname(SETTINGS_FILE) or "data"
PREMIUM_FILE = os.getenv("PREMIUM_FILE", os.path.join(DATA_DIR, "premium_users.json"))

SUPABASE_URL = str(os.getenv("SUPABASE_URL", "") or "").strip().rstrip("/")
SUPABASE_KEY = str(os.getenv("SUPABASE_KEY", "") or "").strip()
SUPABASE_PREMIUM_TABLE = str(os.getenv("SUPABASE_PREMIUM_TABLE", "premium_users") or "premium_users").strip()

FREE_MAX_BATCH_LINKS = int(os.getenv("FREE_MAX_BATCH_LINKS", "50") or "50")
PREMIUM_MAX_BATCH_LINKS = int(os.getenv("PREMIUM_MAX_BATCH_LINKS", "300") or "300")
FREE_MAX_TASKS_PER_USER = int(os.getenv("FREE_MAX_TASKS_PER_USER", "3") or "3")
PREMIUM_MAX_TASKS_PER_USER = int(os.getenv("PREMIUM_MAX_TASKS_PER_USER", "10") or "10")


DEFAULT_SETTINGS = {
    # Upload Mode
    # Supported internally:
    # - media
    # - document
    "upload_mode": "media",

    # Thumbnail
    "thumbnail_enabled": False,
    "thumbnail_file_id": "",

    # Caption
    "caption_enabled": False,
    "caption_text": "",
    "caption_parse_mode": "html",
    "caption_index_enabled": True,
    "caption_index_padding": 2,
    "caption_index_start": 1,

    # Filename styling
    "prefix": "",
    "suffix": "",
    "replace_words": "",

    # Auto rename basic
    "auto_rename": "",
    "auto_rename_enabled": False,

    # Auto rename advanced
    "rename_template": "",
    "rename_parse_mode": "text",
    "filename_prefix": "",
    "filename_suffix": "",
    "filename_index_enabled": False,
    "filename_index_padding": 2,
    "filename_index_start": 1,

    # Metadata
    "metadata_enabled": False,
    "metadata_video_title": "",
    "metadata_video_author": "",
    "metadata_audio_title": "",
    "metadata_subtitle_title": "",

    # Upload
    "upload_destination": "",
    "topic_id": "",

    # Index/session
    "index_mode": False,
    "authorized_mode": False,
    "last_login_user_id": 0,

    # Batch
    "batch_mode": False,
    "batch_last_input": "",
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

    # Rename / index settings
    "set_rename_template": "rename_template",
    "set_filename_prefix": "filename_prefix",
    "set_filename_suffix": "filename_suffix",
    "set_caption_index_padding": "caption_index_padding",
    "set_caption_index_start": "caption_index_start",
    "set_filename_index_padding": "filename_index_padding",
    "set_filename_index_start": "filename_index_start",

    # Login flow states
    "login_phone": "login_phone",
    "login_code": "login_code",
    "login_password": "login_password",

    # Batch flow states
    "set_batch_links": "batch_last_input",
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _to_int(value, default=0):
    try:
        return int(value)
    except Exception:
        return default


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        v = value.strip().lower()
        if v in {"true", "1", "yes", "on"}:
            return True
        if v in {"false", "0", "no", "off"}:
            return False
    try:
        return bool(value)
    except Exception:
        return default


def _normalize_upload_mode(value) -> str:
    value = str(value or "").strip().lower()

    if value in {"document", "doc", "file"}:
        return "document"

    if value in {"media", "telegram", "video", "photo", "audio"}:
        return "media"

    return "media"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(value):
    value = str(value or "").strip()
    if not value:
        return None
    try:
        if value.endswith("Z"):
            value = value[:-1] + "+00:00"
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None


def _normalize_settings(data: dict):
    merged = DEFAULT_SETTINGS.copy()
    if isinstance(data, dict):
        merged.update(data)

    merged["upload_mode"] = _normalize_upload_mode(merged.get("upload_mode", "media"))

    merged["caption_index_padding"] = max(1, _to_int(merged.get("caption_index_padding", 2), 2))
    merged["caption_index_start"] = max(0, _to_int(merged.get("caption_index_start", 1), 1))
    merged["filename_index_padding"] = max(1, _to_int(merged.get("filename_index_padding", 2), 2))
    merged["filename_index_start"] = max(0, _to_int(merged.get("filename_index_start", 1), 1))
    merged["last_login_user_id"] = _to_int(merged.get("last_login_user_id", 0), 0)

    bool_keys = [
        "thumbnail_enabled",
        "caption_enabled",
        "caption_index_enabled",
        "auto_rename_enabled",
        "filename_index_enabled",
        "metadata_enabled",
        "index_mode",
        "authorized_mode",
        "batch_mode",
    ]
    for key in bool_keys:
        merged[key] = _to_bool(merged.get(key, False), False)

    str_keys = [
        "thumbnail_file_id",
        "caption_text",
        "caption_parse_mode",
        "prefix",
        "suffix",
        "replace_words",
        "auto_rename",
        "rename_template",
        "rename_parse_mode",
        "filename_prefix",
        "filename_suffix",
        "metadata_video_title",
        "metadata_video_author",
        "metadata_audio_title",
        "metadata_subtitle_title",
        "upload_destination",
        "topic_id",
        "batch_last_input",
    ]
    for key in str_keys:
        merged[key] = str(merged.get(key, "") or "")

    return merged


# ================= PREMIUM HELPERS =================

def _supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def _supabase_headers():
    return {
        "apikey": SUPABASE_KEY,
        "Authorization": f"Bearer {SUPABASE_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }


def _supabase_request(method: str, path: str, payload=None):
    if not _supabase_enabled():
        raise RuntimeError("Supabase not configured")

    url = f"{SUPABASE_URL}{path}"
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib_request.Request(url=url, data=data, method=method, headers=_supabase_headers())
    try:
        with urllib_request.urlopen(req, timeout=20) as response:
            raw = response.read().decode("utf-8")
            return json.loads(raw) if raw else None
    except urllib_error.HTTPError as e:
        try:
            body = e.read().decode("utf-8")
        except Exception:
            body = ""
        raise RuntimeError(f"Supabase HTTPError {e.code}: {body}")
    except Exception as e:
        raise RuntimeError(f"Supabase request failed: {e}")


def _normalize_premium_record(user_id: int, data=None):
    data = data or {}
    return {
        "user_id": int(user_id),
        "is_premium": bool(data.get("is_premium", False)),
        "plan_name": str(data.get("plan_name", "") or ""),
        "premium_expires_at": str(data.get("premium_expires_at", "") or ""),
        "granted_by": int(data.get("granted_by", 0) or 0),
        "granted_at": str(data.get("granted_at", "") or ""),
        "notes": str(data.get("notes", "") or ""),
        "updated_at": str(data.get("updated_at", "") or ""),
    }


def _compute_expiry_from_duration(duration_text: str):
    duration_text = str(duration_text or "").strip().lower()
    if not duration_text:
        return None

    match = re.fullmatch(r"(\d+)\s*([dhmwy]|day|days|hour|hours|month|months|week|weeks|year|years)", duration_text)
    if not match:
        return None

    value = int(match.group(1))
    unit = match.group(2)

    now = datetime.now(timezone.utc)

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

    return None


def get_all_premium_users():
    if _supabase_enabled():
        try:
            rows = _supabase_request("GET", f"/rest/v1/{SUPABASE_PREMIUM_TABLE}?select=*")
            result = {}
            for row in rows or []:
                uid = str(int(row.get("user_id", 0) or 0))
                if uid != "0":
                    result[uid] = _normalize_premium_record(int(uid), row)
            return result
        except Exception:
            pass

    data = load_json(PREMIUM_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_premium_users(data):
    if _supabase_enabled():
        try:
            payload = []
            for uid, row in (data or {}).items():
                record = _normalize_premium_record(int(uid), row)
                record["updated_at"] = _now_iso()
                payload.append(record)
            _supabase_request("POST", f"/rest/v1/{SUPABASE_PREMIUM_TABLE}?on_conflict=user_id", payload)
            return
        except Exception:
            pass

    save_json(PREMIUM_FILE, data)


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

    if _supabase_enabled():
        try:
            _supabase_request(
                "POST",
                f"/rest/v1/{SUPABASE_PREMIUM_TABLE}?on_conflict=user_id",
                [current],
            )
            return
        except Exception:
            pass

    all_users = get_all_premium_users()
    all_users[str(user_id)] = current
    save_all_premium_users(all_users)


def delete_premium_record(user_id: int):
    if _supabase_enabled():
        try:
            _supabase_request("DELETE", f"/rest/v1/{SUPABASE_PREMIUM_TABLE}?user_id=eq.{int(user_id)}")
            return
        except Exception:
            pass

    all_users = get_all_premium_users()
    all_users.pop(str(user_id), None)
    save_all_premium_users(all_users)


def is_premium_expired(user_id: int) -> bool:
    record = get_premium_record(user_id)
    if not record.get("is_premium"):
        return True

    expiry = _parse_iso(record.get("premium_expires_at", ""))
    if not expiry:
        return False

    return datetime.now(timezone.utc) >= expiry


def is_premium_user(user_id: int) -> bool:
    record = get_premium_record(user_id)
    if not record.get("is_premium"):
        return False

    if is_premium_expired(user_id):
        remove_premium(user_id)
        return False

    return True


def add_premium(user_id: int, duration_text: str = "", granted_by: int = 0, plan_name: str = "Premium", notes: str = ""):
    expires_at = _compute_expiry_from_duration(duration_text) if duration_text else ""
    record = {
        "is_premium": True,
        "plan_name": str(plan_name or "Premium"),
        "premium_expires_at": expires_at,
        "granted_by": int(granted_by or 0),
        "granted_at": _now_iso(),
        "notes": str(notes or ""),
    }
    save_premium_record(user_id, record)
    return get_premium_record(user_id)


def remove_premium(user_id: int):
    save_premium_record(user_id, {
        "is_premium": False,
        "plan_name": "",
        "premium_expires_at": "",
        "notes": "",
    })
    return get_premium_record(user_id)


def get_premium_expiry_text(user_id: int) -> str:
    record = get_premium_record(user_id)
    return str(record.get("premium_expires_at", "") or "")


def get_user_batch_limit(user_id: int) -> int:
    return PREMIUM_MAX_BATCH_LINKS if is_premium_user(user_id) else FREE_MAX_BATCH_LINKS


def get_user_task_limit(user_id: int) -> int:
    return PREMIUM_MAX_TASKS_PER_USER if is_premium_user(user_id) else FREE_MAX_TASKS_PER_USER


def cleanup_expired_premium_users():
    all_users = get_all_premium_users()
    changed = False

    for uid in list(all_users.keys()):
        record = _normalize_premium_record(int(uid), all_users.get(uid, {}))
        if record.get("is_premium"):
            expiry = _parse_iso(record.get("premium_expires_at", ""))
            if expiry and datetime.now(timezone.utc) >= expiry:
                record["is_premium"] = False
                record["plan_name"] = ""
                record["premium_expires_at"] = ""
                record["updated_at"] = _now_iso()
                all_users[uid] = record
                changed = True

    if changed:
        save_all_premium_users(all_users)


# ================= SETTINGS =================

def get_all_settings():
    data = load_json(SETTINGS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_settings(data):
    save_json(SETTINGS_FILE, data)


def get_user_settings(user_id: int):
    all_settings = get_all_settings()
    uid = str(user_id)
    current = all_settings.get(uid, {})

    merged = _normalize_settings(current)

    if uid not in all_settings or merged != current:
        all_settings[uid] = merged
        save_all_settings(all_settings)

    return merged


def update_user_settings(user_id: int, new_data: dict):
    all_settings = get_all_settings()
    uid = str(user_id)

    current = DEFAULT_SETTINGS.copy()
    existing = all_settings.get(uid, {})
    if isinstance(existing, dict):
        current.update(existing)

    if isinstance(new_data, dict):
        current.update(new_data)

    current = _normalize_settings(current)
    all_settings[uid] = current
    save_all_settings(all_settings)


def reset_user_settings(user_id: int):
    all_settings = get_all_settings()
    all_settings[str(user_id)] = _normalize_settings(DEFAULT_SETTINGS.copy())
    save_all_settings(all_settings)


# ================= SETTING STATUS HELPERS =================

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


def get_settings_marks(user_id: int):
    s = get_user_settings(user_id)
    return {
        "upload_mode": "📄" if s.get("upload_mode") == "document" else "🎞",
        "thumbnail": setting_mark(s.get("thumbnail_file_id")),
        "caption": "✅" if s.get("caption_enabled") and s.get("caption_text") else "❌",
        "prefix": setting_mark(s.get("prefix")),
        "suffix": setting_mark(s.get("suffix")),
        "auto_rename": setting_mark(
            s.get("auto_rename")
            or s.get("rename_template")
            or s.get("filename_prefix")
            or s.get("filename_suffix")
        ),
        "metadata": "✅" if s.get("metadata_enabled") else "❌",
        "destination": setting_mark(s.get("upload_destination")),
        "topic_id": setting_mark(s.get("topic_id")),
        "replace_words": setting_mark(s.get("replace_words")),
        "index_mode": "✅" if is_index_mode(user_id) else "❌",
        "login": "✅" if has_user_session(user_id) else "❌",
        "batch_mode": "✅" if s.get("batch_mode") else "❌",
        "premium": "💎" if is_premium_user(user_id) else "🆓",
    }


# ================= USER INPUT STATE =================

def get_all_states():
    data = load_json(STATE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_states(data):
    save_json(STATE_FILE, data)


def get_user_state(user_id: int):
    raw = get_all_states().get(str(user_id), "")
    if isinstance(raw, dict):
        return raw.get("state", "")
    return raw


def set_user_state(user_id: int, state: str):
    states = get_all_states()
    uid = str(user_id)
    current = states.get(uid, {})
    if isinstance(current, dict):
        current["state"] = state
        states[uid] = current
    else:
        states[uid] = {"state": state}
    save_all_states(states)


def clear_user_state(user_id: int):
    states = get_all_states()
    states.pop(str(user_id), None)
    save_all_states(states)


# ================= USERS =================

def get_all_users():
    data = load_json(USERS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_users(data):
    save_json(USERS_FILE, data)


def register_user(user):
    if not user:
        return
    users = get_all_users()
    uid = str(user.id)
    users[uid] = {
        "id": user.id,
        "first_name": getattr(user, "first_name", "") or "",
        "username": getattr(user, "username", "") or "",
        "last_seen": datetime.utcnow().isoformat(),
    }
    save_all_users(users)


def user_count() -> int:
    return len(get_all_users())


def get_recent_users(limit: int = 10):
    users = list(get_all_users().values())
    users.sort(key=lambda x: x.get("last_seen", ""), reverse=True)
    return users[:limit]


# ================= BANNED USERS =================

def get_banned_users():
    data = load_json(BANNED_FILE, [])
    return set(int(x) for x in data if str(x).lstrip("-").isdigit())


def save_banned_users(data):
    save_json(BANNED_FILE, sorted(list(data)))


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


# ================= INDEX ENTRIES =================

def get_all_index_entries():
    data = load_json(INDEX_FILE, [])
    return data if isinstance(data, list) else []


def save_all_index_entries(data):
    save_json(INDEX_FILE, data)


def add_index_entry(entry: dict):
    entries = get_all_index_entries()

    clean_entry = dict(entry) if isinstance(entry, dict) else {}
    clean_entry["index_no"] = len(entries) + 1
    clean_entry["indexed_at"] = datetime.utcnow().isoformat()

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

    user_entries = [x for x in entries if str(x.get("user_id")) == str(user_id)]
    if not user_entries:
        return 0

    return int(user_entries[-1].get("index_no", 0) or 0)


def format_index_number(index_no: int, padding: int = 2) -> str:
    try:
        index_no = int(index_no)
    except Exception:
        index_no = 0

    try:
        padding = max(1, int(padding))
    except Exception:
        padding = 2

    return str(index_no).zfill(padding)


# ================= INDEX MODE / INDEX STATE =================

def get_index_state():
    data = load_json(INDEX_STATE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_index_state(data):
    save_json(INDEX_STATE_FILE, data)


def _default_index_state():
    return {
        "enabled": False,
        "count": 0,
        "user_start_offset": 0,
        "user_current_index": 0,
        "last_reset_at": "",
    }


def set_index_mode(user_id: int, enabled: bool):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, _default_index_state())
    current["enabled"] = bool(enabled)
    state[key] = current
    save_index_state(state)

    update_user_settings(user_id, {"index_mode": bool(enabled)})


def is_index_mode(user_id: int) -> bool:
    state_enabled = bool(get_index_state().get(str(user_id), {}).get("enabled", False))
    settings_enabled = bool(get_user_settings(user_id).get("index_mode", False))
    return state_enabled or settings_enabled


def increase_index_user_count(user_id: int):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, _default_index_state())
    current["count"] = int(current.get("count", 0)) + 1
    current["user_current_index"] = int(current.get("user_current_index", 0)) + 1
    state[key] = current
    save_index_state(state)
    return current["count"]


def get_index_user_count(user_id: int) -> int:
    return int(get_index_state().get(str(user_id), {}).get("count", 0))


def reset_user_index_counter(user_id: int):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, _default_index_state())
    current["user_current_index"] = 0
    current["last_reset_at"] = datetime.utcnow().isoformat()
    state[key] = current
    save_index_state(state)
    return 0


def reset_index_user_count(user_id: int):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, _default_index_state())
    current["count"] = 0
    current["user_current_index"] = 0
    current["last_reset_at"] = datetime.utcnow().isoformat()
    state[key] = current
    save_index_state(state)
    return 0


def get_user_current_index(user_id: int) -> int:
    return int(get_index_state().get(str(user_id), {}).get("user_current_index", 0))


def get_next_user_index(user_id: int) -> int:
    return get_user_current_index(user_id) + 1


# ================= BATCH MODE =================

def set_batch_mode(user_id: int, enabled: bool):
    update_user_settings(user_id, {"batch_mode": bool(enabled)})


def is_batch_mode(user_id: int) -> bool:
    return bool(get_user_settings(user_id).get("batch_mode", False))


def save_batch_input(user_id: int, raw_text: str):
    update_user_settings(user_id, {"batch_last_input": raw_text or ""})


def get_batch_input(user_id: int) -> str:
    return str(get_user_settings(user_id).get("batch_last_input", "") or "")


def clear_batch_input(user_id: int):
    update_user_settings(user_id, {"batch_last_input": ""})


def _normalize_batch_token(token: str) -> str:
    token = (token or "").strip()
    token = token.strip("[](){}<>")
    token = token.rstrip(".,;")
    return token


def _expand_tme_range_link(link: str):
    """
    Supports:
    - https://t.me/username/39-69
    - https://t.me/c/1234567890/39-69
    - single message links remain same
    """
    link = _normalize_batch_token(link)
    if not link.startswith("https://t.me/"):
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
        return [f"{prefix}{msg_id}" for msg_id in range(start, end + 1)]

    if public_range:
        prefix = public_range.group(1)
        start = int(public_range.group(2))
        end = int(public_range.group(3))
        if start > end:
            start, end = end, start
        return [f"{prefix}{msg_id}" for msg_id in range(start, end + 1)]

    if private_single or public_single:
        return [link]

    return []


def parse_batch_links(raw_text: str):
    if not raw_text:
        return []

    parts = []
    for line in raw_text.splitlines():
        line = line.strip()
        if not line:
            continue
        parts.extend(x.strip() for x in line.split() if x.strip())

    links = []
    seen = set()

    for item in parts:
        item = _normalize_batch_token(item)
        expanded = _expand_tme_range_link(item)

        for link in expanded:
            if link not in seen:
                links.append(link)
                seen.add(link)

    return links


# ================= SESSION STORE =================

def get_all_user_sessions():
    data = load_json(SESSION_STORE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_user_sessions(data):
    save_json(SESSION_STORE_FILE, data)


def save_user_session(user_id: int, session_string: str, tg_user_id: int = 0, phone: str = ""):
    sessions = get_all_user_sessions()
    sessions[str(user_id)] = {
        "session_string": session_string,
        "tg_user_id": tg_user_id,
        "phone": phone,
        "saved_at": datetime.utcnow().isoformat(),
    }
    save_all_user_sessions(sessions)

    update_user_settings(user_id, {
        "authorized_mode": True,
        "last_login_user_id": int(tg_user_id or 0),
    })


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

    update_user_settings(user_id, {
        "authorized_mode": False,
        "last_login_user_id": 0,
    })


# ================= LOGIN FLOW TEMP DATA =================

def set_login_temp(user_id: int, key: str, value):
    states = get_all_states()
    uid = str(user_id)
    current = states.get(uid, {})
    if not isinstance(current, dict):
        current = {"state": current} if current else {}
    current[key] = value
    states[uid] = current
    save_all_states(states)


def get_login_temp(user_id: int, key: str, default=None):
    states = get_all_states()
    current = states.get(str(user_id), {})
    if isinstance(current, dict):
        return current.get(key, default)
    return default


# ================= TASK STORE =================

def get_all_tasks():
    data = load_json(TASKS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_tasks(data):
    save_json(TASKS_FILE, data)


def set_task(task_id: str, data: dict):
    tasks = get_all_tasks()
    current = tasks.get(task_id, {})
    if isinstance(current, dict):
        current.update(data or {})
    else:
        current = data or {}

    current["updated_at"] = datetime.utcnow().isoformat()
    tasks[task_id] = current
    save_all_tasks(tasks)


def get_task(task_id: str):
    return get_all_tasks().get(task_id, {})


def delete_task(task_id: str):
    tasks = get_all_tasks()
    tasks.pop(task_id, None)
    save_all_tasks(tasks)


def get_user_tasks(user_id: int, limit: int = 20):
    tasks = list(get_all_tasks().values())
    tasks = [t for t in tasks if str(t.get("user_id")) == str(user_id)]
    tasks.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return tasks[:limit]


def count_running_tasks(user_id: int) -> int:
    tasks = get_user_tasks(user_id, limit=1000)
    count = 0
    for t in tasks:
        if t.get("status") in {"queued", "fetching", "downloading", "uploading", "processing"}:
            count += 1
    return count