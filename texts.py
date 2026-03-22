from config import APP_NAME
from storage import get_user_settings


def start_text():
    return (
        f"👋 Welcome to **{APP_NAME} V2 Structured**\n\n"
        "Ye Code Devil ka working structured bot hai.\n\n"
        "**Available Commands:**\n"
        "/start - Bot start karo\n"
        "/ping - Bot status check karo\n"
        "/help - Help guide dekho\n"
        "/plan - Roadmap dekho\n"
        "/terms - Rules dekho\n"
        "/settings - Personal settings kholo\n"
        "/cancel - Current input cancel karo"
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
        "/cancel - Current text input mode cancel karne ke liye"
    )


def plan_text():
    return (
        "🛣️ **Code Devil Bot Roadmap**\n\n"
        "✅ V1 - Working base bot\n"
        "✅ V2 - Settings panel basic version\n"
        "🔜 V3 - Admin controls\n"
        "🔜 V4 - Login/session system\n"
        "🔜 V5 - Batch processing\n"
        "🔜 V6 - Premium + advanced tools"
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


def settings_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        f"⚙️ **Settings Panel**\n\n"
        f"**Upload Mode:** {s['upload_mode']}\n"
        f"**Thumbnail:** {'✅ On' if s['thumbnail'] else '❌ Off'}\n"
        f"**Caption:** {'✅ On' if s['caption'] else '❌ Off'}\n"
        f"**Prefix:** {s['prefix'] or 'None'}\n"
        f"**Suffix:** {s['suffix'] or 'None'}\n"
        f"**Auto Rename:** {s['auto_rename'] or 'None'}\n"
        f"**Metadata:** {'✅ On' if s['metadata'] else '❌ Off'}\n"
        f"**Upload Destination:** {s['upload_destination'] or 'None'}\n"
        f"**Topic ID:** {s['topic_id'] or 'None'}\n"
        f"**Replace Words:** {s['replace_words'] or 'None'}\n\n"
        f"Niche buttons se settings change kar sakte ho."
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
