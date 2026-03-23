import os
from dotenv import load_dotenv

load_dotenv()


def _get_str(name: str, default: str = "") -> str:
    return str(os.getenv(name, default) or "").strip()


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


def _parse_chat_target(value: str):
    value = str(value or "").strip()
    if not value:
        return 0
    if value.lstrip("-").isdigit():
        return int(value)
    return value


# =========================
# BASIC CONFIG
# =========================
API_ID = _get_int("API_ID", 0)
API_HASH = _get_str("API_HASH", "")
BOT_TOKEN = _get_str("BOT_TOKEN", "")

FORCE_SUB = _get_str("FORCE_SUB", "")
JOIN_LINK = _get_str("JOIN_LINK", "")

APP_NAME = _get_str("APP_NAME", "Code Devil Restricted Saver")
MAIN_CHANNEL = _get_str("MAIN_CHANNEL", "https://t.me/Code_Devil")
UPDATES_CHANNEL = _get_str("UPDATES_CHANNEL", "https://t.me/Devil_Developee")
PLAYLIST_LINK = _get_str("PLAYLIST_LINK", "https://t.me/addlist/wTBxgyESacMwMDA1")
WHATSAPP_CHANNEL = _get_str("WHATSAPP_CHANNEL", "https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U")
YOUTUBE_CHANNEL = _get_str("YOUTUBE_CHANNEL", "https://www.youtube.com/@Code_Devil")

OWNER_ID = _get_int("OWNER_ID", 0)

ADMINS_RAW = _get_str("ADMIN_IDS", "")
ADMIN_IDS = {int(x.strip()) for x in ADMINS_RAW.split(",") if x.strip().isdigit()}
if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)

# =========================
# LOG CHANNEL
# =========================
LOG_CHANNEL = _parse_chat_target(_get_str("LOG_CHANNEL", ""))

# =========================
# DEFAULT DESTINATION
# =========================
DEFAULT_DESTINATION = _parse_chat_target(_get_str("DEFAULT_DESTINATION", ""))

# =========================
# LOGIN / USER SESSION
# =========================
STRING_SESSION = _get_str("STRING_SESSION", "")
SESSION_STORE_FILE = _get_str("SESSION_STORE_FILE", "data/user_sessions.json")

# =========================
# TASK / TEMP SETTINGS
# =========================
TEMP_DIR = _get_str("TEMP_DIR", "temp")
MAX_TASKS_PER_USER = max(1, _get_int("MAX_TASKS_PER_USER", 3))
MAX_CONCURRENT_DOWNLOADS = max(1, _get_int("MAX_CONCURRENT_DOWNLOADS", 2))
TASKS_FILE = _get_str("TASKS_FILE", "data/tasks.json")

# =========================
# BATCH SETTINGS (V8 🔥)
# =========================
MAX_BATCH_LINKS = max(1, _get_int("MAX_BATCH_LINKS", 50))
BATCH_DELAY = max(0.0, _get_float("BATCH_DELAY", 0.5))

# =========================
# DOWNLOAD CONTROL
# =========================
MAX_FILE_SIZE_MB = max(1, _get_int("MAX_FILE_SIZE_MB", 2000))

# =========================
# FORCE SUB STRICT MODE
# =========================
FORCE_SUB_STRICT = _get_bool("FORCE_SUB_STRICT", True)

# =========================
# BASE DATA
# =========================
DATA_DIR = _get_str("DATA_DIR", "data")

SETTINGS_FILE = os.path.join(DATA_DIR, "user_settings.json")
STATE_FILE = os.path.join(DATA_DIR, "user_state.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")
BANNED_FILE = os.path.join(DATA_DIR, "banned_users.json")
INDEX_FILE = os.path.join(DATA_DIR, "index_store.json")
INDEX_STATE_FILE = os.path.join(DATA_DIR, "index_state.json")

SESSION_NAME = _get_str("SESSION_NAME", "code_devil_v8_structured")

# =========================
# CREATE REQUIRED FOLDERS
# =========================
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)
WEB_HOST = _get_str("WEB_HOST", "0.0.0.0")
WEB_PORT = _get_int("WEB_PORT", 8080)
HEALTH_TOKEN = _get_str("HEALTH_TOKEN", "")