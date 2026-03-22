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


def settings_home_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📤 Upload Mode', callback_data='show_upload_mode')],
        [InlineKeyboardButton('🖼 Thumbnail', callback_data='show_thumbnail'), InlineKeyboardButton('📝 Caption', callback_data='show_caption')],
        [InlineKeyboardButton('🏷 Prefix', callback_data='show_prefix'), InlineKeyboardButton('🔖 Suffix', callback_data='show_suffix')],
        [InlineKeyboardButton('✍️ Auto Rename', callback_data='show_auto_rename'), InlineKeyboardButton('📦 Metadata', callback_data='show_metadata')],
        [InlineKeyboardButton('📍 Destination', callback_data='show_destination'), InlineKeyboardButton('🧵 Topic ID', callback_data='show_topic_id')],
        [InlineKeyboardButton('🔁 Replace Words', callback_data='show_replace_words')],
        [InlineKeyboardButton('♻️ Reset All', callback_data='reset_all_settings')],
    ])


def submenu_nav(back='show_settings_home'):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('⬅️ Back', callback_data=back), InlineKeyboardButton('❌ Close', callback_data='close_settings')],
    ])


def thumbnail_buttons(enabled: bool):
    label = '✅ Thumbnail On' if enabled else '❌ Thumbnail Off'
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data='toggle_thumbnail_enabled')],
        [InlineKeyboardButton('📷 Set Thumbnail', callback_data='set_thumbnail_photo')],
        [InlineKeyboardButton('🗑 Remove Thumbnail', callback_data='remove_thumbnail')],
        [InlineKeyboardButton('⬅️ Back', callback_data='show_settings_home'), InlineKeyboardButton('❌ Close', callback_data='close_settings')],
    ])


def caption_buttons(enabled: bool):
    label = '✅ Caption On' if enabled else '❌ Caption Off'
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data='toggle_caption_enabled')],
        [InlineKeyboardButton('✍️ Set Caption', callback_data='set_caption_text')],
        [InlineKeyboardButton('🗑 Remove Caption', callback_data='remove_caption')],
        [InlineKeyboardButton('⬅️ Back', callback_data='show_settings_home'), InlineKeyboardButton('❌ Close', callback_data='close_settings')],
    ])


def simple_set_buttons(set_cb: str, remove_cb: str = '', back='show_settings_home'):
    row1 = [InlineKeyboardButton('✍️ Set Value', callback_data=set_cb)]
    rows = [row1]
    if remove_cb:
        rows.append([InlineKeyboardButton('🗑 Remove', callback_data=remove_cb)])
    rows.append([InlineKeyboardButton('⬅️ Back', callback_data=back), InlineKeyboardButton('❌ Close', callback_data='close_settings')])
    return InlineKeyboardMarkup(rows)


def metadata_buttons(enabled: bool):
    label = '✅ Metadata On' if enabled else '❌ Metadata Off'
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data='toggle_metadata_enabled')],
        [InlineKeyboardButton('🎬 Video Title', callback_data='show_metadata_video_title'),
         InlineKeyboardButton('👤 Video Author', callback_data='show_metadata_video_author')],
        [InlineKeyboardButton('🎵 Audio Title', callback_data='show_metadata_audio_title'),
         InlineKeyboardButton('💬 Subtitle Title', callback_data='show_metadata_subtitle_title')],
        [InlineKeyboardButton('⬅️ Back', callback_data='show_settings_home'), InlineKeyboardButton('❌ Close', callback_data='close_settings')],
    ])


def metadata_field_buttons(set_cb: str, remove_cb: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('✍️ Set Value', callback_data=set_cb)],
        [InlineKeyboardButton('🗑 Remove', callback_data=remove_cb)],
        [InlineKeyboardButton('⬅️ Back', callback_data='show_metadata'), InlineKeyboardButton('❌ Close', callback_data='close_settings')],
    ])
