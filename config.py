import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv('API_ID', '0'))
API_HASH = os.getenv('API_HASH', '')
BOT_TOKEN = os.getenv('BOT_TOKEN', '')

FORCE_SUB = os.getenv('FORCE_SUB', '').strip()
JOIN_LINK = os.getenv('JOIN_LINK', '').strip()

APP_NAME = os.getenv('APP_NAME', 'Code Devil Restricted Saver')
MAIN_CHANNEL = os.getenv('MAIN_CHANNEL', 'https://t.me/Code_Devil')
UPDATES_CHANNEL = os.getenv('UPDATES_CHANNEL', 'https://t.me/Devil_Developee')
PLAYLIST_LINK = os.getenv('PLAYLIST_LINK', 'https://t.me/addlist/wTBxgyESacMwMDA1')
WHATSAPP_CHANNEL = os.getenv('WHATSAPP_CHANNEL', 'https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U')
YOUTUBE_CHANNEL = os.getenv('YOUTUBE_CHANNEL', 'https://www.youtube.com/@Code_Devil')

OWNER_ID = int(os.getenv('OWNER_ID', '0'))

ADMINS_RAW = os.getenv('ADMIN_IDS', '').strip()
ADMIN_IDS = {int(x.strip()) for x in ADMINS_RAW.split(',') if x.strip().isdigit()}
if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)

# Logs channel
LOG_CHANNEL_RAW = os.getenv('LOG_CHANNEL', '').strip()
LOG_CHANNEL = int(LOG_CHANNEL_RAW) if LOG_CHANNEL_RAW.lstrip('-').isdigit() else 0

# Optional fallback destination
DEFAULT_DESTINATION_RAW = os.getenv('DEFAULT_DESTINATION', '').strip()
DEFAULT_DESTINATION = (
    int(DEFAULT_DESTINATION_RAW)
    if DEFAULT_DESTINATION_RAW.lstrip('-').isdigit()
    else 0
)

# =========================
# V6 LOGIN / USER SESSION
# =========================
# Single-owner authorized session string
STRING_SESSION = os.getenv('STRING_SESSION', '').strip()

# Optional per-user sessions file
SESSION_STORE_FILE = os.getenv('SESSION_STORE_FILE', 'data/user_sessions.json')

# =========================
# V6 TASK / TEMP SETTINGS
# =========================
TEMP_DIR = os.getenv('TEMP_DIR', 'temp')
MAX_TASKS_PER_USER = int(os.getenv('MAX_TASKS_PER_USER', '3'))
MAX_CONCURRENT_DOWNLOADS = int(os.getenv('MAX_CONCURRENT_DOWNLOADS', '2'))
TASKS_FILE = os.getenv('TASKS_FILE', 'data/tasks.json')

# Base data directory
DATA_DIR = os.getenv('DATA_DIR', 'data')

SETTINGS_FILE = os.path.join(DATA_DIR, 'user_settings.json')
STATE_FILE = os.path.join(DATA_DIR, 'user_state.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
BANNED_FILE = os.path.join(DATA_DIR, 'banned_users.json')
INDEX_FILE = os.path.join(DATA_DIR, 'index_store.json')
INDEX_STATE_FILE = os.path.join(DATA_DIR, 'index_state.json')

SESSION_NAME = os.getenv('SESSION_NAME', 'code_devil_v6_structured')

# Ensure folders exist
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(TEMP_DIR, exist_ok=True)