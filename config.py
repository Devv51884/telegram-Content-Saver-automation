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
ADMIN_IDS = {
    int(x.strip()) for x in ADMINS_RAW.split(',') if x.strip().isdigit()
}
if OWNER_ID:
    ADMIN_IDS.add(OWNER_ID)

DATA_DIR = os.getenv('DATA_DIR', 'data')
SETTINGS_FILE = os.path.join(DATA_DIR, 'user_settings.json')
STATE_FILE = os.path.join(DATA_DIR, 'user_state.json')
USERS_FILE = os.path.join(DATA_DIR, 'users.json')
BANNED_FILE = os.path.join(DATA_DIR, 'banned_users.json')
SESSION_NAME = os.getenv('SESSION_NAME', 'code_devil_v3_structured')

os.makedirs(DATA_DIR, exist_ok=True)
