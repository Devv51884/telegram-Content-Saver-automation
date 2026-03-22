import os
from dotenv import load_dotenv

load_dotenv()

def required(name: str) -> str:
    value = os.getenv(name, "").strip()
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value

API_ID = int(required("API_ID"))
API_HASH = required("API_HASH")
BOT_TOKEN = required("BOT_TOKEN")
OWNER_ID = int(required("OWNER_ID"))
FORCE_SUB = os.getenv("FORCE_SUB", "").strip()
JOIN_LINK = os.getenv("JOIN_LINK", "https://t.me/Code_Devil").strip()
ADMIN_CONTACT = os.getenv("ADMIN_CONTACT", "https://t.me/Code_Devil24").strip()
COMMUNITY_CHANNEL_1 = os.getenv("COMMUNITY_CHANNEL_1", "https://t.me/Code_Devil").strip()
COMMUNITY_CHANNEL_2 = os.getenv("COMMUNITY_CHANNEL_2", "https://t.me/Devil_Developee").strip()
COMMUNITY_PLAYLIST = os.getenv("COMMUNITY_PLAYLIST", "https://t.me/addlist/wTBxgyESacMwMDA1").strip()
WHATSAPP_CHANNEL = os.getenv("WHATSAPP_CHANNEL", "https://whatsapp.com/channel/0029VaacxeOKWEKsD2KdqR0U").strip()
YOUTUBE_CHANNEL = os.getenv("YOUTUBE_CHANNEL", "https://www.youtube.com/@Code_Devil").strip()
APP_NAME = os.getenv("APP_NAME", "Code Devil Restricted Saver V1.1").strip()
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0").strip()
WEB_PORT = int(os.getenv("PORT", "10000"))
HEALTH_TOKEN = os.getenv("HEALTH_TOKEN", "").strip()
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper().strip()
