from __future__ import annotations


def get_user_storage_mode_from_settings(settings: dict | None) -> str:
    settings = settings if isinstance(settings, dict) else {}
    return str(settings.get("storage_mode", "telegram") or "telegram").strip().lower()


def get_user_telegram_upload_mode_from_settings(settings: dict | None) -> str:
    settings = settings if isinstance(settings, dict) else {}
    return str(settings.get("telegram_upload_mode", settings.get("upload_mode", "media")) or "media").strip().lower()


def get_settings_marks_from_settings(
    settings: dict | None,
    *,
    caption_state: dict | None,
    has_session: bool,
    is_premium: bool,
    setting_mark_fn,
):
    settings = settings if isinstance(settings, dict) else {}
    caption_state = caption_state if isinstance(caption_state, dict) else {}

    storage_mode = get_user_storage_mode_from_settings(settings)
    telegram_mode = get_user_telegram_upload_mode_from_settings(settings)
    has_replace_rules = bool(
        settings.get("replace_words_file")
        or settings.get("replace_words_caption")
        or settings.get("replace_words")
    )

    return {
        "storage_mode": {"telegram": "📨", "gdrive": "☁️", "rclone": "🗂"}.get(storage_mode, "📨"),
        "upload_mode": "📄" if telegram_mode == "document" else "🎞",
        "thumbnail": setting_mark_fn(settings.get("thumbnail_file_id")),
        "caption": "✅" if caption_state.get("enabled") and caption_state.get("text") else "❌",
        "prefix": setting_mark_fn(settings.get("prefix")),
        "suffix": setting_mark_fn(settings.get("suffix")),
        "auto_rename": setting_mark_fn(
            settings.get("auto_rename")
            or settings.get("rename_template")
            or settings.get("filename_prefix")
            or settings.get("filename_suffix")
        ),
        "metadata": "✅" if settings.get("metadata_enabled") else "❌",
        "destination": setting_mark_fn(settings.get("upload_destination")),
        "topic_id": setting_mark_fn(settings.get("topic_id")),
        "replace_words": setting_mark_fn(has_replace_rules),
        "index_mode": "✅" if settings.get("index_mode") else "❌",
        "batch_mode": "✅" if settings.get("batch_mode") else "❌",
        "login": "✅" if has_session else "❌",
        "premium": "💎" if is_premium else "🆓",
        "gdrive_token": setting_mark_fn(settings.get("gdrive_token_path")),
        "gdrive_folder": setting_mark_fn(settings.get("gdrive_folder_id")),
        "gdrive": setting_mark_fn(settings.get("gdrive_folder_id") and settings.get("gdrive_token_path")),
        "rclone_config": setting_mark_fn(settings.get("rclone_config_path")),
        "rclone_path": setting_mark_fn(settings.get("rclone_remote_path")),
        "rclone": setting_mark_fn(settings.get("rclone_remote_path") and settings.get("rclone_config_path")),
        "personal_bot": setting_mark_fn(settings.get("personal_bot_token")),
        "route_template": setting_mark_fn(settings.get("route_template") and str(settings.get("route_template")) != "off"),
    }
