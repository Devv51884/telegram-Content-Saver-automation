from config import APP_NAME, DEFAULT_PREMIUM_PLAN_NAME
from features.format_helpers import human_bytes, human_eta, human_speed
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
    get_caption_settings_for_mode,
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
        f"⚡ **{APP_NAME} {APP_VERSION_LABEL}**\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "📥 **High-Speed Restricted Content Saver**\n\n"
        "👋 Welcome! Kisi bhi Telegram post link ko seedha chat me bhejo:\n"
        "• Public / Private Channels (`t.me/...` & `t.me/c/...`)\n"
        "• Groups / Supergroups & Topics\n"
        "• Forwarding Allowed & Restricted Content\n\n"
        "Content automatically extract hokar aapke destination par deliver ho jayega.\n\n"
        "⚙️ **Quick Commands:**\n"
        "• `/start` — Main menu refresh karo\n"
        "• `/settings` — Personal settings & destination set karo\n"
        "• `/login` — Private restricted posts ke liye account login karo\n"
        "• `/my_tasks` — Active aur completed tasks dekho\n"
        "• `/help` — Full guide, rename tags & caption info\n"
        "• `/ping` — Bot response status check karo\n"
        "━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 **Tip:** Direct post link send karo aur transfer seamlessly start ho jayega!"
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
            "/supabase_status",
            "/storage_status",
            "/backup",
            "/restore latest",
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
    try:
        from storage import get_detailed_stats
        stats = get_detailed_stats()
        total_users = stats.get("total_users", 0)
        active_users = stats.get("active_users", 0)
        premium_users = stats.get("premium_users", 0)
        logged_in = stats.get("logged_in_users", 0)
        tasks = stats.get("task_counts", {})
        running_tasks = tasks.get("running", 0)
        completed_tasks = tasks.get("completed", 0)
    except Exception:
        total_users = active_users = premium_users = logged_in = running_tasks = completed_tasks = 0

    try:
        from features.plan_manager import get_all_plans, get_payment_config
        from features.payment_manager import get_pending_orders
        plans = get_all_plans()
        plans_count = len([p for p in plans.values() if p.get("is_active", True)])
        pending_orders = len(get_pending_orders())
        cfg = get_payment_config()
        upi_id = cfg.get("upi_id") or "Not set"
        paytm_ready = bool(cfg.get("paytm_mid") and cfg.get("paytm_key"))
        paytm_label = f"🟢 Connected (`{cfg.get('paytm_mid')}`)" if paytm_ready else "⚪ UPI Mode (Paytm not set)"
    except Exception:
        plans_count = pending_orders = 0
        upi_id = "Not set"
        paytm_label = "⚪ Not set"

    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "  🛡️  **CODE DEVIL ADMIN DASHBOARD**  🛡️\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "📊 **Users & Growth:**\n"
        f"  • Registered Users: **{total_users}**\n"
        f"  • Active (7 Days): **{active_users}**\n"
        f"  • Premium Subscribers: 💎 **{premium_users}**\n"
        f"  • User Telegram Logins: 🔐 **{logged_in}**\n\n"
        "💳 **Payment & Gateway Status:**\n"
        f"  • Gateway Engine: {paytm_label}\n"
        f"  • Active UPI ID: `{upi_id}`\n"
        f"  • Configured Plan Tiers: **{plans_count} Plans**\n"
        f"  • Pending Orders: ⏳ **{pending_orders} Waiting**\n\n"
        "⚡ **System Engine:**\n"
        f"  • Running Tasks: **{running_tasks}**\n"
        f"  • Completed Tasks: **{completed_tasks}**\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "💡 *Neeche diye interactive buttons se plans, payments, aur users manage karein:*"
    )


def admin_manage_plans_text(plans: dict):
    lines = [
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        "  ⚙️  **PLAN TIERS MANAGEMENT**  ⚙️",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        "Neeche aapke bot ke configured plan tiers hain. Kisi bhi plan par click karke uska price, limits, ya status change karein ya naya plan add karein:",
        "",
    ]
    for p_id, p in sorted(plans.items(), key=lambda x: int(x[1].get("price", 0))):
        status = "🟢 Active" if p.get("is_active", True) else "🔴 Disabled"
        lines.append(f"• **{p.get('name')}** (`{p_id}`): ₹{p.get('price')} ({p.get('duration_days')}d) — {status}")
    lines.append("")
    lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    lines.append("👉 *Select a plan to edit or tap '➕ Add New Plan'*")
    return "\n".join(lines)


def admin_plan_detail_text(plan: dict):
    features = plan.get("features", [])
    features_str = "\n".join([f"  • {f}" for f in features]) if features else "  • No custom features"
    status_str = "🟢 Active" if plan.get("is_active", True) else "🔴 Disabled"

    return (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"  💎 **PLAN: {plan.get('name', '').upper()}**\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"🆔 **Plan ID:** `{plan.get('id')}`\n"
        f"💰 **Price:** `₹{plan.get('price')}`\n"
        f"⏳ **Validity:** `{plan.get('duration_days')} Days`\n"
        f"📦 **Batch Limit:** `{plan.get('batch_limit')} Links`\n"
        f"⚡ **Parallel Tasks:** `{plan.get('task_limit')} Tasks`\n"
        f"☁️ **Storage Modes:** `{plan.get('storage_modes')}`\n"
        f"🔘 **Current Status:** {status_str}\n\n"
        f"**Plan Features:**\n{features_str}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 *Neeche diye buttons se is plan ko edit ya toggle karein:*"
    )


def admin_payment_gateway_text():
    from features.plan_manager import get_payment_config
    cfg = get_payment_config()
    paytm_ready = bool(cfg.get("paytm_mid") and cfg.get("paytm_key"))
    paytm_label = f"🟢 Connected (`{cfg.get('paytm_mid')}`)" if paytm_ready else "⚪ Disconnected (Using UPI Manual mode)"

    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "  💳 **PAYMENT GATEWAY CONFIG**  💳\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "⚡ **Paytm Business Auto-Verification:**\n"
        f"  • Status: {paytm_label}\n"
        f"  • Merchant ID (MID): `{cfg.get('paytm_mid') or 'Not Set'}`\n\n"
        "🏦 **UPI Settings (For QR Code):**\n"
        f"  • UPI ID: `{cfg.get('upi_id') or 'Not Set'}`\n"
        f"  • Payee Name: `{cfg.get('payee_name') or 'Code Devil'}`\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "📌 **Paytm Credentials Kaise Milegi?**\n"
        "1. business.paytm.com par account banayein.\n"
        "2. Left menu me **Developer Settings -> API Keys** par jayein.\n"
        "3. Wahan se **Merchant ID (MID)** aur **Merchant Key** copy karein.\n"
        "4. Neeche **'⚡ Setup Paytm MID & Key'** button dabayein ya command bhejein:\n"
        "   `/set_paytm YOUR_MID YOUR_KEY`"
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
    storage_mode = str(s.get("storage_mode", "telegram") or "telegram").strip().lower()
    caption_state = get_caption_settings_for_mode(s, storage_mode)
    current = caption_state.get("text") or "None"
    padding = s.get("caption_index_padding", 2)
    start = s.get("caption_index_start", 1)
    mode_note = "Telegram mode me ye sent caption banega."
    if storage_mode == "gdrive":
        mode_note = "Google Drive mode me ye file description ke roop me save hoga."
    elif storage_mode == "rclone":
        mode_note = "Rclone mode me ye `.caption.txt` sidecar file me save hoga."

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
        f"Current Mode: **{storage_mode.title()}**\n"
        f"Current Status: **{_yes_no_enabled(caption_state.get('enabled') and caption_state.get('text'))}**\n\n"
        f"Current caption:\n`{current}`\n\n"
        "Example caption:\n"
        "`<b>{index}</b> | {filename}`\n\n"
        f"{mode_note}\n\n"
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
        "❓ Command samajh nahi aayi.\n\n"
        "/help se command list dekho ya /settings kholo."
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
    return human_bytes(value or 0)


def _fmt_speed(value) -> str:
    return human_speed(value or 0)


def _fmt_eta(value) -> str:
    return human_eta(value or 0)


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
    has_session = has_user_session(user_id)
    login_status = "🟢 Connected" if has_session else "🔴 Not Connected (/login)"
    batch_status = "🟢 Active" if is_batch_mode(user_id) else "⚪ Off"
    storage_mode = str(s.get("storage_mode", "telegram") or "telegram").strip().lower()
    storage_title = _storage_mode_display(storage_mode)
    storage_icon = {"telegram": "📨", "gdrive": "☁️", "rclone": "🗂️"}.get(storage_mode, "📨")
    plan_name = _plan_display(user_id)
    plan_icon = "💎" if is_premium_user(user_id) else "🆓"

    upload_mode_raw = str(s.get("telegram_upload_mode", s.get("upload_mode", "media")) or "media").strip().lower()
    upload_type_str = "📄 Document (Original File)" if upload_mode_raw == "document" else "🎞️ Media (Streamable Video/Photo)"

    thumb_set = bool(s.get("thumbnail_file_id"))
    thumb_status = "🖼️ Custom Thumbnail Set" if thumb_set else "✖️ None (Original)"

    caption_on = bool(s.get("caption_enabled"))
    caption_status = "📝 Custom Caption ON" if caption_on else "✖️ Off (Original)"

    prefix_val = _safe_text(s.get("prefix"), "None")
    suffix_val = _safe_text(s.get("suffix"), "None")

    rename_val = s.get("auto_rename") or s.get("rename_template") or "Off"
    meta_on = bool(s.get("metadata_enabled"))
    meta_status = "🏷️ Active" if meta_on else "✖️ Off"

    has_replace = bool(s.get("replace_words") or s.get("replace_words_file") or s.get("replace_words_caption"))
    replace_status = "✂️ Clean Active" if has_replace else "✖️ None"

    dest_val = _safe_text(s.get("upload_destination"), "Not Set")
    topic_val = _safe_text(s.get("topic_id"), "General (Default)")

    lines = [
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        "  ⚙️  **BOT SETTINGS & DASHBOARD**  ⚙️",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        "👤 **Account Profile**",
        f"  • **Plan Tier:** {plan_icon} **{plan_name}**",
        f"  • **Telegram Auth:** {login_status}",
        f"  • **Task Concurrency:** `{get_user_task_limit(user_id)}` concurrent tasks",
        f"  • **Batch Limit:** `{get_user_batch_limit(user_id)}` links per job ({batch_status})",
        "",
        "🎯 **Target & Storage Destination**",
        f"  • **Active Engine:** {storage_icon} **{storage_title}**",
    ]

    if storage_mode == "telegram":
        lines.extend([
            f"  • **Upload Format:** {upload_type_str}",
            f"  • **Destination Chat:** `{dest_val}`",
            f"  • **Topic Thread ID:** `{topic_val}`",
        ])
    elif storage_mode == "gdrive":
        lines.extend([
            f"  • **Target Folder ID:** `{_safe_text(s.get('gdrive_folder_id'), 'Not Set')}`",
            f"  • **Credentials Pickle:** {_exists_text(s.get('gdrive_token_path'))}",
            f"  • **Last Uploaded Link:** `{_safe_text(s.get('gdrive_last_file_link'), 'None')}`",
        ])
    elif storage_mode == "rclone":
        lines.extend([
            f"  • **Rclone Remote:** `{_safe_text(s.get('rclone_remote_path'), 'Not Set')}`",
            f"  • **Config File:** {_exists_text(s.get('rclone_config_path'))}",
            f"  • **Last Remote Path:** `{_safe_text(s.get('rclone_last_file_path'), 'None')}`",
        ])

    lines.extend([
        "",
        "🎨 **Media & Output Formatting**",
        f"  • **Thumbnail:** {thumb_status}",
        f"  • **Caption Engine:** {caption_status}",
        f"  • **Filename Prefix:** `{prefix_val}`",
        f"  • **Filename Suffix:** `{suffix_val}`",
        f"  • **Auto Rename:** `{rename_val}`",
        f"  • **Media Metadata:** {meta_status}",
        f"  • **Word Replace Filter:** {replace_status}",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *Neeche diye interactive buttons se configuration change karein:*",
    ])
    return "\n".join(lines)

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


def advanced_settings_text(user_id: int):
    s = get_user_settings(user_id)
    login_str = "🟢 Connected" if has_user_session(user_id) else "🔴 Disconnected (/login)"
    bot_token = s.get("personal_bot_token")
    bot_name = s.get("personal_bot_username")
    personal_str = f"@{bot_name} ✅" if bot_token and bot_name else ("Set ✅" if bot_token else "✖️ None")
    route_str = _safe_text(s.get("route_template"), "Default (Off)")
    auto_idx = "🟢 Active" if is_index_mode(user_id) else "⚪ Off"
    batch_mode = "🟢 Active" if is_batch_mode(user_id) else "⚪ Off"

    lines = [
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
        "  ⚙️  **ADVANCED SETTINGS & ROUTING**  ⚙️",
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
        "",
        "👤 **Account & Auth Session**",
        f"  • **Plan Tier:** 💎 **{_plan_display(user_id)}**",
        f"  • **Storage Engine:** **{_storage_mode_display(s.get('storage_mode', 'telegram'))}**",
        f"  • **User Telegram Login:** {login_str}",
        f"  • **Dedicated Personal Bot:** {personal_str}",
        "",
        "⚡ **Automation & Routing**",
        f"  • **Delivery Route Template:** `{route_str}`",
        f"  • **Sequential Auto-Indexing:** {auto_idx}",
        f"  • **Multi-Link Batch Mode:** {batch_mode}",
        f"  • **User Batch Max Limit:** `{get_user_batch_limit(user_id)}` links",
        f"  • **User Task Max Limit:** `{get_user_task_limit(user_id)}` tasks",
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "💡 *Primary settings home screen par hain. Yahan se personal bot, routing templates aur session management configure karein.*",
    ]
    return "\n".join(lines)


def buy_plans_text():
    return (
        "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        "  💎 **UPGRADE TO PREMIUM PLANS** 💎\n"
        "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        "Apne requirement ke mutabik best plan select karein:\n\n"
        "🥉 **Silver Plan** (₹99 / 30 Days)\n"
        "  • 50 Batch Links Limit\n"
        "  • 3 Simultaneous Tasks\n"
        "  • Fast Speed & Custom Prefix/Caption\n\n"
        "🥈 **Gold Plan** (₹199 / 30 Days)\n"
        "  • 200 Batch Links Limit\n"
        "  • 5 Simultaneous Tasks\n"
        "  • Google Drive Direct Upload\n"
        "  • Custom Thumbnails & Auto Rename\n\n"
        "🥇 **Diamond VIP** (₹499 / 30 Days)\n"
        "  • 500 Mega Batch Limit\n"
        "  • 8 Parallel Tasks | All Storage Access\n"
        "  • VIP Priority Queue\n\n"
        "👑 **Lifetime Elite** (₹999 / Permanent)\n"
        "  • 1000 Mega Batch Limit | 10 Tasks\n"
        "  • Full Cloud Access | 10 Years Validity\n\n"
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        "👇 *Neeche diye kisi bhi plan par click karein:*"
    )


def plan_duration_selection_text(plan: dict, durations: list[dict] | None = None):
    p_name = plan.get("name") or "Premium Plan"
    batch_limit = plan.get("batch_limit", 50)
    task_limit = plan.get("task_limit", 3)
    storage = str(plan.get("storage_modes", "telegram,personal_bot")).replace(",", ", ")
    features = plan.get("features") or []
    if features:
        feat_lines = "\n".join([f"  • {f}" for f in features])
    else:
        feat_lines = f"  • {batch_limit} Batch Links Limit\n  • {task_limit} Simultaneous Tasks\n  • Storage: {storage}"

    return (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"  💎 **{p_name.upper()}** 💎\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"⚡ **Plan Specifications:**\n"
        f"  • 📦 **Batch Limit:** `{batch_limit}` Links\n"
        f"  • 🚀 **Parallel Tasks:** `{task_limit}` Simultaneous\n"
        f"  • ☁️ **Storage Modes:** `{storage}`\n\n"
        f"✨ **Features Included:**\n{feat_lines}\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 **Apni requirement ke anusaar plan validity (duration) chunein:**"
    )


def order_payment_text(order: dict, upi_id: str):
    import time
    time_left = max(0, int(order.get("expires_at", 0)) - int(time.time()))
    mins, secs = divmod(time_left, 60)
    dur_label = order.get("duration_label") or f"{order.get('duration_days', 30)} Days"
    return (
        f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
        f"  💳 **PAYMENT QR & INVOICE** 💳\n"
        f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
        f"📦 **Plan:** `{order.get('plan_name')}`\n"
        f"⏳ **Validity:** `{dur_label}`\n"
        f"💰 **Amount:** `₹{order.get('amount')}`\n"
        f"🆔 **Order ID:** `{order.get('order_id')}`\n"
        f"⏱️ **Timer:** `{mins:02d}:{secs:02d}` (5 Minutes)\n"
        f"🏦 **UPI ID:** `{upi_id}` *(Tap to copy)*\n\n"
        f"━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
        f"**Payment Instructions:**\n"
        f"1. Upar diye gaye QR Code ko kisi bhi UPI app (Paytm / PhonePe / GPay) se scan karein.\n"
        f"2. Exact **₹{order.get('amount')}** pay karein.\n"
        f"3. Pay karne ke baad **'🔄 Check Payment Status'** dabayein.\n"
        f"4. Ya phir **'✅ Submit 12-Digit UTR'** dabakar apna UTR submit karein.\n\n"
        f"⚠️ *Payment 5 minute ke andar complete karein.*"
    )

