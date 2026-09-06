from __future__ import annotations

import importlib.util
import os

from config import DEFAULT_DESTINATION
from features.media_transforms import is_media_message
from features.message_helpers import get_message_file_id, get_message_file_name
from features.settings_helpers import (
    get_caption_replace_rules,
    get_file_replace_rules,
    normalize_target,
)
from storage import (
    get_caption_settings_for_mode,
    get_user_allowed_storage_modes,
    user_can_use_storage_mode,
)

DOCUMENT_EXTENSIONS = {"pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx", "txt"}
ARCHIVE_EXTENSIONS = {"zip", "rar", "7z", "tar", "gz"}


def normalize_storage_mode(value: str) -> str:
    value = str(value or "telegram").strip().lower()
    return value if value in {"telegram", "gdrive", "rclone"} else "telegram"


def get_configured_storage_destination(settings: dict | None):
    settings = settings or {}
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    if storage_mode == "gdrive":
        return str(settings.get("gdrive_folder_id", "") or "").strip() or None
    if storage_mode == "rclone":
        return str(settings.get("rclone_remote_path", "") or "").strip() or None
    return normalize_target(settings.get("upload_destination", "")) or DEFAULT_DESTINATION or None


def ensure_storage_runtime_ready(settings: dict | None, ensure_site_packages=None):
    settings = settings or {}
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))

    if storage_mode == "gdrive":
        if callable(ensure_site_packages):
            ensure_site_packages()
        token_path = str(settings.get("gdrive_token_path", "") or "").strip()
        folder_id = str(settings.get("gdrive_folder_id", "") or "").strip()
        if not token_path or not os.path.exists(token_path):
            raise RuntimeError("Google Drive token.pickle missing hai.")
        if not folder_id:
            raise RuntimeError("Google Drive Folder ID set nahi hai.")
        if importlib.util.find_spec("googleapiclient") is None:
            raise RuntimeError("Google Drive runtime missing hai. `google-api-python-client` install karo.")
        return

    if storage_mode == "rclone":
        config_path = str(settings.get("rclone_config_path", "") or "").strip()
        remote_path = str(settings.get("rclone_remote_path", "") or "").strip()
        if not config_path or not os.path.exists(config_path):
            raise RuntimeError("rclone.conf missing hai.")
        if not remote_path:
            raise RuntimeError("Rclone Path set nahi hai.")


def get_next_allowed_storage_mode(current_mode: str, allowed_modes: list[str] | None = None) -> str:
    normalized = []
    for mode in (allowed_modes or ["telegram"]):
        mode = normalize_storage_mode(mode)
        if mode not in normalized:
            normalized.append(mode)
    if not normalized:
        normalized = ["telegram"]

    current_mode = normalize_storage_mode(current_mode)
    if current_mode not in normalized:
        return normalized[0]
    return normalized[(normalized.index(current_mode) + 1) % len(normalized)]


def get_effective_storage_mode_for_message(user_id: int, source_msg, settings: dict) -> str:
    settings = settings or {}
    base_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    route_template = str(settings.get("route_template", "off") or "off").strip().lower()
    file_name = (get_message_file_name(source_msg) or "").lower()
    ext = file_name.rsplit(".", 1)[-1] if "." in file_name else ""
    mode = base_mode
    if route_template == "smart":
        if source_msg.document and ext in DOCUMENT_EXTENSIONS:
            mode = "gdrive"
        elif source_msg.document and ext in ARCHIVE_EXTENSIONS:
            mode = "rclone"
    elif route_template == "docs_to_gdrive" and (source_msg.document or ext in DOCUMENT_EXTENSIONS):
        mode = "gdrive"
    elif route_template == "media_to_telegram" and is_media_message(source_msg):
        mode = "telegram"
    elif route_template == "archives_to_rclone" and ext in ARCHIVE_EXTENSIONS:
        mode = "rclone"
    if not user_can_use_storage_mode(user_id, mode):
        raise RuntimeError(f"Current plan me {mode} storage allowed nahi hai. Allowed: {', '.join(get_user_allowed_storage_modes(user_id))}")
    return mode


def get_primary_telegram_settings(settings: dict) -> dict:
    cloned = dict(settings or {})
    tg_mode = str(cloned.get("telegram_upload_mode", cloned.get("upload_mode", "media")) or "media").strip().lower()
    if tg_mode not in {"media", "document"}:
        tg_mode = "media"
    cloned["telegram_upload_mode"] = tg_mode
    cloned["upload_mode"] = tg_mode
    telegram_caption = get_caption_settings_for_mode(cloned, "telegram")
    cloned["caption_enabled"] = bool(telegram_caption.get("enabled"))
    cloned["caption_text"] = str(telegram_caption.get("text") or "")
    return cloned


def analyze_telegram_media_delivery(source_msg, settings: dict | None) -> dict:
    settings = get_primary_telegram_settings(settings or {})
    upload_mode = str(settings.get("telegram_upload_mode", settings.get("upload_mode", "media")) or "media").strip().lower()
    if upload_mode not in {"media", "document"}:
        upload_mode = "media"

    supports_caption = not bool(getattr(source_msg, "sticker", None) or getattr(source_msg, "video_note", None))
    caption_state = get_caption_settings_for_mode(settings, "telegram")
    custom_caption_enabled = bool(caption_state.get("enabled") or settings.get("caption_enabled"))
    custom_caption_text = str(caption_state.get("text") or settings.get("caption_text") or "").strip()
    original_caption = str(getattr(source_msg, "caption", "") or "").strip()
    caption_rules = bool(get_caption_replace_rules(settings))
    prefix_or_suffix = bool(str(settings.get("prefix", "") or "").strip() or str(settings.get("suffix", "") or "").strip())

    caption_transform = False
    if supports_caption:
        caption_transform = bool(
            (custom_caption_enabled and custom_caption_text)
            or (original_caption and (caption_rules or prefix_or_suffix))
        )

    needs_document_upload = bool(
        upload_mode == "document"
        and not getattr(source_msg, "document", None)
        and not getattr(source_msg, "sticker", None)
        and not getattr(source_msg, "video_note", None)
    )
    document_output = bool(getattr(source_msg, "document", None) or needs_document_upload)
    filename_transform = bool(
        document_output and (
            get_file_replace_rules(settings)
            or settings.get("auto_rename_enabled")
            or settings.get("rename_template")
            or settings.get("auto_rename")
            or settings.get("filename_prefix")
            or settings.get("filename_suffix")
            or settings.get("filename_index_enabled")
        )
    )
    thumbnail_transform = bool(
        settings.get("thumbnail_enabled")
        and str(settings.get("thumbnail_file_id") or "").strip()
        and (
            getattr(source_msg, "video", None)
            or getattr(source_msg, "document", None)
            or getattr(source_msg, "audio", None)
            or getattr(source_msg, "animation", None)
        )
    )

    requires_local_upload = bool(needs_document_upload or filename_transform or thumbnail_transform)
    direct_copy_blocked = bool(requires_local_upload)
    cached_send_allowed = bool(get_message_file_id(source_msg) and not requires_local_upload)

    return {
        "upload_mode": upload_mode,
        "caption_transform": caption_transform,
        "filename_transform": filename_transform,
        "thumbnail_transform": thumbnail_transform,
        "needs_document_upload": needs_document_upload,
        "requires_local_upload": requires_local_upload,
        "direct_copy_blocked": direct_copy_blocked,
        "cached_send_allowed": cached_send_allowed,
    }


def build_missing_storage_target_text(settings: dict | None) -> str:
    settings = settings or {}
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))

    if storage_mode == "gdrive":
        has_token = bool(str(settings.get("gdrive_token_path", "") or "").strip())
        has_folder = bool(str(settings.get("gdrive_folder_id", "") or "").strip())
        if not has_token and not has_folder:
            return (
                "☁️ Google Drive Storage Mode selected hai.\n\n"
                "Pehle `token.pickle` aur `Folder ID` set karo.\n"
                "/settings -> token.pickle aur Folder ID"
            )
        if not has_token:
            return (
                "☁️ Google Drive Storage Mode selected hai.\n\n"
                "Pehle `token.pickle` set karo.\n"
                "/settings -> token.pickle"
            )
        return (
            "☁️ Google Drive Storage Mode selected hai.\n\n"
            "Pehle `Folder ID` set karo.\n"
            "/settings -> Folder ID"
        )

    if storage_mode == "rclone":
        has_config = bool(str(settings.get("rclone_config_path", "") or "").strip())
        has_remote_path = bool(str(settings.get("rclone_remote_path", "") or "").strip())
        if not has_config and not has_remote_path:
            return (
                "🗂 Rclone Storage Mode selected hai.\n\n"
                "Pehle `rclone.conf` aur `Rclone Path` set karo.\n"
                "/settings -> Rclone Config aur Rclone Path"
            )
        if not has_config:
            return (
                "🗂 Rclone Storage Mode selected hai.\n\n"
                "Pehle `rclone.conf` set karo.\n"
                "/settings -> Rclone Config"
            )
        return (
            "🗂 Rclone Storage Mode selected hai.\n\n"
            "Pehle `Rclone Path` set karo.\n"
            "/settings -> Rclone Path"
        )

    return (
        "📍 Pehle apna destination set karo.\n\n"
        "/settings -> Upload Destination me chat id ya @channelusername set karo, tabhi content save hoga."
    )
