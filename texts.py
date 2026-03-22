from config import APP_NAME
from storage import get_user_settings, get_index_user_count, index_count


def start_text():
    return (
        f"👋 Welcome to **{APP_NAME} V4**\n\n"
        "Ye Code Devil ka working structured bot hai.\n\n"
        "**Available Commands:**\n"
        "/start - Bot start karo\n"
        "/ping - Bot status check karo\n"
        "/help - Help guide dekho\n"
        "/plan - Roadmap dekho\n"
        "/terms - Rules dekho\n"
        "/settings - Personal settings kholo\n"
        "/cancel - Current input cancel karo\n\n"
        "**New in V4:**\n"
        "Advanced settings pages + indexing commands add ho gaye hain."
    )


def help_text():
    return (
        "📘 **Help Guide (Hinglish)**\n\n"
        "/start - Bot start karne ke liye\n"
        "/ping - Check karo bot online hai ya nahi\n"
        "/help - Ye help guide dekhne ke liye\n"
        "/plan - Aage ke versions me kya aayega dekhne ke liye\n"
        "/terms - Bot ke rules dekhne ke liye\n"
        "/settings - Personal settings panel kholne ke liye\n"
        "/cancel - Current text input mode cancel karne ke liye\n\n"
        "**Admin / Index Commands**\n"
        "/stats\n/users\n/ban user_id\n/unban user_id\n/broadcast your message\n"
        "/index_id - auto indexing on karo\n"
        "/stop_index - indexing off karo\n"
        "/index_stats - index stats dekho"
    )


def plan_text():
    return (
        "🛣️ **Code Devil Bot Roadmap**\n\n"
        "✅ V1 - Working base bot\n"
        "✅ V2 - Settings panel basic version\n"
        "✅ V3 - Admin controls basic version\n"
        "✅ V4 - Advanced settings + indexing\n"
        "🔜 V5 - Login/session system\n"
        "🔜 V6 - Batch processing\n"
        "🔜 V7 - Premium + advanced tools"
    )


def terms_text():
    return (
        "📜 **Terms / Rules**\n\n"
        "1. Bot responsibly use karo.\n"
        "2. Required channel join compulsory ho sakta hai.\n"
        "3. Spam ya abuse mat karo.\n"
        "4. Future versions me usage limits add ho sakti hain.\n"
        "5. Code Devil community updates ke liye channels join rakho."
    )


def settings_home_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        f"⚙️ **Settings for User**\n\n"
        f"Upload Mode: **{s['upload_mode']}**\n"
        f"Custom Thumbnail: **{'Exists' if s['thumbnail_file_id'] else 'None'}**\n"
        f"Caption: **{'Enabled' if s['caption_enabled'] else 'Disabled'}**\n"
        f"Prefix: **{s['prefix'] or 'None'}**\n"
        f"Suffix: **{s['suffix'] or 'None'}**\n"
        f"Auto Rename: **{s['auto_rename'] or 'None'}**\n"
        f"Metadata: **{'Enabled' if s['metadata_enabled'] else 'Disabled'}**\n"
        f"Upload Destination: **{s['upload_destination'] or 'None'}**\n"
        f"Topic ID: **{s['topic_id'] or 'None'}**\n"
        f"Replace Words: **{s['replace_words'] or 'None'}**\n\n"
        "Niche buttons se sab setting manage kar sakte ho."
    )


def upload_mode_text():
    return (
        "📤 **Upload Mode**\n\n"
        "Abhi bot me upload mode fixed **Telegram** rakha gaya hai, jaisa tumne bola tha.\n\n"
        "Aage future version me aur modes add kiye ja sakte hain."
    )


def thumbnail_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🖼 **Thumbnail Setting**\n\n"
        f"Current thumbnail: **{'Exists' if s['thumbnail_file_id'] else 'None'}**\n"
        f"Thumbnail status: **{'Enabled' if s['thumbnail_enabled'] else 'Disabled'}**\n\n"
        "Send a photo to save it as custom thumbnail.\nTimeout: 60 sec"
    )


def caption_text(user_id: int):
    s = get_user_settings(user_id)
    current = s['caption_text'] or 'None'
    return (
        "📝 **Caption Setting**\n\n"
        "Caption files ke niche custom text hota hai.\n\n"
        "**Variables use kar sakte ho:**\n"
        "{filename} - File name\n"
        "{size} - File size\n"
        "{duration} - Duration\n"
        "{quality} - Quality\n"
        "{language} - Language\n"
        "{subtitle} - Subtitle\n\n"
        f"Current caption:\n`{current}`\n\n"
        "HTML tags bhi use kar sakte ho. Timeout: 60 sec"
    )


def prefix_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🏷 **Prefix Setting**\n\n"
        "Prefix filename ke starting me add hota hai.\n\n"
        "Example:\n"
        "Prefix = @Code_Devil\n\n"
        "Output:\n"
        "@Code_Devil Fast_And_Furious.mkv\n\n"
        f"Current prefix: **{s['prefix'] or 'None'}**\n\n"
        "Send Prefix. Timeout: 60 sec"
    )


def suffix_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🔖 **Suffix Setting**\n\n"
        "Suffix filename ke end me add hota hai.\n\n"
        "Example:\n"
        "Suffix = @Code_Devil\n\n"
        "Output:\n"
        "Fast_And_Furious @Code_Devil.mkv\n\n"
        f"Current suffix: **{s['suffix'] or 'None'}**\n\n"
        "Send Suffix. Timeout: 60 sec"
    )


def auto_rename_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "✍️ **Auto Rename Setting**\n\n"
        "Yahan jo text doge, bot usse files ke naam me use karega.\n\n"
        f"Current auto rename: **{s['auto_rename'] or 'None'}**\n\n"
        "Send Auto Rename value. Timeout: 60 sec"
    )


def destination_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "📍 **Upload Destination Setting**\n\n"
        "Yahan chat id ya channel/group id set kar sakte ho.\n\n"
        f"Current destination: **{s['upload_destination'] or 'None'}**\n\n"
        "Send upload destination. Timeout: 60 sec"
    )


def topic_id_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🧵 **Topic ID Setting**\n\n"
        "Agar supergroup topics use kar rahe ho to topic id yahan set kar sakte ho.\n\n"
        f"Current topic id: **{s['topic_id'] or 'None'}**\n\n"
        "Send Topic ID. Timeout: 60 sec"
    )


def replace_words_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🔁 **Remove / Replace Words**\n\n"
        "Format example:\n"
        "old1:new1, old2:new2\n\n"
        "Sirf remove karna ho to:\n"
        "old1:, old2:\n\n"
        f"Current replace words: **{s['replace_words'] or 'None'}**\n\n"
        "Send remove/replace rules. Timeout: 60 sec"
    )


def metadata_home_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "📦 **Metadata Setting**\n\n"
        f"Metadata status: **{'Enabled' if s['metadata_enabled'] else 'Disabled'}**\n\n"
        f"Video Title: **{s['metadata_video_title'] or 'None'}**\n"
        f"Video Author: **{s['metadata_video_author'] or 'None'}**\n"
        f"Audio Title: **{s['metadata_audio_title'] or 'None'}**\n"
        f"Subtitle Title: **{s['metadata_subtitle_title'] or 'None'}**\n"
    )


def metadata_field_text(user_id: int, label: str, key: str):
    s = get_user_settings(user_id)
    return (
        f"📦 **{label} Setting**\n\n"
        f"Current value: **{s.get(key) or 'None'}**\n\n"
        f"Send {label}. Timeout: 60 sec"
    )


def unknown_text():
    return (
        "🤖 Mujhe ye commands bhejo:\n\n"
        "/start\n"
        "/ping\n"
        "/help\n"
        "/plan\n"
        "/terms\n"
        "/settings\n"
        "/cancel"
    )


def index_started_text(user_id: int):
    return (
        "🧠 **Index Mode On**\n\n"
        "Ab jo bhi content / text / media tum bhejoge, bot usko auto index karega.\n\n"
        "Band karne ke liye /stop_index bhejo."
    )


def index_stopped_text(user_id: int):
    return (
        "🛑 **Index Mode Off**\n\n"
        "Auto indexing band kar di gayi hai."
    )


def index_stats_text(user_id: int):
    return (
        "📚 **Index Stats**\n\n"
        f"Your indexed items: **{get_index_user_count(user_id)}**\n"
        f"Total indexed items: **{index_count()}**"
    )
