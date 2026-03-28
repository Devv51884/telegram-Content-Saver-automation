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
        "/plan - Roadmap dekho\n"
        "/terms - Rules dekho\n"
        "/settings - Personal settings kholo\n"
        "/login - Telegram account login karo\n"
        "/login_status - Login status dekho\n"
        "/logout - Saved login remove karo\n"
        "/my_tasks - Running/completed tasks dekho\n"
        "/cancel - Current input cancel karo\n\n"
        "**Highlights:**\n"
        "Cleaner task destination display + stronger task schema sync + better retry-friendly wording + premium-ready settings flow."
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
        "/login - Account login start karne ke liye\n"
        "/login_status - Saved session status dekhne ke liye\n"
        "/logout - Saved session remove karne ke liye\n"
        "/my_tasks - Task history dekhne ke liye\n"
        "/cancel - Current text input ya login flow cancel karne ke liye\n\n"
        "**Admin / Index Commands**\n"
        "/stats\n"
        "/users\n"
        "/ban user_id\n"
        "/unban user_id\n"
        "/broadcast your message\n"
        "/index_id - auto indexing on karo\n"
        "/stop_index - indexing off karo\n"
        "/index_stats - index stats dekho\n\n"
        "**Caption Variables**\n"
        "{filename}, {size}, {duration}, {quality}, {language}, {subtitle}, {index}\n\n"
        "**Rename Variables**\n"
        "{filename}, {index}\n\n"
        "**Batch Use**\n"
        "Batch ON karke multiple Telegram links ek saath bhej sakte ho.\n\n"
        "**Supported Batch Formats**\n"
        "1. Single link:\n"
        "   https://t.me/channel/25\n\n"
        "2. Multiple lines:\n"
        "   https://t.me/channel/25\n"
        "   https://t.me/channel/26\n\n"
        "3. Range format:\n"
        "   https://t.me/Code_Devil/39-69\n"
        "   https://t.me/c/2102477857/340-360\n\n"
        "4. Space separated links bhi bhej sakte ho.\n\n"
        "**Upload Mode**\n"
        "Media mode me bot photo/video/audio ko media ki tarah bhejega.\n"
        "Document mode me bot almost sab files ko document ki tarah bhejega.\n\n"
        "**Premium**\n"
        "Premium users ko zyada batch/task limits aur future advanced tools mil sakte hain."
    )


def plan_text():
    return (
        "🛣️ **Code Devil Bot Roadmap**\n\n"
        "✅ V1 - Working base bot\n"
        "✅ V2 - Settings panel basic version\n"
        "✅ V3 - Admin controls basic version\n"
        "✅ V4 - Advanced settings + indexing\n"
        "✅ V5 - Auto index + destination upload + log channel\n"
        "✅ V6 - Login/session system + realtime task processing\n"
        "✅ V7 - Dynamic login/logout UI + advanced caption + advanced auto rename\n"
        "✅ V8 - Batch mode + strict force subscribe + /start index reset + range format batch links\n"
        "✅ V9 - Dynamic media/document upload mode + improved progress system + cleaner settings UI\n"
        "✅ V10 - Premium-ready system + better UI/UX + direct public copy workflow base\n"
        "✅ V11 - Hybrid database support + upgraded admin panel + cleaner premium flow + stronger retry/batch experience\n"
        "✅ V12 - Task schema sync + better destination display + more stable task text flow\n"
        "🔜 Next - analytics + payments + plan-based advanced controls"
    )


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
        f"Plan Name: **{DEFAULT_PREMIUM_PLAN_NAME if is_premium_user(user_id) else 'Free'}**\n"
        f"Expiry: **{expiry}**\n"
        f"Batch Limit: **{batch_limit}**\n"
        f"Task Limit: **{task_limit}**\n\n"
        "Premium users ko higher limits aur future advanced features mil sakte hain."
    )


def admin_panel_text():
    return (
        "🛡 **Admin Panel**\n\n"
        "Yahan se admin-related controls, premium management aur broadcast/help actions access kiye ja sakte hain.\n\n"
        "**Useful Commands:**\n"
        "/stats\n"
        "/users\n"
        "/ban user_id\n"
        "/unban user_id\n"
        "/broadcast your message\n\n"
        "**Premium command examples:**\n"
        "/add_premium user_id 30d\n"
        "/remove_premium user_id\n"
        "/premium_status user_id"
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
    upload_mode = _upload_mode_display(s.get("upload_mode", "media"))

    return (
        f"⚙️ **Settings for User**\n\n"
        f"Plan: **{_premium_display(user_id)}**\n"
        f"Upload Mode: **{upload_mode}**\n"
        f"Custom Thumbnail: **{_exists_text(s.get('thumbnail_file_id'))}**\n"
        f"Caption: **{'Enabled ✅' if s.get('caption_enabled') else 'Disabled ❌'}**\n"
        f"Prefix: **{_safe_text(s.get('prefix'))}**\n"
        f"Suffix: **{_safe_text(s.get('suffix'))}**\n"
        f"Auto Rename: **{_safe_text(s.get('auto_rename'))}**\n"
        f"Rename Template: **{_safe_text(s.get('rename_template'))}**\n"
        f"Filename Prefix: **{_safe_text(s.get('filename_prefix'))}**\n"
        f"Filename Suffix: **{_safe_text(s.get('filename_suffix'))}**\n"
        f"Metadata: **{'Enabled ✅' if s.get('metadata_enabled') else 'Disabled ❌'}**\n"
        f"Upload Destination: **{_safe_text(s.get('upload_destination'))}**\n"
        f"Topic ID: **{_safe_text(s.get('topic_id'))}**\n"
        f"Replace Words: **{_safe_text(s.get('replace_words'))}**\n"
        f"Index Mode: **{_yes_no_enabled(is_index_mode(user_id))}**\n"
        f"Batch Mode: **{batch_status}**\n"
        f"Authorized Login: **{login_status}**\n"
        f"Batch Limit: **{get_user_batch_limit(user_id)}**\n"
        f"Task Limit: **{get_user_task_limit(user_id)}**\n\n"
        "Niche buttons se sab setting manage kar sakte ho."
    )


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
    if progress_bar_text:
        try:
            lines.append(f"**Transfer:** `{progress_bar_text}` **{float(progress_percent or 0):.2f}%**")
        except Exception:
            lines.append(f"**Transfer:** `{progress_bar_text}`")
    if processed:
        lines.append(f"**Processed:** `{processed}`")
    if speed:
        lines.append(f"**Speed:** `{speed}`")
    if eta:
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
