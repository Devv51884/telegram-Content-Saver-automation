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


def join_required_buttons():
    join_url = _safe_url(JOIN_LINK or MAIN_CHANNEL, "https://t.me/")
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🔒 Pehle Channel Join Karo", url=join_url)],
        [InlineKeyboardButton("✅ Join Kar Liya", callback_data="check_join_again")],
    ])


def start_buttons(has_session: bool = False):
    auth_button = (
        InlineKeyboardButton("🚪 Logout", callback_data="do_logout")
        if has_session
        else InlineKeyboardButton("🔐 Login", callback_data="show_login_info")
    )

    return InlineKeyboardMarkup([
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
            auth_button,
            InlineKeyboardButton("⚙️ Settings", callback_data="show_settings_home"),
        ],
    ])


def settings_home_buttons(marks: dict, has_session: bool = False):
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

    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                f"{marks.get('upload_mode', '✅')} Upload Mode",
                callback_data="show_upload_mode"
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
        [
            auth_button,
            InlineKeyboardButton("📊 Login Status", callback_data="show_login_status"),
        ],
        [
            InlineKeyboardButton("♻️ Reset All", callback_data="reset_all_settings"),
        ],
    ])


def submenu_nav(back: str = "show_settings_home"):
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("⬅️ Back", callback_data=back),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def thumbnail_buttons(enabled: bool):
    label = "✅ Thumbnail On" if enabled else "❌ Thumbnail Off"
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
    label = "✅ Caption On" if enabled else "❌ Caption Off"
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
    label = "✅ {index} On" if enabled else "❌ {index} Off"
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
    label = "✅ Metadata On" if enabled else "❌ Metadata Off"
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
    label = "✅ Index ON" if enabled else "❌ Index OFF"
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
    label = "✅ Auto Rename On" if enabled else "❌ Auto Rename Off"
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
    label = "✅ Filename {index} On" if enabled else "❌ Filename {index} Off"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_filename_index_enabled")],
        [InlineKeyboardButton("🔢 Set Padding", callback_data="set_filename_index_padding")],
        [InlineKeyboardButton("🚀 Set Start", callback_data="set_filename_index_start")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_auto_rename"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


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


def task_buttons(task_id: str, done: bool = False):
    if done:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
            [InlineKeyboardButton("❌ Close", callback_data="close_settings")],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♻️ Refresh", callback_data=f"task_refresh:{task_id}")],
        [InlineKeyboardButton("🛑 Cancel", callback_data=f"task_cancel:{task_id}")],
        [InlineKeyboardButton("📂 My Tasks", callback_data="show_my_tasks")],
    ])


def my_tasks_buttons():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("♻️ Refresh", callback_data="show_my_tasks")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])


def batch_buttons(enabled: bool):
    label = "✅ Batch ON" if enabled else "❌ Batch OFF"
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data="toggle_batch_mode")],
        [InlineKeyboardButton("📥 Set Batch Links", callback_data="set_batch_links")],
        [InlineKeyboardButton("▶️ Start Batch", callback_data="start_batch_now")],
        [InlineKeyboardButton("🗑 Clear Batch", callback_data="clear_batch_links")],
        [
            InlineKeyboardButton("⬅️ Back", callback_data="show_settings_home"),
            InlineKeyboardButton("❌ Close", callback_data="close_settings"),
        ],
    ])