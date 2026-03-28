from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import (
    MAIN_CHANNEL,
    UPDATES_CHANNEL,
    PLAYLIST_LINK,
    WHATSAPP_CHANNEL,
    YOUTUBE_CHANNEL,
    JOIN_LINK,
)


def _safe_url(value: str, fallback: str = "https://t.me/"):
    value = str(value or "").strip()
    fallback = str(fallback or "https://t.me/").strip()

    if value.startswith("http://") or value.startswith("https://"):
        return value

    if value.startswith("@"):
        return f"https://t.me/{value[1:]}"

    if value.startswith("t.me/"):
        return f"https://{value}"

    return fallback


def _upload_mode_button_label(mode: str) -> str:
    mode = str(mode or "media").strip().lower()
    if mode == "document":
        return "📄 Send As Document"
    return "🎞 Send As Media"


def _premium_label(is_premium: bool) -> str:
    return "💎 Premium" if is_premium else "🆓 Free"


def _yes_no_label(enabled: bool, on_text: str, off_text: str) -> str:
    return on_text if enabled else off_text


def _task_status_badge(status: str) -> str:
    value = str(status or "checking").strip().lower()
    mapping = {
        "checking": "🔎 Checking",
        "queued": "🔎 Checking",
        "validating": "🔎 Checking",
        "fetching": "🔎 Checking",
        "processing": "🔎 Checking",
        "downloading": "📥 Downloading",
        "uploading": "📤 Uploading",
        "copying": "🚀 Copying",
        "completed": "✅ Completed",
        "failed": "❌ Failed",
        "cancelled": "🛑 Cancelled",
    }
    return mapping.get(value, f"ℹ️ {value.title()}")
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
):
    auth_button = (
        InlineKeyboardButton(
            f"{marks.get('login', '❌')} Logout",
            callback_data="do_logout"
        )
        if has_session
        else InlineKeyboardButton(
            f"{marks.get('login', '❌')} Login",
            callback_data="show_login_info"
        )
    )

    upload_mode_label = _upload_mode_button_label(upload_mode)

    rows = [
        [
            InlineKeyboardButton(
                f"{marks.get('premium', '🆓')} {_premium_label(is_premium)}",
                callback_data="show_premium_info"
            )
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('upload_mode', '🎞')} {upload_mode_label}",
                callback_data="toggle_upload_mode"
            )
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('thumbnail', '❌')} Thumbnail",
                callback_data="show_thumbnail"
            ),
            InlineKeyboardButton(
                f"{marks.get('caption', '❌')} Caption",
                callback_data="show_caption"
            ),
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('prefix', '❌')} Prefix",
                callback_data="show_prefix"
            ),
            InlineKeyboardButton(
                f"{marks.get('suffix', '❌')} Suffix",
                callback_data="show_suffix"
            ),
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('auto_rename', '❌')} Auto Rename",
                callback_data="show_auto_rename"
            ),
            InlineKeyboardButton(
                f"{marks.get('metadata', '❌')} Metadata",
                callback_data="show_metadata"
            ),
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('destination', '❌')} Destination",
                callback_data="show_destination"
            ),
            InlineKeyboardButton(
                f"{marks.get('topic_id', '❌')} Topic ID",
                callback_data="show_topic_id"
            ),
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('replace_words', '❌')} Replace Words",
                callback_data="show_replace_words"
            )
        ],
        [
            InlineKeyboardButton(
                f"{marks.get('index_mode', '❌')} Auto Index",
                callback_data="show_index_settings"
            ),
            InlineKeyboardButton(
                f"{marks.get('batch_mode', '❌')} Batch",
                callback_data="show_batch_settings"
            ),
        ],
    ]

    if is_admin:
        rows.append([
            InlineKeyboardButton("🛡 Admin Panel", callback_data="show_admin_panel"),
            InlineKeyboardButton("👥 Users", callback_data="show_admin_users"),
        ])

    rows.extend([
        [
            auth_button,
            InlineKeyboardButton("📊 Login Status", callback_data="show_login_status"),
        ],
        [
            InlineKeyboardButton("♻️ Reset All", callback_data="reset_all_settings"),
        ],
    ])

    return InlineKeyboardMarkup(rows)


# ---------- ADMIN / PREMIUM ----------
def admin_panel_buttons():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📊 Stats", callback_data="admin_stats"),
            InlineKeyboardButton("👥 Users", callback_data="show_admin_users"),
        ],
        [
            InlineKeyboardButton("💎 Premium", callback_data="admin_premium_help"),
            InlineKeyboardButton("📢 Broadcast", callback_data="admin_broadcast_help"),
        ],
        [
            InlineKeyboardButton("🆕 Recent Users", callback_data="admin_recent_users"),
            InlineKeyboardButton("🧾 Logs", callback_data="admin_logs_summary"),
        ],
        [
            InlineKeyboardButton("🧪 Task Debug", callback_data="admin_task_debug_help"),
            InlineKeyboardButton("📌 Destinations", callback_data="admin_destination_help"),
        ],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def premium_info_buttons(is_admin: bool = False):
    rows = []

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


def replace_words_buttons(enabled: bool = True):
    label = _yes_no_label(enabled, "✅ Replace Words On", "❌ Replace Words Off")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_replace_words")],
        [InlineKeyboardButton("✍️ Set Rules", callback_data="set_replace_words")],
        [InlineKeyboardButton("🗑 Clear Rules", callback_data="clear_replace_words")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
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
    if done:
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


def batch_live_board_buttons(batch_key: str, current_task_id: str = "", done: bool = False):
    cancel_cb = f"task_cancel:{current_task_id}" if current_task_id else "noop"
    if done:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
            [InlineKeyboardButton("❌ Close", callback_data=f"batch_close:{batch_key}")],
        ])

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("♻️ Refresh", callback_data=f"batch_refresh:{batch_key}"),
            InlineKeyboardButton("🛑 Cancel Current", callback_data=cancel_cb),
        ],
        [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
        [InlineKeyboardButton("❌ Close", callback_data=f"batch_close:{batch_key}")],
    ])
