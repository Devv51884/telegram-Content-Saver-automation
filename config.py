import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
ENV_FILE = BASE_DIR / ".env"

load_dotenv(ENV_FILE if ENV_FILE.exists() else None)


# =========================================================
# ENV HELPERS
# =========================================================
def _get_str(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


def _resolve_path(value: str, default: str = "") -> str:
    value = str(value or default or "").strip()
    if not value:
        return ""
    path = Path(value)
    if not path.is_absolute():
        path = BASE_DIR / path
    return str(path.resolve())


def _get_int(name: str, default: int = 0) -> int:
    value = _get_str(name, str(default))
    try:
        return int(value)
    except Exception:
        return default


def _get_float(name: str, default: float = 0.0) -> float:
    value = _get_str(name, str(default))
    try:
        return float(value)
    except Exception:
        return default


def _get_bool(name: str, default: bool = False) -> bool:
    value = _get_str(name, str(default)).lower()
    if value in {"true", "1", "yes", "on"}:
        return True
    if value in {"false", "0", "no", "off"}:
        return False
    return default


def _get_csv_int_set(name: str) -> set[int]:
    raw = _get_str(name, "")
    return {
        int(x.strip())
        for x in raw.split(",")
        if x.strip() and x.strip().lstrip("-").isdigit()
    }


def _parse_chat_target(value: str):
    value = str(value or "").strip()
    if not value:
        return 0
    if value.lstrip("-").isdigit():
        return int(value)
    return value


def _normalize_upload_mode(value: str, default: str = "media") -> str:
    value = str(value or default).strip().lower()
    if value in {"document", "doc", "file"}:
        return "document"
    if value in {"media", "video", "photo", "audio"}:
        return "media"
    default = str(default or "media").strip().lower()
    return "document" if default == "document" else "media"


def _sanitize_database_mode(value: str, default: str = "hybrid") -> str:
    value = str(value or default).strip().lower()
    if value in {"hybrid", "supabase", "local"}:
        return value
    return default


# =========================================================
# APP / BRANDING
# =========================================================
APP_NAME = _get_str("APP_NAME", "Code Devil Restricted Saver")
APP_VERSION = _get_str("APP_VERSION", "v12")
APP_ENV = _get_str("APP_ENV", "production")
DEBUG = _get_bool("DEBUG", False)
TZ = _get_str("TZ", "Asia/Kolkata")

MAIN_CHANNEL = _get_str("MAIN_CHANNEL", "https://t.me/Code_Devil")
UPDATES_CHANNEL = _get_str("UPDATES_CHANNEL", "https://t.me/Devil_Developee")
PLAYLIST_LINK = _get_str("PLAYLIST_LINK", "https://t.me/addlist/wTBxgyESacMwMDA1")
WHATSAPP_CHANNEL = _get_str("WHATSAPP_CHANNEL", "https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U")
YOUTUBE_CHANNEL = _get_str("YOUTUBE_CHANNEL", "https://www.youtube.com/@Code_Devil")
SUPPORT_CONTACT = _get_str("SUPPORT_CONTACT", MAIN_CHANNEL)


# =========================================================
# TELEGRAM API / BOT
# =========================================================
API_ID = _get_int("API_ID", 0)
API_HASH = _get_str("API_HASH", "")
BOT_TOKEN = _get_str("BOT_TOKEN", "")
STRING_SESSION = _get_str("STRING_SESSION", "")
SESSION_NAME = _get_str("SESSION_NAME", "code_devil_v12_bot")
SESSION_STORE_FILE = _resolve_path(_get_str("SESSION_STORE_FILE", "data/user_sessions.json"))


# =========================================================
# CHANNELS / FORCE SUB
# =========================================================
FORCE_SUB = _get_str("FORCE_SUB", "")
JOIN_LINK = _get_str("JOIN_LINK", "")
FORCE_SUB_STRICT = _get_bool("FORCE_SUB_STRICT", True)

LOG_CHANNEL = _parse_chat_target(_get_str("LOG_CHANNEL", ""))
DEFAULT_DESTINATION = _parse_chat_target(_get_str("DEFAULT_DESTINATION", ""))
OWNER_ID = _get_int("OWNER_ID", 0)
ADMIN_IDS = _get_csv_int_set("ADMIN_IDS")
if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)


# =========================================================
# PATHS / STORAGE
# =========================================================
DATA_DIR = _resolve_path(_get_str("DATA_DIR", "data"))
TEMP_DIR = _resolve_path(_get_str("TEMP_DIR", "temp"))
CACHE_DIR = _resolve_path(_get_str("CACHE_DIR", os.path.join(DATA_DIR, "cache")))
BACKUP_DIR = _resolve_path(_get_str("BACKUP_DIR", os.path.join(DATA_DIR, "backups")))
EXPORT_DIR = _resolve_path(_get_str("EXPORT_DIR", os.path.join(DATA_DIR, "exports")))

SETTINGS_FILE = _resolve_path(_get_str("SETTINGS_FILE", os.path.join(DATA_DIR, "user_settings.json")))
STATE_FILE = _resolve_path(_get_str("STATE_FILE", os.path.join(DATA_DIR, "user_state.json")))
USERS_FILE = _resolve_path(_get_str("USERS_FILE", os.path.join(DATA_DIR, "users.json")))
BANNED_FILE = _resolve_path(_get_str("BANNED_FILE", os.path.join(DATA_DIR, "banned_users.json")))
INDEX_FILE = _resolve_path(_get_str("INDEX_FILE", os.path.join(DATA_DIR, "index_store.json")))
INDEX_STATE_FILE = _resolve_path(_get_str("INDEX_STATE_FILE", os.path.join(DATA_DIR, "index_state.json")))
TASKS_FILE = _resolve_path(_get_str("TASKS_FILE", os.path.join(DATA_DIR, "tasks.json")))
PREMIUM_FILE = _resolve_path(_get_str("PREMIUM_FILE", os.path.join(DATA_DIR, "premium_users.json")))
STATS_FILE = _resolve_path(_get_str("STATS_FILE", os.path.join(DATA_DIR, "stats.json")))
BROADCAST_LOG_FILE = _resolve_path(_get_str("BROADCAST_LOG_FILE", os.path.join(DATA_DIR, "broadcast_log.json")))
FAILED_TASKS_FILE = _resolve_path(_get_str("FAILED_TASKS_FILE", os.path.join(DATA_DIR, "failed_tasks.json")))
DESTINATIONS_FILE = _resolve_path(_get_str("DESTINATIONS_FILE", os.path.join(DATA_DIR, "destinations.json")))
AUDIT_LOG_FILE = _resolve_path(_get_str("AUDIT_LOG_FILE", os.path.join(DATA_DIR, "task_audit_log.json")))
USER_LIMITS_FILE = _resolve_path(_get_str("USER_LIMITS_FILE", os.path.join(DATA_DIR, "user_limits.json")))
GDRIVE_TOKENS_DIR = _resolve_path(_get_str("GDRIVE_TOKENS_DIR", os.path.join(DATA_DIR, "gdrive_tokens")))
RCLONE_CONFIGS_DIR = _resolve_path(_get_str("RCLONE_CONFIGS_DIR", os.path.join(DATA_DIR, "rclone_configs")))
GDRIVE_CREDENTIALS_FILE = _resolve_path(_get_str("GDRIVE_CREDENTIALS_FILE", os.path.join(DATA_DIR, "credentials.json")))
RCLONE_BIN = _get_str("RCLONE_BIN", "rclone")


# =========================================================
# DATABASE - SUPABASE + OFFLINE HYBRID
# =========================================================
DATABASE_MODE = _sanitize_database_mode(_get_str("DATABASE_MODE", "hybrid"))
ENABLE_LOCAL_FALLBACK = _get_bool("ENABLE_LOCAL_FALLBACK", True)
SYNC_LOCAL_TO_SUPABASE = _get_bool("SYNC_LOCAL_TO_SUPABASE", True)
SUPABASE_URL = _get_str("SUPABASE_URL", "")
SUPABASE_KEY = _get_str("SUPABASE_KEY", "")
SUPABASE_TIMEOUT = max(3.0, _get_float("SUPABASE_TIMEOUT", 15.0))
SUPABASE_SCHEMA = _get_str("SUPABASE_SCHEMA", "public")

SUPABASE_USERS_TABLE = _get_str("SUPABASE_USERS_TABLE", "users")
SUPABASE_SETTINGS_TABLE = _get_str("SUPABASE_SETTINGS_TABLE", "user_settings")
SUPABASE_STATE_TABLE = _get_str("SUPABASE_STATE_TABLE", "user_state")
SUPABASE_PREMIUM_TABLE = _get_str("SUPABASE_PREMIUM_TABLE", "premium_users")
SUPABASE_TASKS_TABLE = _get_str("SUPABASE_TASKS_TABLE", "tasks")
SUPABASE_STATS_TABLE = _get_str("SUPABASE_STATS_TABLE", "bot_stats")
SUPABASE_BROADCAST_TABLE = _get_str("SUPABASE_BROADCAST_TABLE", "broadcast_logs")
SUPABASE_DESTINATIONS_TABLE = _get_str("SUPABASE_DESTINATIONS_TABLE", "user_destinations")
SUPABASE_AUDIT_TABLE = _get_str("SUPABASE_AUDIT_TABLE", "task_audit_logs")


# =========================================================
# USER PLANS / PREMIUM SYSTEM
# =========================================================
DEFAULT_PLAN_NAME = _get_str("DEFAULT_PLAN_NAME", "Free")
DEFAULT_PREMIUM_PLAN_NAME = _get_str("DEFAULT_PREMIUM_PLAN_NAME", "Premium")
PREMIUM_GRACE_HOURS = max(0, _get_int("PREMIUM_GRACE_HOURS", 0))
PREMIUM_EXPIRY_CHECK_INTERVAL = max(60, _get_int("PREMIUM_EXPIRY_CHECK_INTERVAL", 300))
ENABLE_PREMIUM_EXPIRY_ALERTS = _get_bool("ENABLE_PREMIUM_EXPIRY_ALERTS", True)
PREMIUM_EXPIRY_ALERT_HOURS = max(1, _get_int("PREMIUM_EXPIRY_ALERT_HOURS", 24))

FREE_MAX_TASKS_PER_USER = max(1, _get_int("FREE_MAX_TASKS_PER_USER", 3))
PREMIUM_MAX_TASKS_PER_USER = max(FREE_MAX_TASKS_PER_USER, _get_int("PREMIUM_MAX_TASKS_PER_USER", 10))

FREE_MAX_BATCH_LINKS = max(1, _get_int("FREE_MAX_BATCH_LINKS", 50))
PREMIUM_MAX_BATCH_LINKS = max(FREE_MAX_BATCH_LINKS, _get_int("PREMIUM_MAX_BATCH_LINKS", 300))

FREE_MAX_FILE_SIZE_MB = max(1, _get_int("FREE_MAX_FILE_SIZE_MB", 2000))
PREMIUM_MAX_FILE_SIZE_MB = max(FREE_MAX_FILE_SIZE_MB, _get_int("PREMIUM_MAX_FILE_SIZE_MB", 4000))

# Backward-compatible generic values
MAX_TASKS_PER_USER = max(1, _get_int("MAX_TASKS_PER_USER", FREE_MAX_TASKS_PER_USER))
MAX_BATCH_LINKS = max(1, _get_int("MAX_BATCH_LINKS", FREE_MAX_BATCH_LINKS))
MAX_FILE_SIZE_MB = max(1, _get_int("MAX_FILE_SIZE_MB", FREE_MAX_FILE_SIZE_MB))


# =========================================================
# TASK / QUEUE CONTROL
# =========================================================
MAX_CONCURRENT_DOWNLOADS = max(1, _get_int("MAX_CONCURRENT_DOWNLOADS", 3))
MAX_CONCURRENT_UPLOADS = max(1, _get_int("MAX_CONCURRENT_UPLOADS", 3))
GLOBAL_MAX_RUNNING_TASKS = max(1, _get_int("GLOBAL_MAX_RUNNING_TASKS", 20))
TASK_CLEANUP_AFTER_HOURS = max(1, _get_int("TASK_CLEANUP_AFTER_HOURS", 24))
TASK_STATUS_TTL_MINUTES = max(5, _get_int("TASK_STATUS_TTL_MINUTES", 180))
QUEUE_POLL_INTERVAL = max(0.2, _get_float("QUEUE_POLL_INTERVAL", 0.2))
ENABLE_TASK_DEBUG = _get_bool("ENABLE_TASK_DEBUG", False)
STORE_TASK_AUDIT_LOG = _get_bool("STORE_TASK_AUDIT_LOG", True)
TASK_DEBUG_MAX_ENTRIES = max(10, _get_int("TASK_DEBUG_MAX_ENTRIES", 200))
ENABLE_TASK_SCHEMA_NORMALIZATION = _get_bool("ENABLE_TASK_SCHEMA_NORMALIZATION", True)
TASK_CARD_HIDE_DELAY = max(0, _get_int("TASK_CARD_HIDE_DELAY", 8))


# =========================================================
# BATCH SYSTEM
# =========================================================
BATCH_DELAY = max(0.0, _get_float("BATCH_DELAY", 0.0))
BATCH_STATUS_UPDATE_EVERY = max(1, _get_int("BATCH_STATUS_UPDATE_EVERY", 1))
ALLOW_BATCH_RANGE_LINKS = _get_bool("ALLOW_BATCH_RANGE_LINKS", True)
SKIP_INVALID_BATCH_LINKS = _get_bool("SKIP_INVALID_BATCH_LINKS", True)
BATCH_STOP_ON_FATAL_ERROR = _get_bool("BATCH_STOP_ON_FATAL_ERROR", False)
BATCH_SUMMARY_SHOW_FAILED = _get_bool("BATCH_SUMMARY_SHOW_FAILED", True)
BATCH_SUMMARY_SHOW_SKIPPED = _get_bool("BATCH_SUMMARY_SHOW_SKIPPED", True)


# =========================================================
# DIRECT SAVE / FAST COPY
# =========================================================
ENABLE_DIRECT_PUBLIC_COPY = _get_bool("ENABLE_DIRECT_PUBLIC_COPY", True)
ENABLE_DIRECT_PRIVATE_COPY = _get_bool("ENABLE_DIRECT_PRIVATE_COPY", True)
ENABLE_LOG_CHANNEL_DIRECT_COPY = _get_bool("ENABLE_LOG_CHANNEL_DIRECT_COPY", True)
ENABLE_LOG_FROM_DESTINATION = _get_bool("ENABLE_LOG_FROM_DESTINATION", True)
PREFER_COPY_OVER_DOWNLOAD = _get_bool("PREFER_COPY_OVER_DOWNLOAD", True)
ALLOW_FORWARD_AS_FALLBACK = _get_bool("ALLOW_FORWARD_AS_FALLBACK", True)
ENABLE_DESTINATION_PRECHECK = _get_bool("ENABLE_DESTINATION_PRECHECK", True)


# =========================================================
# RETRY / RESILIENCE
# =========================================================
AUTO_RETRY_FAILED_TASKS = _get_bool("AUTO_RETRY_FAILED_TASKS", True)
MAX_RETRY_ATTEMPTS = max(0, _get_int("MAX_RETRY_ATTEMPTS", 2))
RETRY_DELAY_SECONDS = max(0.0, _get_float("RETRY_DELAY_SECONDS", 2.0))
RETRY_ON_FLOODWAIT = _get_bool("RETRY_ON_FLOODWAIT", True)
RETRY_ON_TIMEOUT = _get_bool("RETRY_ON_TIMEOUT", True)
RETRY_ON_NETWORK_ERROR = _get_bool("RETRY_ON_NETWORK_ERROR", True)


# =========================================================
# PROGRESS UI
# =========================================================
SHOW_PROGRESS_BAR = _get_bool("SHOW_PROGRESS_BAR", True)
SHOW_REALTIME_SPEED = _get_bool("SHOW_REALTIME_SPEED", True)
SHOW_REALTIME_ETA = _get_bool("SHOW_REALTIME_ETA", True)
SHOW_TRANSFERRED_SIZE = _get_bool("SHOW_TRANSFERRED_SIZE", True)
PROGRESS_BAR_LENGTH = max(5, _get_int("PROGRESS_BAR_LENGTH", 10))
PROGRESS_UPDATE_INTERVAL = max(0.5, _get_float("PROGRESS_UPDATE_INTERVAL", 0.8))
EDIT_PROGRESS_MESSAGE = _get_bool("EDIT_PROGRESS_MESSAGE", True)
SHOW_PROGRESS_STAGE = _get_bool("SHOW_PROGRESS_STAGE", True)
SHOW_TOPIC_IN_TASK_CARD = _get_bool("SHOW_TOPIC_IN_TASK_CARD", True)
SHOW_MODE_IN_TASK_CARD = _get_bool("SHOW_MODE_IN_TASK_CARD", True)
SHOW_UPDATED_AT_IN_TASK_CARD = _get_bool("SHOW_UPDATED_AT_IN_TASK_CARD", True)


# =========================================================
# USER EXPERIENCE / UI
# =========================================================
DEFAULT_UPLOAD_MODE = _normalize_upload_mode(_get_str("DEFAULT_UPLOAD_MODE", "media"))
SHOW_PLAN_IN_START = _get_bool("SHOW_PLAN_IN_START", True)
SHOW_LIMITS_IN_SETTINGS = _get_bool("SHOW_LIMITS_IN_SETTINGS", True)
ENABLE_DYNAMIC_UPLOAD_MODE = _get_bool("ENABLE_DYNAMIC_UPLOAD_MODE", True)
ENABLE_SMART_CAPTIONS = _get_bool("ENABLE_SMART_CAPTIONS", True)
ENABLE_DESTINATION_DISPLAY = _get_bool("ENABLE_DESTINATION_DISPLAY", True)
ENABLE_TOPIC_SUPPORT = _get_bool("ENABLE_TOPIC_SUPPORT", True)
ENABLE_TASK_DETAILS_BUTTON = _get_bool("ENABLE_TASK_DETAILS_BUTTON", True)
ENABLE_CLEAR_FINISHED_TASKS = _get_bool("ENABLE_CLEAR_FINISHED_TASKS", True)


# =========================================================
# BROADCAST / ADMIN TOOLS
# =========================================================
ENABLE_BROADCAST = _get_bool("ENABLE_BROADCAST", True)
BROADCAST_RATE_LIMIT = max(0.0, _get_float("BROADCAST_RATE_LIMIT", 0.08))
BROADCAST_CHUNK_SIZE = max(1, _get_int("BROADCAST_CHUNK_SIZE", 25))
STORE_BROADCAST_HISTORY = _get_bool("STORE_BROADCAST_HISTORY", True)
ENABLE_ADMIN_STATS = _get_bool("ENABLE_ADMIN_STATS", True)
ENABLE_RECENT_USERS_PANEL = _get_bool("ENABLE_RECENT_USERS_PANEL", True)
ENABLE_TASK_DEBUG_PANEL = _get_bool("ENABLE_TASK_DEBUG_PANEL", True)
ENABLE_DESTINATIONS_PANEL = _get_bool("ENABLE_DESTINATIONS_PANEL", True)


# =========================================================
# STORAGE PLANS / ROUTING
# =========================================================
FREE_STORAGE_MODES = [item.strip().lower() for item in _get_str("FREE_STORAGE_MODES", "telegram").split(",") if item.strip()] or ["telegram"]
PREMIUM_STORAGE_MODES = [item.strip().lower() for item in _get_str("PREMIUM_STORAGE_MODES", "telegram,gdrive,rclone").split(",") if item.strip()] or ["telegram", "gdrive", "rclone"]
PRO_STORAGE_MODES = [item.strip().lower() for item in _get_str("PRO_STORAGE_MODES", "telegram,gdrive,rclone,personal_bot").split(",") if item.strip()] or ["telegram", "gdrive", "rclone", "personal_bot"]
DEFAULT_STORAGE_MODE = _get_str("DEFAULT_STORAGE_MODE", "telegram").strip().lower() or "telegram"

# =========================================================
# WEB / HEALTH / DEPLOYMENT
# =========================================================
WEB_HOST = _get_str("WEB_HOST", "0.0.0.0")
WEB_PORT = _get_int("WEB_PORT", 8080)
HEALTH_TOKEN = _get_str("HEALTH_TOKEN", "")
RENDER_EXTERNAL_URL = _get_str("RENDER_EXTERNAL_URL", "")
KEEP_ALIVE_PING = _get_bool("KEEP_ALIVE_PING", False)
KEEP_ALIVE_INTERVAL = max(60, _get_int("KEEP_ALIVE_INTERVAL", 240))
WEB_THREAD_ENABLED = _get_bool("WEB_THREAD_ENABLED", True)


# =========================================================
# VALIDATION / STARTUP HELPERS
# =========================================================
REQUIRED_ENV_VARS = {
    "API_ID": API_ID,
    "API_HASH": API_HASH,
    "BOT_TOKEN": BOT_TOKEN,
    "OWNER_ID": OWNER_ID,
}


def missing_required_config() -> list[str]:
    missing = []
    for key, value in REQUIRED_ENV_VARS.items():
        if value in (None, "", 0):
            missing.append(key)
    return missing


def is_supabase_enabled() -> bool:
    return bool(SUPABASE_URL and SUPABASE_KEY)


def is_hybrid_mode() -> bool:
    return DATABASE_MODE == "hybrid"


def is_local_mode() -> bool:
    return DATABASE_MODE == "local"


def is_supabase_mode() -> bool:
    return DATABASE_MODE == "supabase"


def get_plan_task_limit(is_premium: bool = False) -> int:
    return PREMIUM_MAX_TASKS_PER_USER if is_premium else FREE_MAX_TASKS_PER_USER


def get_plan_batch_limit(is_premium: bool = False) -> int:
    return PREMIUM_MAX_BATCH_LINKS if is_premium else FREE_MAX_BATCH_LINKS


def get_plan_file_size_limit_mb(is_premium: bool = False) -> int:
    return PREMIUM_MAX_FILE_SIZE_MB if is_premium else FREE_MAX_FILE_SIZE_MB


# =========================================================
# CREATE REQUIRED FOLDERS
# =========================================================
for path in {DATA_DIR, TEMP_DIR, CACHE_DIR, BACKUP_DIR, EXPORT_DIR, GDRIVE_TOKENS_DIR, RCLONE_CONFIGS_DIR}:
    os.makedirs(path, exist_ok=True)
