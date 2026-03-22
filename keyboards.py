from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import MAIN_CHANNEL, UPDATES_CHANNEL, PLAYLIST_LINK, WHATSAPP_CHANNEL, YOUTUBE_CHANNEL, JOIN_LINK


def join_required_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🔒 Pehle Channel Join Karo', url=JOIN_LINK or MAIN_CHANNEL)],
        [InlineKeyboardButton('✅ Join Kar Liya', callback_data='check_join_again')],
    ])


def start_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📢 Main Channel', url=MAIN_CHANNEL), InlineKeyboardButton('🛠 Updates', url=UPDATES_CHANNEL)],
        [InlineKeyboardButton('📚 Playlist', url=PLAYLIST_LINK), InlineKeyboardButton('▶️ YouTube', url=YOUTUBE_CHANNEL)],
        [InlineKeyboardButton('💬 WhatsApp', url=WHATSAPP_CHANNEL)],
    ])


def settings_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton('📤 Upload Mode', callback_data='toggle_upload_mode'),
            InlineKeyboardButton('🖼 Thumbnail', callback_data='toggle_thumbnail'),
        ],
        [
            InlineKeyboardButton('📝 Caption', callback_data='toggle_caption'),
            InlineKeyboardButton('🏷 Prefix', callback_data='set_prefix'),
        ],
        [
            InlineKeyboardButton('🔖 Suffix', callback_data='set_suffix'),
            InlineKeyboardButton('✍️ Auto Rename', callback_data='set_auto_rename'),
        ],
        [
            InlineKeyboardButton('📦 Metadata', callback_data='toggle_metadata'),
            InlineKeyboardButton('📍 Destination', callback_data='set_destination'),
        ],
        [
            InlineKeyboardButton('🧵 Topic ID', callback_data='set_topic_id'),
            InlineKeyboardButton('🔁 Replace Words', callback_data='set_replace_words'),
        ],
        [InlineKeyboardButton('♻️ Reset All', callback_data='reset_all_settings')],
    ])
