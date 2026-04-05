from config import APP_NAME, DEFAULT_PREMIUM_PLAN_NAME
from storage import (
    get_user_settings,
    get_index_user_count,
    index_count,
    is_index_mode,
    has_user_session,
    is_batch_mode,
    is_premium_user,
    get_premium_expiry_text,
    get_user_batch_limit,
    get_user_task_limit,
    get_user_plan_name,
    get_user_plan_features,
)

APP_VERSION_LABEL = "V12"


def _safe_text(value, fallback="None"):
    value = str(value or "").strip()
    return value if value else fallback


def _upload_mode_display(value: str) -> str:
    value = str(value or "").strip().lower()
    if value == "document":
        return "Document"
    return "Media"


def _premium_display(user_id: int) -> str:
    return "Premium 💎" if is_premium_user(user_id) else "Free 🆓"


def _plan_display(user_id: int) -> str:
    return f"{get_user_plan_name(user_id)} ({_premium_display(user_id)})"


def _plan_features_block(user_id: int) -> str:
    features = get_user_plan_features(user_id)
    if not features:
        return "Admin ne abhi is plan ke custom features set nahi kiye."
    return "\n".join([f"- {feature}" for feature in features])


def _yes_no_enabled(value: bool) -> str:
    return "Enabled ✅" if value else "Disabled ❌"


def _exists_text(value) -> str:
    return "Exists ✅" if value else "None"


def _task_destination_display(task: dict) -> str:
    if not isinstance(task, dict):
        return "Not Set"

    candidates = [
        task.get("user_destination"),
        task.get("destination_display"),
        task.get("destination"),
        task.get("destination_raw"),
        task.get("upload_destination"),
        task.get("target_chat"),
        task.get("target_chat_id"),
        task.get("destination_chat_id"),
        task.get("target"),
        task.get("dest"),
    ]

    for value in candidates:
        value = str(value or "").strip()
        if value:
            return value
    return "Not Set"


def _task_topic_display(task: dict) -> str:
    if not isinstance(task, dict):
        return "None"
    for key in ("topic_id", "message_thread_id", "thread_id"):
        value = str(task.get(key) or "").strip()
        if value:
            return value
    return "None"


def start_text():
    return (
        f"👋 Welcome to **{APP_NAME} {APP_VERSION_LABEL}**\n\n"
        "Ye Code Devil ka upgraded structured bot hai jisme settings, tasks, premium flow aur batch processing ko aur stable banaya gaya hai.\n\n"
        "**Available Commands:**\n"
        "/start - Bot start karo\n"
        "/ping - Bot status check karo\n"
        "/help - Help guide dekho\n"
        "/plan - Apna current plan dekho\n"
        "/terms - Rules dekho\n"
        "/settings - Personal settings kholo\n"
        "/login - Telegram account login karo\n"
        "/login_status - Login status dekho\n"
        "/logout - Saved login remove karo\n"
        "/my_tasks - Running/completed tasks dekho\n"
        "/cancel - Current input ya current task cancel karo\n"
        "/cancelall - Sab active tasks cancel karo\n\n"
        "**Highlights:**\n"
        "Cleaner task destination display + stronger task schema sync + better retry-friendly wording + premium-ready settings flow."
    )


def help_text(is_admin: bool = False):
    lines = [
        "📘 **Help Guide (Hinglish)**",
        "",
        "/start - Bot start karne ke liye",
        "/ping - Check karo bot online hai ya nahi",
        "/help - Ye help guide dekhne ke liye",
        "/plan - Apna current plan aur features dekhne ke liye",
        "/terms - Bot ke rules dekhne ke liye",
        "/settings - Personal settings panel kholne ke liye",
        "/login - Account login start karne ke liye",
        "/login_status - Saved session status dekhne ke liye",
        "/logout - Saved session remove karne ke liye",
        "/my_tasks - Task history dekhne ke liye",
        "/cancel - Current text input ya current running task cancel karne ke liye",
        "/cancelall - Sab active running tasks cancel karne ke liye",
        "/set_bot <bot_token> - Personal bot set/update karne ke liye",
        "/bot_status - Personal bot status dekhne ke liye",
        "/remove_bot - Personal bot remove karne ke liye",
        "/id - Us channel/group/topic me chat id nikaalne ke liye jahan bot admin ho",
        "",
        "**Caption Variables**",
        "{filename}, {size}, {duration}, {quality}, {language}, {subtitle}, {index}",
        "",
        "**Rename Variables**",
        "{filename}, {index}",
        "",
        "**Batch Use**",
        "Batch ON karke multiple Telegram links ek saath bhej sakte ho. Invalid ya missing posts skip ho jayengi.",
        "",
        "**Supported Batch Formats**",
        "1. Single link:",
        "   https://t.me/channel/25",
        "",
        "2. Multiple lines:",
        "   https://t.me/channel/25",
        "   https://t.me/channel/26",
        "",
        "3. Range format:",
        "   https://t.me/Code_Devil/39-69",
        "   https://t.me/c/2102477857/340-360",
        "",
        "4. Space separated links bhi bhej sakte ho.",
        "",
        "**Upload Modes**",
        "Telegram mode me bot Telegram destination par save karega.",
        "Google Drive mode me full content GDrive folder me upload hoga.",
        "Rclone mode me full content selected remote path par upload hoga.",
        "",
        "**Tip**",
        "Settings me Upload Mode button ko click karke Telegram -> Google Drive -> Rclone dynamically switch kar sakte ho.",
    ]
    if is_admin:
        lines.extend([
            "",
            "**Admin Commands**",
            "/stats",
            "/users",
            "/recent_users",
            "/ban user_id",
            "/unban user_id",
            "/broadcast your message",
            "/set_batch_limit user_id 500",
            "/set_task_limit user_id 10",
            "/set_storage_access user_id telegram,gdrive,rclone,personal_bot",
            "/set_plan user_id Gold",
            "/set_plan_features user_id feature 1 | feature 2",
            "/clear_plan_features user_id",
            "/plan_status user_id",
            "/premium_status user_id",
            "/add_premium user_id 30d",
            "/remove_premium user_id",
            "/id",
            "/index_id - auto indexing on karo",
            "/stop_index - indexing off karo",
            "/index_stats - index stats dekho",
        ])
    return "\n".join(lines)


def plan_text(user_id: int = 0):
    if not user_id:
        return (
            "🪪 **Plan Info**\n\n"
            "Apna current plan dekhne ke liye private chat me /plan bhejo."
        )

    expiry = _safe_text(get_premium_expiry_text(user_id), "No expiry set")
    return "\n".join([
        "🪪 **Your Plan**",
        "",
        f"Current Plan: **{_plan_display(user_id)}**",
        f"Expiry: **{expiry}**",
        "",
        "**Plan Features**",
        _plan_features_block(user_id),
    ])


def terms_text():
    return (
        "📜 **Terms / Rules**\n\n"
        "1. Bot responsibly use karo.\n"
        "2. Required channel join compulsory hai agar force subscribe enabled hai.\n"
        "3. Join ke bina bot ka koi feature use nahi hoga.\n"
        "4. Spam ya abuse mat karo.\n"
        "5. Authorized access sirf wahi chalega jahan account ka valid access ho.\n"
        "6. Premium misuse ya abuse hone par access remove kiya ja sakta hai.\n"
        "7. Code Devil community updates ke liye channels join rakho."
    )


def premium_info_text(user_id: int):
    status = _premium_display(user_id)
    expiry = _safe_text(get_premium_expiry_text(user_id), "No expiry set")
    batch_limit = get_user_batch_limit(user_id)
    task_limit = get_user_task_limit(user_id)

    return (
        " **Premium Info**\n\n"
        f"Current Plan: **{status}**\n"
        f"Plan Name: **{get_user_plan_name(user_id)}**\n"
        f"Expiry: **{expiry}**\n"
        f"Batch Limit: **{batch_limit}**\n"
        f"Task Limit: **{task_limit}**\n\n"
        "**Plan Features**\n"
        f"{_plan_features_block(user_id)}\n\n"
        "Premium users ko higher limits aur future advanced features mil sakte hain."
    )


def admin_panel_text():
    return (
        "🛡 **Admin Panel**\n\n"
        "Yahan se admin-related controls, premium management, plan settings aur broadcast/help actions access kiye ja sakte hain.\n\n"
        "**Useful Commands:**\n"
        "/stats\n"
        "/users\n"
        "/recent_users\n"
        "/ban user_id\n"
        "/unban user_id\n"
        "/broadcast your message\n"
        "/set_batch_limit user_id 500\n"
        "/set_task_limit user_id 10\n"
        "/set_storage_access user_id telegram,gdrive,rclone,personal_bot\n"
        "/set_plan user_id Gold\n"
        "/set_plan_features user_id feature 1 | feature 2\n"
        "/clear_plan_features user_id\n"
        "/plan_status user_id\n"
        "/id\n\n"
        "**Premium command examples:**\n"
        "/add_premium user_id 30d\n"
        "/remove_premium user_id\n"
        "/premium_status user_id"
    )


def admin_plan_help_text():
    return (
        "🧾 **Plan Settings Help**\n\n"
        "Admin kisi bhi user ke liye custom plan name aur plan features set kar sakta hai.\n\n"
        "**Commands:**\n"
        "`/set_plan user_id Gold`\n"
        "`/set_plan_features user_id feature 1 | feature 2 | feature 3`\n"
        "`/clear_plan_features user_id`\n"
        "`/plan_status user_id`\n\n"
        "Notes:\n"
        "- Plan name user ke My Plan aur /plan screen me dikhai dega.\n"
        "- Plan features `|` ya new line se alag karke set kar sakte ho.\n"
        "- Ye display layer existing premium expiry/limits ko revoke nahi karegi."
    )


def admin_premium_help_text():
    return (
        "💎 **Premium Admin Help**\n\n"
        "Suggested command style:\n"
        "`/add_premium user_id 30d`\n"
        "`/remove_premium user_id`\n"
        "`/premium_status user_id`\n\n"
        "Duration examples:\n"
        "`7d`, `30d`, `12h`, `4w`, `1m`, `1y`"
    )


def settings_home_text(user_id: int):
    s = get_user_settings(user_id)
    login_status = "Connected ✅" if has_user_session(user_id) else "Not Connected ❌"
    batch_status = "Enabled ✅" if is_batch_mode(user_id) else "Disabled ❌"
    storage_mode_key = str(s.get("storage_mode", "telegram") or "telegram").strip().lower()
    storage_mode = _storage_mode_display(storage_mode_key)
    lines = [
        "⚙️ **Settings for User**",
        "",
        f"Plan: **{_premium_display(user_id)}**",
        f"Storage Mode: **{storage_mode}**",
        f"Authorized Login: **{login_status}**",
        f"Batch Mode: **{batch_status}**",
        f"Batch Limit: **{get_user_batch_limit(user_id)}**",
        f"Task Limit: **{get_user_task_limit(user_id)}**",
        "",
    ]
    if storage_mode_key == "telegram":
        lines.extend([
            f"Telegram Upload Type: **{_upload_mode_display(s.get('telegram_upload_mode', s.get('upload_mode', 'media')))}**",
            f"Telegram Destination: **{_safe_text(s.get('upload_destination'))}**",
            f"Topic ID: **{_safe_text(s.get('topic_id'))}**",
            "Tip: /id command help guide me diya gaya hai.",
        ])
    elif storage_mode_key == "gdrive":
        lines.extend([
            f"GDrive Token: **{_exists_text(s.get('gdrive_token_path'))}**",
            f"GDrive Folder ID: **{_safe_text(s.get('gdrive_folder_id'))}**",
            f"Last GDrive Link: **{_safe_text(s.get('gdrive_last_file_link'))}**",
        ])
    elif storage_mode_key == "rclone":
        lines.extend([
            f"Rclone Config: **{_exists_text(s.get('rclone_config_path'))}**",
            f"Rclone Path: **{_safe_text(s.get('rclone_remote_path'))}**",
            f"Last Rclone Target: **{_safe_text(s.get('rclone_last_file_path'))}**",
        ])
    lines.extend([
        "",
        f"Custom Thumbnail: **{_exists_text(s.get('thumbnail_file_id'))}**",
        f"Caption: **{'Enabled ✅' if s.get('caption_enabled') else 'Disabled ❌'}**",
        f"Prefix: **{_safe_text(s.get('prefix'))}**",
        f"Suffix: **{_safe_text(s.get('suffix'))}**",
        f"Auto Rename: **{_safe_text(s.get('auto_rename'))}**",
        f"Rename Template: **{_safe_text(s.get('rename_template'))}**",
        f"Filename Prefix: **{_safe_text(s.get('filename_prefix'))}**",
        f"Filename Suffix: **{_safe_text(s.get('filename_suffix'))}**",
        f"Metadata: **{'Enabled ✅' if s.get('metadata_enabled') else 'Disabled ❌'}**",
        f"Replace Words: **{_safe_text(s.get('replace_words'))}**",
        f"Index Mode: **{_yes_no_enabled(is_index_mode(user_id))}**",
        "",
        "Storage Mode button ko tap karke Telegram -> Google Drive -> Rclone dynamically switch kar sakte ho.",
    ])
    return "\n".join(lines)


def upload_mode_text(user_id: int = 0):
    mode = "Media"
    if user_id:
        mode = _upload_mode_display(get_user_settings(user_id).get("upload_mode", "media"))

    return (
        "📤 **Upload Mode**\n\n"
        f"Current upload mode: **{mode}**\n\n"
        "**Media Mode:**\n"
        "Photo, video, audio ko media type me bhejne ki koshish hogi.\n\n"
        "**Document Mode:**\n"
        "Files ko document ki tarah bheja jayega.\n\n"
        "Settings button se mode toggle kar sakte ho."
    )


def thumbnail_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🖼 **Thumbnail Setting**\n\n"
        f"Current thumbnail: **{_exists_text(s.get('thumbnail_file_id'))}**\n"
        f"Thumbnail status: **{'Enabled ✅' if s.get('thumbnail_enabled') else 'Disabled ❌'}**\n\n"
        "Send a photo to save it as custom thumbnail.\n"
        "Timeout: 60 sec"
    )


def caption_text(user_id: int):
    s = get_user_settings(user_id)
    current = s.get("caption_text") or "None"
    padding = s.get("caption_index_padding", 2)
    start = s.get("caption_index_start", 1)

    return (
        "📝 **Caption Setting**\n\n"
        "Caption uploaded file ke niche custom text hota hai.\n\n"
        "**Variables use kar sakte ho:**\n"
        "{filename} - File name\n"
        "{size} - File size\n"
        "{duration} - Duration\n"
        "{quality} - Quality\n"
        "{language} - Language\n"
        "{subtitle} - Subtitle\n"
        "{index} - Auto index number\n\n"
        "**{index} Example:**\n"
        f"Current padding: **{padding}**\n"
        f"Current start: **{start}**\n"
        "Output example: `01`, `02`, `03`\n\n"
        "**HTML formatting examples:**\n"
        "<b>Bold</b>\n"
        "<i>Italic</i>\n"
        "<u>Underline</u>\n"
        "<code>Monospace</code>\n"
        "<a href='https://t.me/Code_Devil'>Link</a>\n\n"
        f"Current caption:\n`{current}`\n\n"
        "Example caption:\n"
        "`<b>{index}</b> | {filename}`\n\n"
        "HTML tags use kar sakte ho. Timeout: 60 sec"
    )


def prefix_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🏷 **Prefix Setting**\n\n"
        "Prefix filename ya caption ke starting me add hota hai.\n\n"
        "Example:\n"
        "Prefix = @Code_Devil\n\n"
        "Output:\n"
        "@Code_Devil Fast_And_Furious.mkv\n\n"
        f"Current prefix: **{_safe_text(s.get('prefix'))}**\n\n"
        "Send Prefix. Timeout: 60 sec"
    )


def suffix_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🔖 **Suffix Setting**\n\n"
        "Suffix filename ya caption ke end me add hota hai.\n\n"
        "Example:\n"
        "Suffix = @Code_Devil\n\n"
        "Output:\n"
        "Fast_And_Furious @Code_Devil.mkv\n\n"
        f"Current suffix: **{_safe_text(s.get('suffix'))}**\n\n"
        "Send Suffix. Timeout: 60 sec"
    )


def auto_rename_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "✍️ **Auto Rename Setting**\n\n"
        "Yahan tum filename ko advanced tareeke se control kar sakte ho.\n\n"
        "**Simple Mode:**\n"
        "auto_rename me jo text doge, bot usko filename me use karega.\n\n"
        "**Advanced Variables:**\n"
        "{filename} - Original filename\n"
        "{index} - Auto index number\n\n"
        "**Advanced Fields:**\n"
        f"Rename Template: **{_safe_text(s.get('rename_template'))}**\n"
        f"Filename Prefix: **{_safe_text(s.get('filename_prefix'))}**\n"
        f"Filename Suffix: **{_safe_text(s.get('filename_suffix'))}**\n"
        f"Filename Index Enabled: **{'Yes' if s.get('filename_index_enabled') else 'No'}**\n"
        f"Filename Index Padding: **{s.get('filename_index_padding', 2)}**\n"
        f"Filename Index Start: **{s.get('filename_index_start', 1)}**\n\n"
        f"Current auto rename: **{_safe_text(s.get('auto_rename'))}**\n\n"
        "Example rename template:\n"
        "`Movie_{index}`\n"
        "`{index}_{filename}`\n\n"
        "Send Auto Rename value. Timeout: 60 sec"
    )


def destination_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "📍 **Upload Destination Setting**\n\n"
        "Yahan chat id ya channel/group id set kar sakte ho.\n\n"
        "Example:\n"
        "`-1001234567890`\n"
        "`@yourchannelusername`\n\n"
        f"Current destination: **{_safe_text(s.get('upload_destination'))}**\n\n"
        "Send upload destination. Timeout: 60 sec"
    )


def topic_id_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "🧵 **Topic ID Setting**\n\n"
        "Agar supergroup topics use kar rahe ho to topic id yahan set kar sakte ho.\n\n"
        f"Current topic id: **{_safe_text(s.get('topic_id'))}**\n\n"
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
        f"Current replace words: **{_safe_text(s.get('replace_words'))}**\n\n"
        "Ye filename aur caption dono cleaning me use ho sakta hai.\n"
        "Send remove/replace rules. Timeout: 60 sec"
    )


def metadata_home_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "📦 **Metadata Setting**\n\n"
        f"Metadata status: **{'Enabled ✅' if s.get('metadata_enabled') else 'Disabled ❌'}**\n\n"
        f"Video Title: **{_safe_text(s.get('metadata_video_title'))}**\n"
        f"Video Author: **{_safe_text(s.get('metadata_video_author'))}**\n"
        f"Audio Title: **{_safe_text(s.get('metadata_audio_title'))}**\n"
        f"Subtitle Title: **{_safe_text(s.get('metadata_subtitle_title'))}**"
    )


def metadata_field_text(user_id: int, label: str, key: str):
    s = get_user_settings(user_id)
    return (
        f"📦 **{label} Setting**\n\n"
        f"Current value: **{_safe_text(s.get(key))}**\n\n"
        f"Send {label}. Timeout: 60 sec"
    )


def batch_text(user_id: int):
    s = get_user_settings(user_id)
    current = s.get("batch_last_input") or "None"
    return (
        "📦 **Batch Mode Setting**\n\n"
        f"Batch mode: **{'Enabled ✅' if is_batch_mode(user_id) else 'Disabled ❌'}**\n"
        f"Current tier: **{_premium_display(user_id)}**\n"
        f"Your batch limit: **{get_user_batch_limit(user_id)}**\n\n"
        "Batch ON hone par multiple Telegram links ek saath process kar sakte ho.\n\n"
        "**Supported formats:**\n"
        "1. Single link:\n"
        "`https://t.me/channel/25`\n\n"
        "2. Multiple links:\n"
        "`https://t.me/channel/25`\n"
        "`https://t.me/channel/26`\n\n"
        "3. Range link:\n"
        "`https://t.me/Codebasics_courses_free/39-69`\n"
        "`https://t.me/c/2102477197/340-360`\n\n"
        "4. Space separated:\n"
        "`https://t.me/channel/25 https://t.me/channel/26`\n\n"
        "Range ka matlab start se end tak sab posts process hongi.\n\n"
        f"Last batch input:\n`{current}`\n\n"
        "Set Batch Links button se multiple links ya range save karo."
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
        "/login\n"
        "/login_status\n"
        "/logout\n"
        "/my_tasks\n"
        "/cancel"
    )


def index_started_text(user_id: int):
    return (
        "🧠 **Index Mode On**\n\n"
        "Ab jo bhi content / text / media tum bhejoge, bot usko auto index karega.\n"
        "Agar destination set hai to waha auto upload bhi karega.\n"
        "Agar log channel set hai to waha bhi save karega.\n\n"
        "Band karne ke liye /stop_index bhejo."
    )


def index_stopped_text(user_id: int):
    return "🛑 **Index Mode Off**\n\nAuto indexing band kar di gayi hai."


def index_stats_text(user_id: int):
    return (
        "📚 **Index Stats**\n\n"
        f"Your indexed items: **{get_index_user_count(user_id)}**\n"
        f"Total indexed items: **{index_count()}**"
    )


def index_info_text(user_id: int):
    return (
        "⚡ **Auto Index + Upload Mode**\n\n"
        "Agar ON hai:\n"
        "• Link / media / content bhejo\n"
        "• Bot auto process karega\n"
        "• Destination par upload karega\n"
        "• Log channel me save karega\n"
        "• {index} caption aur rename me use ho sakta hai\n"
        "• /start bhejne par tumhara current user index reset ho jayega\n"
        "• Batch mode me range links bhi use ho sakte hain\n"
        "• Upload mode Media ya Document dono me switch kiya ja sakta hai\n\n"
        "OFF karne ke liye /stop_index"
    )


def login_intro_text():
    return (
        "🔐 **Login System**\n\n"
        "Yahan tum apna Telegram account authorize kar sakte ho.\n\n"
        "**Flow:**\n"
        "1. /login bhejo\n"
        "2. Phone number bhejo\n"
        "3. OTP bhejo\n"
        "4. Agar 2-step password enabled hai to password bhejo\n\n"
        "Cancel karne ke liye /cancel bhejo."
    )


def ask_phone_text():
    return (
        "📱 **Phone Number Bhejo**\n\n"
        "Example:\n"
        "`+919876543210`\n\n"
        "Telegram account ka number international format me bhejo."
    )


def ask_code_text():
    return (
        "🔑 **OTP / Login Code Bhejo**\n\n"
        "Telegram ne jo login code bheja hai woh yahan bhejo.\n\n"
        "Example formats:\n"
        "`12345`\n"
        "`1 2 3 4 5`"
    )


def ask_password_text():
    return (
        "🔒 **2-Step Password Bhejo**\n\n"
        "Tumhare Telegram account par cloud password enabled hai.\n"
        "Apna password bhejo."
    )


def login_success_text(phone: str = ""):
    phone_info = f"\n📱 Phone: `{phone}`" if phone else ""
    return (
        "✅ **Login Successful**\n\n"
        "Tumhara Telegram account authorize ho gaya hai.\n"
        "Ab authorized access workflow use kiya ja sakta hai."
        f"{phone_info}"
    )


def login_failed_text(error: str):
    return (
        "❌ **Login Failed**\n\n"
        f"Error:\n`{error}`\n\n"
        "Dobara /login try karo."
    )


def login_status_text(user_id: int):
    if has_user_session(user_id):
        s = get_user_settings(user_id)
        return (
            "✅ **Login Status**\n\n"
            "Authorized session connected hai.\n"
            f"Last Login User ID: **{s.get('last_login_user_id') or 'Unknown'}**"
        )
    return (
        "⚠️ **Login Status**\n\n"
        "Abhi koi authorized session connected nahi hai.\n\n"
        "Login karne ke liye /login bhejo."
    )


def logout_success_text():
    return "🚪 **Logout Successful**\n\nSaved session remove kar di gayi hai."


def logout_missing_text():
    return "⚠️ **Logout**\n\nAbhi koi saved session mila hi nahi."


def checking_text(link_text: str = ""):
    link_text = str(link_text or "").strip()
    if link_text:
        return (
            "🔎 **Checking Link...**\n\n"
            f"**Source:** `{link_text}`\n"
            "_Please wait... bot source access aur task readiness verify kar raha hai._"
        )
    return "🔎 **Checking Link...**\n\n_Please wait... bot source access aur task readiness verify kar raha hai._"


def batch_live_board_text(board: dict):
    board = dict(board or {})
    total = int(board.get("total") or 0)
    running = int(board.get("running") or 0)
    completed = int(board.get("completed") or 0)
    failed = int(board.get("failed") or 0)
    current_index = int(board.get("current_index") or 0)
    current_source = str(board.get("current_source") or "").strip()
    current_stage = str(board.get("current_stage") or "").strip() or "Checking"
    current_task_id = str(board.get("current_task_id") or "").strip()
    progress_bar_text = str(board.get("progress_bar_text") or "").strip()
    progress_percent = board.get("progress_percent")
    processed = str(board.get("processed_text") or "").strip()
    speed = str(board.get("speed_text") or "").strip()
    eta = str(board.get("eta_text") or "").strip()
    elapsed = str(board.get("elapsed_text") or "").strip()
    status = str(board.get("status") or "Running").strip()
    status_key = status.lower()
    current_stage_key = current_stage.lower()
    show_transfer_metrics = status_key not in {"cancelled", "completed", "failed"} and current_stage_key not in {"cancelled", "completed", "failed"}

    lines = [
        "📌 **Batch Processing**",
        "",
        f"**Status:** `{status}`",
        f"**Progress:** `{completed + failed}/{total}` | **Running:** `{running}` | **Failed:** `{failed}`",
    ]
    if current_index:
        lines.append(f"**Current Link:** `{current_index}/{max(total, current_index)}`")
    if current_task_id:
        lines.append(f"**Task ID:** `{current_task_id}`")
    if current_stage:
        lines.append(f"**Stage:** `{current_stage}`")
    if current_source:
        lines.append(f"**Source:** `{current_source}`")
    if show_transfer_metrics and progress_bar_text:
        try:
            lines.append(f"**Transfer:** `{progress_bar_text}` **{float(progress_percent or 0):.2f}%**")
        except Exception:
            lines.append(f"**Transfer:** `{progress_bar_text}`")
    if show_transfer_metrics and processed:
        lines.append(f"**Processed:** `{processed}`")
    if show_transfer_metrics and speed:
        lines.append(f"**Speed:** `{speed}`")
    if show_transfer_metrics and eta:
        lines.append(f"**ETA:** `{eta}`")
    if elapsed:
        lines.append(f"**Elapsed:** `{elapsed}`")
    return "\n".join(lines)


def batch_completed_board_text(board: dict):
    board = dict(board or {})
    batch_name = str(board.get("batch_name") or "Batch Job").strip()
    total = int(board.get("total") or 0)
    completed = int(board.get("completed") or 0)
    failed = int(board.get("failed") or 0)
    elapsed = str(board.get("elapsed_text") or "").strip()

    lines = [
        "𝗝𝗼𝗯 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱",
        "",
        f"𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 » {batch_name}",
        f"𝗩𝗮𝗹𝗶𝗱 𝗟𝗶𝗻𝗸𝘀 » {total}",
        f"𝗦𝘂𝗰𝗰𝗲𝘀𝘀 » {completed}",
        f"𝗙𝗮𝗶𝗹𝗲𝗱 » {failed}",
    ]
    if elapsed:
        lines.append(f"𝗘𝗹𝗮𝗽𝘀𝗲𝗱 » {elapsed}")
    lines.extend([
        "",
        "𝘙𝘦𝘱𝘰𝘳𝘵 𝘵𝘰 𝘉𝘖𝘛 𝘈𝘥𝘮𝘪𝘯 𝘧𝘰𝘳 𝘧𝘢𝘪𝘭𝘦𝘥 𝘭𝘪𝘯𝘬𝘴 𝘪𝘧 𝘢𝘯𝘺.",
    ])
    return "\n".join(lines)
def auto_index_completed_text(payload: dict):
    payload = dict(payload or {})
    batch_name = str(payload.get("batch_name") or "Single Link Job").strip()
    valid_links = int(payload.get("valid_links") or 1)
    success = int(payload.get("success") or 1)
    failed = int(payload.get("failed") or 0)
    destination = str(payload.get("destination") or "Not Set").strip()
    index_no = payload.get("index_no")
    user_index_no = payload.get("user_index_no")
    link_type = str(payload.get("link_type") or "unknown").strip()

    lines = [
        "𝗝𝗼𝗯 𝗖𝗼𝗺𝗽𝗹𝗲𝘁𝗲𝗱",
        "",
        f"𝗕𝗮𝘁𝗰𝗵 𝗡𝗮𝗺𝗲 » {batch_name}",
        f"𝗩𝗮𝗹𝗶𝗱 𝗟𝗶𝗻𝗸𝘀 » {valid_links}",
        f"𝗦𝘂𝗰𝗰𝗲𝘀𝘀 » {success}",
        f"𝗙𝗮𝗶𝗹𝗲𝗱 » {failed}",
    ]
    if index_no not in (None, "", 0):
        lines.append(f"𝗚𝗹𝗼𝗯𝗮𝗹 𝗜𝗻𝗱𝗲𝘅 » {index_no}")
    if user_index_no not in (None, "", 0):
        lines.append(f"𝗨𝘀𝗲𝗿 𝗜𝗻𝗱𝗲𝘅 » {user_index_no}")
    if destination:
        lines.append(f"𝗗𝗲𝘀𝘁𝗶𝗻𝗮𝘁𝗶𝗼𝗻 » {destination}")
    if link_type:
        lines.append(f"𝗟𝗶𝗻𝗸 𝗧𝘆𝗽𝗲 » {link_type}")
    lines.extend([
        "",
        "𝘙𝘦𝘱𝘰𝘳𝘵 𝘵𝘰 𝘉𝘖𝘛 𝘈𝘥𝘮𝘪𝘯 𝘧𝘰𝘳 𝘧𝘢𝘪𝘭𝘦𝘥 𝘭𝘪𝘯𝘬𝘴 𝘪𝘧 𝘢𝘯𝘺.",
    ])
    return "\n".join(lines)


def _stage_label(task: dict) -> str:
    stage = str(task.get("current_stage") or task.get("status") or "checking").strip().lower()
    labels = {
        "checking": "Checking",
        "queued": "Checking",
        "processing": "Checking",
        "fetching": "Checking",
        "downloading": "Downloading",
        "uploading": "Uploading",
        "copying": "Copying",
        "completed": "Completed",
        "failed": "Failed",
        "cancelled": "Cancelled",
    }
    return labels.get(stage, stage.title())


def _fmt_bytes(value) -> str:
    try:
        value = float(value or 0)
    except Exception:
        value = 0.0
    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.2f} {units[idx]}"


def _fmt_speed(value) -> str:
    try:
        value = float(value or 0)
    except Exception:
        value = 0.0
    return f"{_fmt_bytes(value)}/s"


def _fmt_eta(value) -> str:
    try:
        seconds = int(float(value or 0))
    except Exception:
        seconds = 0
    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def _fmt_elapsed(value) -> str:
    return _fmt_eta(value)


def _user_destination_display(task: dict) -> str:
    if not isinstance(task, dict):
        return "Not Set"
    for key in ("user_destination", "destination_display", "destination"):
        value = str(task.get(key) or "").strip()
        if value:
            return value
    return "Not Set"


def task_running_text(task: dict):
    stage = _stage_label(task)
    source = task.get("source", "unknown")
    destination = _user_destination_display(task)
    progress_note = str(task.get("progress_text") or "").strip()
    retries = task.get("retry_count", task.get("retries"))
    topic_id = _task_topic_display(task)
    upload_mode = _upload_mode_display(task.get("upload_mode", "media"))
    task_id = str(task.get("id") or task.get("task_id") or "").strip()

    progress_bar_text = str(task.get("progress_bar_text") or "").strip()
    progress_percent = task.get("progress_percent", task.get("progress"))
    current_bytes = task.get("current_bytes", 0)
    total_bytes = task.get("total_bytes", 0)
    speed_bps = task.get("speed_bps", 0)
    eta_seconds = task.get("eta_seconds", 0)
    elapsed_seconds = task.get("elapsed_seconds", 0)

    lines = ["✨ **Task Processing**", ""]
    if task_id:
        lines.append(f"**Task ID:** `{task_id}`")
    lines.extend([
        f"**Stage:** `{stage}`",
        f"**Source:** `{source}`",
        f"**Destination:** `{destination}`",
    ])

    if str(topic_id).strip() and str(topic_id).strip().lower() != "none":
        lines.append(f"**Topic ID:** `{topic_id}`")
    lines.append(f"**Mode:** `{upload_mode}`")

    if str(stage).lower() not in {"checking"}:
        if progress_bar_text and progress_percent not in (None, ""):
            try:
                lines.append(f"**Transfer:** `{progress_bar_text}` **{float(progress_percent):.2f}%**")
            except Exception:
                lines.append(f"**Transfer:** `{progress_bar_text}`")
        elif progress_percent not in (None, ""):
            try:
                lines.append(f"**Transfer:** **{float(progress_percent):.2f}%**")
            except Exception:
                pass
        if total_bytes:
            lines.append(f"**Processed:** `{_fmt_bytes(current_bytes)}` / `{_fmt_bytes(total_bytes)}`")
        elif current_bytes:
            lines.append(f"**Processed:** `{_fmt_bytes(current_bytes)}`")
        if speed_bps:
            lines.append(f"**Speed:** `{_fmt_speed(speed_bps)}`")
        if eta_seconds:
            lines.append(f"**ETA:** `{_fmt_eta(eta_seconds)}`")
        if elapsed_seconds:
            lines.append(f"**Elapsed:** `{_fmt_elapsed(elapsed_seconds)}`")

    if retries not in (None, "", 0):
        lines.append(f"**Retries:** `{retries}`")
    return "\n".join(lines)


def task_completed_text(task: dict):
    progress = task.get("progress_text", "")
    destination = _user_destination_display(task)
    topic_id = _task_topic_display(task)
    elapsed_seconds = task.get("elapsed_seconds", 0)
    task_id = str(task.get("id") or task.get("task_id") or "").strip()

    lines = ["✅ **Task Completed**", ""]
    if task_id:
        lines.append(f"**Task ID:** `{task_id}`")
    lines.extend([
        f"**Source:** `{task.get('source', 'unknown')}`",
        f"**Destination:** `{destination}`",
    ])
    if str(topic_id).strip() and str(topic_id).strip().lower() != "none":
        lines.append(f"**Topic ID:** `{topic_id}`")
    if elapsed_seconds:
        lines.append(f"**Elapsed:** `{_fmt_elapsed(elapsed_seconds)}`")
    if progress:
        lines.append(f"**Result:** `{progress}`")
    return "\n".join(lines)


def task_failed_text(task: dict):
    destination = _user_destination_display(task)
    retries = task.get("retry_count", task.get("retries"))
    stage = _stage_label(task)
    task_id = str(task.get("id") or task.get("task_id") or "").strip()

    lines = ["❌ **Task Failed**", ""]
    if task_id:
        lines.append(f"**Task ID:** `{task_id}`")
    lines.extend([
        f"**Stage:** `{stage}`",
        f"**Source:** `{task.get('source', 'unknown')}`",
        f"**Destination:** `{destination}`",
        f"**Error:** `{task.get('error', 'Unknown error')}`",
    ])
    if retries not in (None, "", 0):
        lines.append(f"**Retries Used:** `{retries}`")
    return "\n".join(lines)


def my_tasks_text(tasks: list):
    if not tasks:
        return "📂 **My Tasks**\n\nAbhi koi task history nahi mili."

    lines = ["📂 **My Tasks**\n"]
    for i, task in enumerate(tasks[:10], start=1):
        stage = _stage_label(task)
        source = task.get("source", "unknown")
        destination = _user_destination_display(task)
        percent = task.get("progress_percent", task.get("progress"))
        task_id = str(task.get("id") or task.get("task_id") or "").strip()
        suffix = ""

        if percent not in (None, "") and str(stage).lower() not in {"completed", "failed", "cancelled", "checking"}:
            try:
                suffix = f" | {float(percent):.1f}%"
            except Exception:
                suffix = ""

        lines.append(
            f"{i}. **{stage}**{suffix}\n"
            f"   **Task ID:** `{task_id or '-'}`\n"
            f"   **Source:** `{source}`\n"
            f"   **Destination:** `{destination}`"
        )

    return "\n".join(lines)


# =========================================================
# V13/V14/V15 OVERRIDES
# =========================================================
def _storage_mode_display(value: str) -> str:
    value = str(value or "telegram").strip().lower()
    return {"telegram": "Telegram", "gdrive": "Google Drive", "rclone": "Rclone"}.get(value, "Telegram")


def settings_home_text(user_id: int):
    s = get_user_settings(user_id)
    login_status = "Connected ✅" if has_user_session(user_id) else "Not Connected ❌"
    batch_status = "Enabled ✅" if is_batch_mode(user_id) else "Disabled ❌"
    storage_mode = str(s.get("storage_mode", "telegram") or "telegram").strip().lower()

    lines = [
        "⚙️ **Settings for User**",
        "",
        f"Plan: **{_plan_display(user_id)}**",
        f"Storage Mode: **{_storage_mode_display(storage_mode)}**",
        f"Authorized Login: **{login_status}**",
        f"Batch Mode: **{batch_status}**",
        f"Batch Limit: **{get_user_batch_limit(user_id)}**",
        f"Task Limit: **{get_user_task_limit(user_id)}**",
        "",
    ]

    if storage_mode == "telegram":
        lines.extend([
            f"Destination: **{_safe_text(s.get('upload_destination'))}**",
            f"Topic ID: **{_safe_text(s.get('topic_id'))}**",
            f"Telegram Upload Type: **{_upload_mode_display(s.get('telegram_upload_mode', s.get('upload_mode', 'media')))}**",
        ])
    elif storage_mode == "gdrive":
        lines.extend([
            f"Destination: **{_safe_text(s.get('gdrive_folder_id'))}**",
            f"Token File: **{_exists_text(s.get('gdrive_token_path'))}**",
            f"Last GDrive Link: **{_safe_text(s.get('gdrive_last_file_link'))}**",
        ])
    elif storage_mode == "rclone":
        lines.extend([
            f"Destination: **{_safe_text(s.get('rclone_remote_path'))}**",
            f"Config File: **{_exists_text(s.get('rclone_config_path'))}**",
            f"Last Rclone Target: **{_safe_text(s.get('rclone_last_file_path'))}**",
        ])

    lines.extend([
        "",
        f"Custom Thumbnail: **{_exists_text(s.get('thumbnail_file_id'))}**",
        f"Caption: **{'Enabled ✅' if s.get('caption_enabled') else 'Disabled ❌'}**",
        f"Prefix: **{_safe_text(s.get('prefix'))}**",
        f"Suffix: **{_safe_text(s.get('suffix'))}**",
        f"Auto Rename: **{_safe_text(s.get('auto_rename'))}**",
        f"Rename Template: **{_safe_text(s.get('rename_template'))}**",
        f"Filename Prefix: **{_safe_text(s.get('filename_prefix'))}**",
        f"Filename Suffix: **{_safe_text(s.get('filename_suffix'))}**",
        f"Metadata: **{'Enabled ✅' if s.get('metadata_enabled') else 'Disabled ❌'}**",
        f"Replace Words: **{_safe_text(s.get('replace_words'))}**",
        f"Index Mode: **{_yes_no_enabled(is_index_mode(user_id))}**",
        "",
        "Storage Mode button se Telegram -> Google Drive -> Rclone dynamically switch hota hai.",
        "Telegram Upload Type button se Media <-> Document toggle hota hai.",
        "Tip: /id command help guide me diya gaya hai.",
    ])
    return "\n".join(lines)

def upload_mode_text(user_id: int = 0):
    mode = "Media"
    if user_id:
        s = get_user_settings(user_id)
        mode = _upload_mode_display(s.get('telegram_upload_mode', s.get('upload_mode', 'media')))
    return "\n".join([
        "📤 **Telegram Upload Mode**",
        "",
        f"Current telegram upload mode: **{mode}**",
        "",
        "Media mode Telegram destination me media ki tarah send karega.",
        "",
        "Document mode Telegram destination me document ki tarah send karega.",
        "",
        "Ye setting sirf Telegram storage mode ke liye apply hoti hai.",
        "Quick Toggle button se turant Media <-> Document switch kar sakte ho.",
    ])


def destination_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "📍 **Telegram Destination Setting**",
        "",
        "Yahan chat id ya @channelusername set kar sakte ho.",
        "",
        "Examples:",
        "`-1001234567890`",
        "`@yourchannelusername`",
        "",
        f"Current telegram destination: **{_safe_text(s.get('upload_destination'))}**",
        f"Current topic id: **{_safe_text(s.get('topic_id'))}**",
        "",
        "Tip: Agar bot aapke channel/group me admin hai to /id command se id nikaal sakte ho.",
    ])


def gdrive_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "☁️ **Google Drive Settings**",
        "",
        f"Folder ID: **{_safe_text(s.get('gdrive_folder_id'))}**",
        f"Token File: **{_exists_text(s.get('gdrive_token_path'))}**",
        f"Last Link: **{_safe_text(s.get('gdrive_last_file_link'))}**",
        "",
        "1. token.pickle bhejo",
        "2. Folder ID set karo",
        "3. Storage Mode ko Google Drive select karo",
    ])


def rclone_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "🗂 **Rclone Settings**",
        "",
        f"Config File: **{_exists_text(s.get('rclone_config_path'))}**",
        f"Remote Path: **{_safe_text(s.get('rclone_remote_path'))}**",
        f"Last Target: **{_safe_text(s.get('rclone_last_file_path'))}**",
        "",
        "1. rclone.conf bhejo",
        "2. Remote path set karo",
        "3. Storage Mode ko Rclone select karo",
    ])


def personal_bot_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "🤖 **Personal Bot Settings**",
        "",
        f"Bot Token: **{_exists_text(s.get('personal_bot_token'))}**",
        f"Bot Username: **{_safe_text(s.get('personal_bot_username'))}**",
        f"Delivery Mode: **{_safe_text(s.get('bot_delivery_mode'), 'main')}**",
        "",
        "Commands:",
        "`/set_bot <bot_token>`",
        "`/bot_status`",
        "`/remove_bot`",
    ])


def route_template_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "🧭 **Route Template**",
        "",
        f"Current template: **{_safe_text(s.get('route_template'), 'off')}**",
        "",
        "Available:",
        "- off",
        "- smart",
        "- docs_to_gdrive",
        "- media_to_telegram",
        "- archives_to_rclone",
    ])


def admin_stats_text(payload: dict):
    payload = payload or {}
    storage_counts = payload.get('storage_counts', {}) or {}
    task_counts = payload.get('task_counts', {}) or {}
    stats = payload.get('stats', {}) or {}
    return "\n".join([
        "📊 **Bot Stats**",
        "",
        f"Total Users: **{payload.get('total_users', 0)}**",
        f"Active Users (7d): **{payload.get('active_users', 0)}**",
        f"Logged-in Users: **{payload.get('logged_in_users', 0)}**",
        f"Premium Users: **{payload.get('premium_users', 0)}**",
        "",
        f"Telegram Mode Users: **{storage_counts.get('telegram', 0)}**",
        f"GDrive Mode Users: **{storage_counts.get('gdrive', 0)}**",
        f"Rclone Mode Users: **{storage_counts.get('rclone', 0)}**",
        "",
        f"Tasks Total: **{task_counts.get('total', 0)}**",
        f"Completed: **{task_counts.get('completed', 0)}** | Failed: **{task_counts.get('failed', 0)}**",
        f"Running: **{task_counts.get('running', 0)}** | Queued: **{task_counts.get('queued', 0)}**",
        f"Batch Tasks: **{task_counts.get('batch', 0)}**",
        "",
        f"Stats File → Tasks Created: **{stats.get('tasks_created', 0)}** | Completed: **{stats.get('tasks_completed', 0)}** | Failed: **{stats.get('tasks_failed', 0)}**",
    ])


def all_users_text(users: list, title: str = "All Users"):
    if not users:
        return f"👥 **{title}**\n\nNo users"
    rows = [f"• {u.get('first_name') or 'User'} | `{u.get('id')}` | @{u.get('username') or 'no_username'}" for u in users]
    return f"👥 **{title}**\n\n" + "\n".join(rows)


def batch_analysis_text(summary: dict):
    summary = summary or {}
    invalid_tokens = summary.get('invalid_tokens', []) or []
    invalid_preview = "\n".join(f"• `{item}`" for item in invalid_tokens[:10]) or "None"
    return "\n".join([
        "📦 **Batch Analyzer**",
        "",
        f"Valid Links: **{summary.get('valid_links', 0)}**",
        f"Invalid Links: **{summary.get('invalid_links', 0)}**",
        f"Public Links: **{summary.get('public_links', 0)}**",
        f"Private Links: **{summary.get('private_links', 0)}**",
        f"Topic Links: **{summary.get('topic_links', 0)}**",
        "",
        "Invalid Preview:",
        invalid_preview,
    ])


def id_info_text(chat, topic_id: int | None = None):
    title = getattr(chat, 'title', None) or getattr(chat, 'first_name', None) or 'Unknown'
    username = getattr(chat, 'username', None) or 'None'
    chat_type = getattr(chat, 'type', None)
    return "\n".join([
        "🆔 **Chat / Destination Info**",
        "",
        f"Title: **{title}**",
        f"Chat ID: `{getattr(chat, 'id', '')}`",
        f"Username: `{username}`",
        f"Type: `{chat_type}`",
        f"Topic ID: `{topic_id or 'None'}`",
    ])
#
# V16 UI OVERRIDES
#
def settings_home_text(user_id: int):
    s = get_user_settings(user_id)
    storage_mode = str(s.get("storage_mode", "telegram") or "telegram").strip().lower()
    storage_mode_label = _storage_mode_display(storage_mode)
    upload_mode = _upload_mode_display(s.get("telegram_upload_mode", s.get("upload_mode", "media"))).upper()
    messages_saved = get_index_user_count(user_id)
    file_rules = _safe_text(s.get("replace_words_file") or s.get("replace_words"))
    caption_rules = _safe_text(s.get("replace_words_caption") or s.get("replace_words"))

    lines = [
        f"**Settings for {APP_NAME}**",
        "",
        f"Messages Saved: **{messages_saved}**",
        f"Upload Mode: **{storage_mode_label}**",
        "",
    ]

    if storage_mode == "telegram":
        lines.extend([
            f"Custom Thumbnail is **{_exists_text(s.get('thumbnail_file_id'))}**",
            f"Telegram Upload Type is **{upload_mode}**",
            f"Upload Destination is **{_safe_text(s.get('upload_destination'))}**",
            f"Topic ID is **{_safe_text(s.get('topic_id'))}**",
        ])
    elif storage_mode == "gdrive":
        lines.extend([
            f"GDrive Token is **{_exists_text(s.get('gdrive_token_path'))}**",
            f"Folder ID is **{_safe_text(s.get('gdrive_folder_id'))}**",
        ])
        if s.get("gdrive_last_file_link"):
            lines.append(f"Last GDrive Link is **{_safe_text(s.get('gdrive_last_file_link'))}**")
        if not s.get("gdrive_token_path") or not s.get("gdrive_folder_id"):
            lines.extend([
                "",
                "Next Step: token.pickle aur Folder ID set karo.",
            ])
    elif storage_mode == "rclone":
        lines.extend([
            f"Rclone Config is **{_exists_text(s.get('rclone_config_path'))}**",
            f"Rclone Path is **{_safe_text(s.get('rclone_remote_path'))}**",
        ])
        if s.get("rclone_last_file_path"):
            lines.append(f"Last Rclone Target is **{_safe_text(s.get('rclone_last_file_path'))}**")
        if not s.get("rclone_config_path") or not s.get("rclone_remote_path"):
            lines.extend([
                "",
                "Next Step: rclone.conf aur Rclone Path set karo.",
            ])

    lines.extend([
        "",
        f"Prefix is **{_safe_text(s.get('prefix'))}**",
        f"Suffix is **{_safe_text(s.get('suffix'))}**",
        f"Metadata is **{_yes_no_enabled(s.get('metadata_enabled'))}**",
        f"Remove/Replace Words from File is **{file_rules}**",
        f"Remove/Replace Words from Caption is **{caption_rules}**",
        f"Auto Rename is **{_safe_text(s.get('auto_rename') or s.get('rename_template'))}**",
    ])
    return "\n".join(lines)


def upload_mode_text(user_id: int = 0):
    mode = "Media"
    if user_id:
        s = get_user_settings(user_id)
        mode = _upload_mode_display(s.get("telegram_upload_mode", s.get("upload_mode", "media")))
    return "\n".join([
        "**Telegram Send As**",
        "",
        f"Current Telegram upload type: **{mode}**",
        "",
        "Media mode me bot Telegram destination par media ki tarah send karega.",
        "",
        "Document mode me bot Telegram destination par document ki tarah send karega.",
        "",
        "Ye setting sirf Telegram Upload Mode ke liye apply hoti hai.",
        "Quick Toggle button se turant Media <-> Document switch kar sakte ho.",
    ])


def gdrive_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "**Google Drive Settings**",
        "",
        f"Folder ID: **{_safe_text(s.get('gdrive_folder_id'))}**",
        f"Token File: **{_exists_text(s.get('gdrive_token_path'))}**",
        f"Last Link: **{_safe_text(s.get('gdrive_last_file_link'))}**",
        "",
        "1. token.pickle bhejo",
        "2. Folder ID set karo",
        "3. Upload Mode ko Google Drive select karo",
    ])


def rclone_text(user_id: int):
    s = get_user_settings(user_id)
    return "\n".join([
        "**Rclone Settings**",
        "",
        f"Config File: **{_exists_text(s.get('rclone_config_path'))}**",
        f"Remote Path: **{_safe_text(s.get('rclone_remote_path'))}**",
        f"Last Target: **{_safe_text(s.get('rclone_last_file_path'))}**",
        "",
        "1. rclone.conf bhejo",
        "2. Remote path set karo",
        "3. Upload Mode ko Rclone select karo",
    ])


def replace_words_text(user_id: int):
    s = get_user_settings(user_id)
    return (
        "Remove / Replace Words\n\n"
        "Format example:\n"
        "old1:new1, old2:new2\n\n"
        "Sirf remove karna ho to:\n"
        "old1:, old2:\n\n"
        f"Current file rules: **{_safe_text(s.get('replace_words_file') or s.get('replace_words'))}**\n"
        f"Current caption rules: **{_safe_text(s.get('replace_words_caption') or s.get('replace_words'))}**\n\n"
        "File rules filename cleaning me use honge.\n"
        "Caption rules caption aur text cleaning me use honge.\n"
        "Send remove/replace rules. Timeout: 60 sec"
    )


def advanced_settings_text(user_id: int):
    s = get_user_settings(user_id)
    lines = [
        "**Advanced Settings**",
        "",
        f"Plan: **{_plan_display(user_id)}**",
        f"Upload Mode: **{_storage_mode_display(s.get('storage_mode', 'telegram'))}**",
        f"Authorized Login: **{'Connected' if has_user_session(user_id) else 'Not Connected'}**",
        f"Personal Bot: **{_exists_text(s.get('personal_bot_token'))}**",
        f"Route Template: **{_safe_text(s.get('route_template'), 'off')}**",
        f"Auto Index: **{_yes_no_enabled(is_index_mode(user_id))}**",
        f"Batch Mode: **{_yes_no_enabled(is_batch_mode(user_id))}**",
        f"Batch Limit: **{get_user_batch_limit(user_id)}**",
        f"Task Limit: **{get_user_task_limit(user_id)}**",
        "",
        "Upload Mode switching aur common save controls home screen par available hain.",
        "Yahan sirf advanced saver features aur helper pages dikhte hain.",
    ]
    return "\n".join(lines)
