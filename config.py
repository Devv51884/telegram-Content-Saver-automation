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

DATA_DIR = os.getenv('DATA_DIR', 'data')
SETTINGS_FILE = os.path.join(DATA_DIR, 'user_settings.json')
STATE_FILE = os.path.join(DATA_DIR, 'user_state.json')
SESSION_NAME = os.getenv('SESSION_NAME', 'code_devil_v2_structured')

os.makedirs(DATA_DIR, exist_ok=True)
