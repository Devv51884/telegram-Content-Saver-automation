from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    MAIN_CHANNEL,
    UPDATES_CHANNEL,
    PLAYLIST_LINK,
    WHATSAPP_CHANNEL,
    YOUTUBE_CHANNEL,
    JOIN_LINK,
)
from features.keyboard_helpers import (
    premium_label,
    safe_url,
    storage_mode_label,
    task_status_badge,
    upload_mode_button_label,
    yes_no_label,
)


def _safe_url(value: str, fallback: str = "https://t.me/"):
    return safe_url(value, fallback)


def _upload_mode_button_label(mode: str) -> str:
    return upload_mode_button_label(mode)


def _premium_label(is_premium: bool) -> str:
    return premium_label(is_premium)


def _yes_no_label(enabled: bool, on_text: str, off_text: str) -> str:
    return yes_no_label(enabled, on_text, off_text)


def _task_status_badge(status: str) -> str:
    return task_status_badge(status)
def join_required_buttons():
    join_url = _safe_url(JOIN_LINK or MAIN_CHANNEL, "https://t.me/")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Pehle Channel Join Karo", url=join_url)],
        [InlineKeyboardButton("✅ Join Kar Liya", callback_data="check_join_again")],
    ])


def start_buttons(has_session: bool = False, is_admin: bool = False, is_premium: bool = False):
    auth_button = (
        InlineKeyboardButton("🚪 Logout", callback_data="do_logout")
        if has_session
        else InlineKeyboardButton("🔐 Login", callback_data="show_login_info")
    )

    rows = [
        [
            InlineKeyboardButton("📢 Main Channel", url=_safe_url(MAIN_CHANNEL)),
            InlineKeyboardButton("🛠 Updates", url=_safe_url(UPDATES_CHANNEL)),
        ],
        [
            InlineKeyboardButton("📚 Playlist", url=_safe_url(PLAYLIST_LINK)),
            InlineKeyboardButton("▶️ YouTube", url=_safe_url(YOUTUBE_CHANNEL)),
        ],
        [
            InlineKeyboardButton("💬 WhatsApp", url=_safe_url(WHATSAPP_CHANNEL)),
        ],
        [
            InlineKeyboardButton(_premium_label(is_premium), callback_data="show_premium_info"),
            InlineKeyboardButton("💎 Buy Premium", callback_data="buy_plans_menu"),
        ],
    ]

    if is_admin:
        rows.append([
            InlineKeyboardButton("🛡 Admin Panel", callback_data="show_admin_panel")
        ])

    rows.append([
        auth_button,
        InlineKeyboardButton("⚙️ Settings", callback_data="show_settings_home"),
    ])

    return InlineKeyboardMarkup(rows)


# ---------- SETTINGS HOME ----------
def settings_home_buttons(
    marks: dict,
    has_session: bool = False,
    upload_mode: str = "media",
    is_admin: bool = False,
    is_premium: bool = False,
    storage_mode: str = "telegram",
):
    storage_mode = str(storage_mode or "telegram").strip().lower()
    current_storage_label = _storage_mode_label(storage_mode)
    current_upload_mode = str(upload_mode or "media").strip().lower()
    upload_mode_btn_text = "Mode: Document 📄" if current_upload_mode == "document" else "Mode: Media 🎞️"

    # Status indicators (never show '?')
    m_thumb = "✅" if marks.get("thumbnail") == "✅" else "❌"
    m_cap = "✅" if marks.get("caption") == "✅" else "❌"
    m_dest = "✅" if marks.get("destination") == "✅" else "❌"
    m_topic = "✅" if marks.get("topic_id") == "✅" else "❌"
    m_pref = "✅" if marks.get("prefix") == "✅" else "❌"
    m_suff = "✅" if marks.get("suffix") == "✅" else "❌"
    m_rename = "✅" if marks.get("auto_rename") == "✅" else "❌"
    m_meta = "✅" if marks.get("metadata") == "✅" else "❌"
    m_repl = "✅" if marks.get("replace_words") == "✅" else "❌"

    rows = [
        [InlineKeyboardButton(f"📦 Storage Engine: {current_storage_label} 🔄", callback_data="cycle_storage_mode")],
    ]

    if storage_mode == "telegram":
        rows.extend([
            [
                InlineKeyboardButton(f"🔁 {upload_mode_btn_text}", callback_data="toggle_upload_mode"),
                InlineKeyboardButton(f"📢 Target Chat: {m_dest}", callback_data="show_destination"),
            ],
            [
                InlineKeyboardButton(f"🖼️ Thumbnail: {m_thumb}", callback_data="show_thumbnail"),
                InlineKeyboardButton(f"📝 Caption: {m_cap}", callback_data="show_caption"),
            ],
            [InlineKeyboardButton(f"📌 Topic Thread ID: {m_topic}", callback_data="show_topic_id")],
        ])
    elif storage_mode == "gdrive":
        m_token = "✅" if marks.get("gdrive_token") == "✅" else "❌"
        m_folder = "✅" if marks.get("gdrive_folder") == "✅" else "❌"
        rows.extend([
            [
                InlineKeyboardButton(f"🔑 token.pickle: {m_token}", callback_data="set_gdrive_token_file"),
                InlineKeyboardButton(f"📁 Folder ID: {m_folder}", callback_data="set_gdrive_folder_id"),
            ],
            [InlineKeyboardButton(f"📝 Set Caption: {m_cap}", callback_data="show_caption")],
        ])
    elif storage_mode == "rclone":
        m_rc_cfg = "✅" if marks.get("rclone_config") == "✅" else "❌"
        m_rc_path = "✅" if marks.get("rclone_path") == "✅" else "❌"
        rows.extend([
            [
                InlineKeyboardButton(f"📄 Rclone Config: {m_rc_cfg}", callback_data="set_rclone_config_file"),
                InlineKeyboardButton(f"🗂️ Remote Path: {m_rc_path}", callback_data="set_rclone_remote_path"),
            ],
            [InlineKeyboardButton(f"📝 Set Caption: {m_cap}", callback_data="show_caption")],
        ])

    rows.extend([
        [
            InlineKeyboardButton(f"🏷️ Prefix: {m_pref}", callback_data="show_prefix"),
            InlineKeyboardButton(f"🏷️ Suffix: {m_suff}", callback_data="show_suffix"),
        ],
        [
            InlineKeyboardButton(f"✍️ Auto Rename: {m_rename}", callback_data="show_auto_rename"),
            InlineKeyboardButton(f"🏷️ Metadata: {m_meta}", callback_data="show_metadata"),
        ],
        [InlineKeyboardButton(f"✂️ Remove / Replace Words: {m_repl}", callback_data="show_replace_words")],
        [
            InlineKeyboardButton("⚙️ Advanced Options", callback_data="show_advanced_settings"),
            InlineKeyboardButton("🔄 Reset Defaults", callback_data="reset_all_settings"),
        ],
    ])

    if is_admin:
        rows.append([InlineKeyboardButton("👑 Admin Control Panel", callback_data="show_admin_panel")])

    rows.append([InlineKeyboardButton("❌ Close Menu", callback_data="close_settings")])
    return InlineKeyboardMarkup(rows)


# ---------- ADMIN / PREMIUM ----------


def premium_info_buttons(is_admin: bool = False):
    rows = [
        [InlineKeyboardButton("💳 Buy / Upgrade Plan", callback_data="buy_plans_menu")],
    ]

    if is_admin:
        rows.append([InlineKeyboardButton("💎 Premium Admin Help", callback_data="admin_premium_help")])

    rows.append([
        InlineKeyboardButton("📈 My Limits", callback_data="show_user_limits"),
        InlineKeyboardButton("🪪 My Plan", callback_data="show_premium_info"),
    ])
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
        InlineKeyboardButton("❌ Close", callback_data="close_settings"),
    ])

    return InlineKeyboardMarkup(rows)


def admin_users_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🆕 Recent", callback_data="admin_recent_users"),
            InlineKeyboardButton("🔎 Search", callback_data="admin_user_search_help"),
        ],
        [
            InlineKeyboardButton("💎 Premium List", callback_data="admin_premium_list"),
            InlineKeyboardButton("📊 User Stats", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_admin_panel"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def admin_premium_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("➕ Add Premium", callback_data="admin_add_premium_help"),
            InlineKeyboardButton("➖ Remove Premium", callback_data="admin_remove_premium_help"),
        ],
        [
            InlineKeyboardButton("📋 Premium List", callback_data="admin_premium_list"),
            InlineKeyboardButton("⏳ Check Expiry", callback_data="admin_check_premium_help"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_admin_panel"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def admin_broadcast_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📝 Text Guide", callback_data="admin_broadcast_help"),
            InlineKeyboardButton("📦 Media Guide", callback_data="admin_broadcast_media_help"),
        ],
        [
            InlineKeyboardButton("📊 Broadcast Stats", callback_data="admin_broadcast_stats"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_admin_panel"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def admin_task_debug_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("🧪 Task Debug Help", callback_data="admin_task_debug_help"),
            InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_admin_panel"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


# ---------- SHARED NAV ----------
def submenu_nav(back: str = "show_settings_home"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Back", callback_data=back),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


# ---------- SETTINGS SUB MENUS ----------
def thumbnail_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ Thumbnail On", "❌ Thumbnail Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_thumbnail_enabled")],
        [InlineKeyboardButton("📷 Set Thumbnail", callback_data="set_thumbnail_photo")],
        [InlineKeyboardButton("🗑 Remove Thumbnail", callback_data="remove_thumbnail")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def caption_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ Caption On", "❌ Caption Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_caption_enabled")],
        [InlineKeyboardButton("✍️ Set Caption", callback_data="set_caption_text")],
        [InlineKeyboardButton("🔢 Index Format", callback_data="show_caption_index_settings")],
        [InlineKeyboardButton("🗑 Remove Caption", callback_data="remove_caption")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def caption_index_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ {index} On", "❌ {index} Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_caption_index_enabled")],
        [InlineKeyboardButton("🔢 Set Padding", callback_data="set_caption_index_padding")],
        [InlineKeyboardButton("🚀 Set Start", callback_data="set_caption_index_start")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_caption"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def simple_set_buttons(set_cb: str, remove_cb: str = "", back: str = "show_settings_home"):
    rows = [[InlineKeyboardButton("✍️ Set Value", callback_data=set_cb)]]

    if remove_cb:
        rows.append([InlineKeyboardButton("🗑 Remove", callback_data=remove_cb)])

    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data=back),
        InlineKeyboardButton("❌ Close", callback_data="close_settings"),
    ])

    return InlineKeyboardMarkup(rows)


def metadata_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ Metadata On", "❌ Metadata Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_metadata_enabled")],
        [
            InlineKeyboardButton("🎬 Video Title", callback_data="show_metadata_video_title"),
            InlineKeyboardButton("👤 Video Author", callback_data="show_metadata_video_author"),
        ],
        [
            InlineKeyboardButton("🎵 Audio Title", callback_data="show_metadata_audio_title"),
            InlineKeyboardButton("💬 Subtitle Title", callback_data="show_metadata_subtitle_title"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def metadata_field_buttons(set_cb: str, remove_cb: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✍️ Set Value", callback_data=set_cb)],
        [InlineKeyboardButton("🗑 Remove", callback_data=remove_cb)],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_metadata"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def index_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ Index ON", "❌ Index OFF")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_index_mode")],
        [InlineKeyboardButton("📊 Index Stats", callback_data="show_index_stats")],
        [InlineKeyboardButton("ℹ️ Info", callback_data="show_index_info")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def auto_rename_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ Auto Rename On", "❌ Auto Rename Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_auto_rename_enabled")],
        [InlineKeyboardButton("✍️ Simple Rename", callback_data="set_auto_rename")],
        [InlineKeyboardButton("🧩 Rename Template", callback_data="set_rename_template")],
        [
            InlineKeyboardButton("🏷 Filename Prefix", callback_data="set_filename_prefix"),
            InlineKeyboardButton("🔖 Filename Suffix", callback_data="set_filename_suffix"),
        ],
        [InlineKeyboardButton("🔢 Filename Index", callback_data="show_filename_index_settings")],
        [InlineKeyboardButton("🗑 Remove Rename", callback_data="remove_auto_rename")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def filename_index_buttons(enabled: bool):
    label = _yes_no_label(enabled, "✅ Filename {index} On", "❌ Filename {index} Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_filename_index_enabled")],
        [InlineKeyboardButton("🔢 Set Padding", callback_data="set_filename_index_padding")],
        [InlineKeyboardButton("🚀 Set Start", callback_data="set_filename_index_start")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_auto_rename"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def destination_buttons(has_destination: bool = False, has_topic: bool = False):
    dest_label = "✅ Destination Set" if has_destination else "❌ Destination Not Set"
    topic_label = "✅ Topic Set" if has_topic else "❌ Topic Not Set"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(dest_label, callback_data="show_destination")],
        [InlineKeyboardButton("📌 Set Destination", callback_data="set_destination")],
        [InlineKeyboardButton(topic_label, callback_data="show_topic_id")],
        [InlineKeyboardButton("🧵 Set Topic ID", callback_data="set_topic_id")],
        [
            InlineKeyboardButton("🧹 Clear Topic", callback_data="clear_topic_id"),
            InlineKeyboardButton("🗑 Clear Destination", callback_data="clear_destination"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def upload_mode_buttons(upload_mode: str = "media"):
    current = _upload_mode_button_label(upload_mode)
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Current: {current}", callback_data="noop")],
        [
            InlineKeyboardButton("🎞 Media", callback_data="set_upload_mode:media"),
            InlineKeyboardButton("📄 Document", callback_data="set_upload_mode:document"),
        ],
        [InlineKeyboardButton("🔁 Quick Toggle", callback_data="toggle_upload_mode")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


# ---------- LOGIN / TASKS ----------
def login_buttons(has_session: bool = False):
    if has_session:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📊 Login Status", callback_data="show_login_status")],
            [InlineKeyboardButton("🚪 Logout", callback_data="do_logout")],
            [
                InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
                InlineKeyboardButton("❌ Close", callback_data="close_settings"),
            ],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔐 Start Login", callback_data="start_login_flow")],
        [InlineKeyboardButton("📘 Login Guide", callback_data="show_login_info")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def task_buttons(task_id: str, done: bool = False, status: str = "", can_debug: bool = False):
    status_key = str(status or "").strip().lower()
    is_final = bool(done or status_key in {"completed", "failed", "cancelled"})
    if is_final:
        rows = [
            [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
        ]
        if can_debug:
            rows.append([InlineKeyboardButton("🧪 Details", callback_data=f"task_debug:{task_id}")])
        rows.append([InlineKeyboardButton("❌ Close", callback_data="close_settings")])
        return InlineKeyboardMarkup(rows)

    rows = []
    if status:
        rows.append([InlineKeyboardButton(_task_status_badge(status), callback_data="noop")])
    rows.extend([
        [
            InlineKeyboardButton("♻️ Refresh", callback_data=f"task_refresh:{task_id}"),
            InlineKeyboardButton("🛑 Cancel", callback_data=f"task_cancel:{task_id}"),
        ],
        [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
    ])
    if can_debug:
        rows.append([InlineKeyboardButton("🧪 Details", callback_data=f"task_debug:{task_id}")])
    return InlineKeyboardMarkup(rows)
def my_tasks_buttons(include_cleanup: bool = False):
    rows = [
        [InlineKeyboardButton("♻️ Refresh", callback_data="show_my_tasks")],
    ]
    if include_cleanup:
        rows.append([InlineKeyboardButton("🧹 Clear Finished", callback_data="clear_finished_tasks")])
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
        InlineKeyboardButton("❌ Close", callback_data="close_settings"),
    ])
    return InlineKeyboardMarkup(rows)


def task_debug_buttons(task_id: str):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♻️ Refresh Task", callback_data=f"task_refresh:{task_id}")],
        [InlineKeyboardButton("🧪 Raw Debug", callback_data=f"task_debug:{task_id}")],
        [InlineKeyboardButton("🛑 Cancel", callback_data=f"task_cancel:{task_id}")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_my_tasks"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


# ---------- BATCH ----------
def batch_buttons(enabled: bool, is_premium: bool = False):
    label = _yes_no_label(enabled, "✅ Batch ON", "❌ Batch OFF")
    tier = "💎 Premium Batch" if is_premium else "🆓 Free Batch"

    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_batch_mode")],
        [InlineKeyboardButton(tier, callback_data="show_premium_info")],
        [InlineKeyboardButton("📥 Set Batch Links", callback_data="set_batch_links")],
        [
            InlineKeyboardButton("▶️ Start Batch", callback_data="start_batch_now"),
            InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks"),
        ],
        [
            InlineKeyboardButton("🗑 Clear Batch", callback_data="clear_batch_links"),
            InlineKeyboardButton("ℹ️ Batch Info", callback_data="show_batch_info"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def batch_live_board_buttons(batch_key: str, current_task_id: str = "", done: bool = False, status: str = ""):
    status_key = str(status or "").strip().lower()
    if done or status_key in {"completed", "failed", "cancelled"}:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
            [InlineKeyboardButton("❌ Close", callback_data=f"batch_close:{batch_key}")],
        ])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("♻️ Refresh", callback_data=f"batch_refresh:{batch_key}"),
            InlineKeyboardButton("🛑 Cancel Current", callback_data=f"batch_cancel_current:{batch_key}"),
        ],
        [InlineKeyboardButton("🧹 Cancel All", callback_data=f"batch_cancel_all:{batch_key}")],
        [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
        [InlineKeyboardButton("❌ Close", callback_data=f"batch_close:{batch_key}")],
    ])


# =========================================================
# V13/V14/V15 OVERRIDES
# =========================================================
def _storage_mode_label(mode: str) -> str:
    return storage_mode_label(mode)


def admin_panel_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Live Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 All Users", callback_data="show_admin_users"),
        ],
        [
            InlineKeyboardButton("⚙️ Manage Plans", callback_data="admin_manage_plans"),
            InlineKeyboardButton("💳 Payment Gateway", callback_data="admin_payment_settings"),
        ],
        [
            InlineKeyboardButton("⏳ Pending Orders", callback_data="admin_pending_orders"),
            InlineKeyboardButton("💎 Premium Users", callback_data="admin_premium_help"),
        ],
        [
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast_help"),
            InlineKeyboardButton("🧪 Task Debug", callback_data="admin_task_debug_help"),
        ],
        [
            InlineKeyboardButton("🔄 Refresh Dashboard", callback_data="show_admin_panel"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def gdrive_buttons(has_token: bool = False, has_folder: bool = False):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Token Set" if has_token else "❌ Token Missing", callback_data="noop"), InlineKeyboardButton("✅ Folder Set" if has_folder else "❌ Folder Missing", callback_data="noop")],
        [InlineKeyboardButton("📎 Set token.pickle", callback_data="set_gdrive_token_file"), InlineKeyboardButton("📁 Set Folder ID", callback_data="set_gdrive_folder_id")],
        [InlineKeyboardButton("🧪 Validate GDrive", callback_data="validate_gdrive_settings"), InlineKeyboardButton("🗑 Clear GDrive", callback_data="clear_gdrive_settings")],
        [InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"), InlineKeyboardButton("❌ Close", callback_data="close_settings")],
    ])


def rclone_buttons(has_config: bool = False, has_path: bool = False):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Config Set" if has_config else "❌ Config Missing", callback_data="noop"), InlineKeyboardButton("✅ Path Set" if has_path else "❌ Path Missing", callback_data="noop")],
        [InlineKeyboardButton("📎 Set rclone.conf", callback_data="set_rclone_config_file"), InlineKeyboardButton("🗂 Set Remote Path", callback_data="set_rclone_remote_path")],
        [InlineKeyboardButton("🧪 Validate Rclone", callback_data="validate_rclone_settings"), InlineKeyboardButton("🗑 Clear Rclone", callback_data="clear_rclone_settings")],
        [InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"), InlineKeyboardButton("❌ Close", callback_data="close_settings")],
    ])


def personal_bot_buttons(has_bot: bool = False, personal_enabled: bool = False):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✅ Personal Bot Set" if has_bot else "❌ Bot Missing", callback_data="noop")],
        [InlineKeyboardButton("🤖 Set / Update Bot", callback_data="set_personal_bot_token"), InlineKeyboardButton("🧪 Validate Bot", callback_data="validate_personal_bot")],
        [InlineKeyboardButton(("✅ Using Personal Bot" if personal_enabled else "❌ Using Main Bot"), callback_data="toggle_personal_bot_mode"), InlineKeyboardButton("🗑 Remove Bot", callback_data="remove_personal_bot")],
        [InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"), InlineKeyboardButton("❌ Close", callback_data="close_settings")],
    ])


def route_template_buttons(current: str = "off"):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"Current: {str(current or 'off').replace('_', ' ').title()}", callback_data="noop")],
        [InlineKeyboardButton("Off", callback_data="set_route_template:off"), InlineKeyboardButton("Smart", callback_data="set_route_template:smart")],
        [InlineKeyboardButton("Docs→GDrive", callback_data="set_route_template:docs_to_gdrive"), InlineKeyboardButton("Media→Telegram", callback_data="set_route_template:media_to_telegram")],
        [InlineKeyboardButton("Archives→Rclone", callback_data="set_route_template:archives_to_rclone")],
        [InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"), InlineKeyboardButton("❌ Close", callback_data="close_settings")],
    ])
# =========================================================
# V16 UI OVERRIDES
# =========================================================


def advanced_settings_buttons(
    has_session: bool = False,
    has_personal_bot: bool = False,
    is_admin: bool = False,
    storage_mode: str = "telegram",
):
    auth_text = "🔓 Logout Account" if has_session else "🔐 Login Account (/login)"
    auth_callback = "do_logout" if has_session else "show_login_info"
    storage_mode = str(storage_mode or "telegram").strip().lower()
    rows = [
        [
            InlineKeyboardButton(auth_text, callback_data=auth_callback),
            InlineKeyboardButton("📡 Session Status", callback_data="show_login_status"),
        ],
        [
            InlineKeyboardButton("🤖 Personal Bot Token", callback_data="show_personal_bot_settings"),
            InlineKeyboardButton("🔀 Route Templates", callback_data="show_route_template"),
        ],
        [
            InlineKeyboardButton("🔢 Auto Indexing", callback_data="show_index_settings"),
            InlineKeyboardButton("📦 Batch Mode", callback_data="show_batch_settings"),
        ],
        [InlineKeyboardButton("💎 Premium Subscription Info", callback_data="show_premium_info")],
        [
            InlineKeyboardButton("⬅️ Back to Settings", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ]
    if storage_mode == "gdrive":
        rows.insert(-2, [InlineKeyboardButton("☁️ Google Drive Tools", callback_data="show_gdrive_settings")])
    elif storage_mode == "rclone":
        rows.insert(-2, [InlineKeyboardButton("🗂️ Rclone Remote Tools", callback_data="show_rclone_settings")])
    if is_admin:
        rows.insert(-1, [InlineKeyboardButton("👑 Admin Control Panel", callback_data="show_admin_panel")])
    return InlineKeyboardMarkup(rows)


def replace_words_buttons(file_enabled: bool = False, caption_enabled: bool | None = None):
    if caption_enabled is None:
        caption_enabled = file_enabled
    file_label = "File Rules On" if file_enabled else "File Rules Off"
    caption_label = "Caption Rules On" if caption_enabled else "Caption Rules Off"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(file_label, callback_data="noop"),
            InlineKeyboardButton(caption_label, callback_data="noop"),
        ],
        [
            InlineKeyboardButton("Set File Rules", callback_data="set_replace_words_file"),
            InlineKeyboardButton("Set Caption Rules", callback_data="set_replace_words_caption"),
        ],
        [
            InlineKeyboardButton("Clear File Rules", callback_data="clear_replace_words_file"),
            InlineKeyboardButton("Clear Caption Rules", callback_data="clear_replace_words_caption"),
        ],
        [InlineKeyboardButton("Clear All", callback_data="clear_replace_words")],
        [InlineKeyboardButton("Back", callback_data="show_settings_home"), InlineKeyboardButton("Close", callback_data="close_settings")],
    ])


def storage_mode_buttons(current_mode: str = "telegram", allowed_modes: list[str] | None = None):
    normalized_modes = []
    for mode in (allowed_modes or ["telegram", "gdrive", "rclone"]):
        mode = str(mode or "").strip().lower()
        if mode in {"telegram", "gdrive", "rclone"} and mode not in normalized_modes:
            normalized_modes.append(mode)
    if not normalized_modes:
        normalized_modes = ["telegram"]

    labels = {
        "telegram": "Telegram",
        "gdrive": "Google Drive",
        "rclone": "Rclone",
    }
    mode_buttons = [
        InlineKeyboardButton(labels[mode], callback_data=f"set_storage_mode:{mode}")
        for mode in normalized_modes
    ]

    rows = [
        [InlineKeyboardButton(f"Storage Mode | {_storage_mode_label(current_mode)}", callback_data="noop")],
        mode_buttons,
        [InlineKeyboardButton("Quick Cycle", callback_data="cycle_storage_mode")],
        [InlineKeyboardButton("Back", callback_data="show_advanced_settings"), InlineKeyboardButton("Close", callback_data="close_settings")],
    ]
    return InlineKeyboardMarkup(rows)


def buy_plans_markup(active_plans: list[dict]):
    from features.plan_manager import get_plan_durations
    rows = []
    for plan in active_plans:
        p_name = plan.get("name") or "Plan"
        p_id = plan.get("id")
        durations = get_plan_durations(plan)
        min_price = min([d["price"] for d in durations]) if durations else plan.get("price", 99)
        btn_text = f"💎 {p_name} — From ₹{min_price}"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"buy_plan:{p_id}")])
    rows.append([
        InlineKeyboardButton("⬅️ Back", callback_data="show_premium_info"),
        InlineKeyboardButton("❌ Close", callback_data="close_settings"),
    ])
    return InlineKeyboardMarkup(rows)


def plan_durations_markup(plan_id: str, durations: list[dict]):
    rows = []
    row = []
    for dur in durations:
        btn = InlineKeyboardButton(
            dur["display"],
            callback_data=f"buy_dur:{plan_id}:{dur['key']}",
        )
        row.append(btn)
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([
        InlineKeyboardButton("⬅️ Back to Plans", callback_data="buy_plans_menu"),
        InlineKeyboardButton("❌ Close", callback_data="close_settings"),
    ])
    return InlineKeyboardMarkup(rows)


def order_payment_markup(order_id: str, deep_links: dict | None = None):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔄 Check Payment Status", callback_data=f"pay_check:{order_id}")],
        [
            InlineKeyboardButton("✅ Submit 12-Digit UTR", callback_data=f"pay_utr:{order_id}"),
            InlineKeyboardButton("❌ Cancel Order", callback_data=f"pay_cancel:{order_id}"),
        ],
    ])


def admin_payment_approval_markup(order_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Activate", callback_data=f"adm_approve_pay:{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_pay:{order_id}"),
        ]
    ])


def admin_plans_list_markup(plans: dict):
    rows = []
    sorted_plans = sorted(plans.items(), key=lambda x: int(x[1].get("price", 0)))
    for p_id, p in sorted_plans:
        status_icon = "🟢" if p.get("is_active", True) else "🔴"
        name = p.get("name", p_id)
        price = p.get("price", 0)
        days = p.get("duration_days", 30)
        btn_text = f"{status_icon} {name} (₹{price} / {days}d)"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"adm_plan_detail:{p_id}")])

    rows.append([
        InlineKeyboardButton("➕ Create New Plan", callback_data="adm_add_plan_start"),
        InlineKeyboardButton("🔄 Reset Defaults", callback_data="adm_reset_plans"),
    ])
    rows.append([
        InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="show_admin_panel"),
        InlineKeyboardButton("❌ Close", callback_data="close_settings"),
    ])
    return InlineKeyboardMarkup(rows)


def admin_plan_action_markup(plan_id: str, is_active: bool):
    toggle_text = "🔴 Disable Plan" if is_active else "🟢 Enable Plan"
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(toggle_text, callback_data=f"adm_toggle_plan:{plan_id}"),
            InlineKeyboardButton("✏️ Edit Price", callback_data=f"adm_edit_price_start:{plan_id}"),
        ],
        [
            InlineKeyboardButton("⚙️ Edit Limits & Days", callback_data=f"adm_edit_limits_start:{plan_id}"),
            InlineKeyboardButton("🗑 Delete Plan", callback_data=f"adm_delete_plan:{plan_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Plans", callback_data="admin_manage_plans"),
            InlineKeyboardButton("👑 Admin Panel", callback_data="show_admin_panel"),
        ],
    ])


def admin_payment_gateway_markup():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⚡ Setup Paytm MID & Key", callback_data="adm_set_paytm_start"),
            InlineKeyboardButton("🏦 Setup UPI ID", callback_data="adm_set_upi_start"),
        ],
        [
            InlineKeyboardButton("🧪 Test Paytm Gateway API", callback_data="adm_test_paytm"),
            InlineKeyboardButton("📋 View Pending Orders", callback_data="admin_pending_orders"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Admin Panel", callback_data="show_admin_panel"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def admin_pending_orders_markup(orders: list):
    rows = []
    for o in orders[:8]:
        order_id = o.get("order_id")
        uid = o.get("user_id")
        amt = o.get("amount")
        utr = o.get("utr_number")
        utr_tag = f"UTR: {utr[-4:]}" if utr else "No UTR"
        btn_text = f"⏳ #{order_id} | ₹{amt} | {utr_tag}"
        rows.append([InlineKeyboardButton(btn_text, callback_data=f"adm_view_order:{order_id}")])

    rows.append([
        InlineKeyboardButton("🔄 Refresh Orders", callback_data="admin_pending_orders"),
        InlineKeyboardButton("⬅️ Admin Panel", callback_data="show_admin_panel"),
    ])
    return InlineKeyboardMarkup(rows)


def admin_order_detail_markup(order_id: str):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Approve & Activate", callback_data=f"adm_approve_pay:{order_id}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"adm_reject_pay:{order_id}"),
        ],
        [
            InlineKeyboardButton("⬅️ Back to Orders", callback_data="admin_pending_orders"),
            InlineKeyboardButton("👑 Admin Panel", callback_data="show_admin_panel"),
        ],
    ])

