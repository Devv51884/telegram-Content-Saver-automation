from __future__ import annotations

import os

from pyrogram.enums import ParseMode

from features.message_helpers import (
    get_message_duration,
    get_message_file_name,
    get_message_file_size,
)
from features.settings_helpers import (
    apply_replace_rules,
    get_caption_replace_rules,
    get_file_replace_rules,
    sanitize_filename,
    split_filename_ext,
)
from storage import format_index_number, get_caption_settings_for_mode

MEDIA_KIND_NAMES = {
    "message_media_type.photo",
    "message_media_type.video",
    "message_media_type.document",
    "message_media_type.audio",
    "message_media_type.voice",
    "message_media_type.animation",
    "photo",
    "video",
    "document",
    "audio",
    "voice",
    "animation",
    "sticker",
    "video_note",
}
MEDIA_KIND_TOKENS = ["photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"]


def is_media_message(source_msg) -> bool:
    if not source_msg:
        return False

    direct_media = (
        getattr(source_msg, "photo", None)
        or getattr(source_msg, "video", None)
        or getattr(source_msg, "document", None)
        or getattr(source_msg, "audio", None)
        or getattr(source_msg, "voice", None)
        or getattr(source_msg, "animation", None)
        or getattr(source_msg, "sticker", None)
        or getattr(source_msg, "video_note", None)
    )
    if direct_media:
        return True

    media_name = str(getattr(source_msg, "media", "") or "").lower()
    return media_name in MEDIA_KIND_NAMES


def is_media_like_message(source_msg) -> bool:
    if is_media_message(source_msg):
        return True
    media_name = str(getattr(source_msg, "media", "") or "").lower()
    return any(token in media_name for token in MEDIA_KIND_TOKENS)


def build_template_context(source_msg, settings: dict, index_no: int = 0):
    filename = sanitize_filename(get_message_file_name(source_msg))
    filename = apply_replace_rules(filename, get_file_replace_rules(settings))

    caption_padding = int(settings.get("caption_index_padding", 2) or 2)
    caption_start = int(settings.get("caption_index_start", 1) or 1)
    filename_padding = int(settings.get("filename_index_padding", 2) or 2)
    filename_start = int(settings.get("filename_index_start", 1) or 1)

    caption_index_value = format_index_number(max(0, caption_start + max(0, index_no - 1)), caption_padding)
    filename_index_value = format_index_number(max(0, filename_start + max(0, index_no - 1)), filename_padding)

    return {
        "filename": filename,
        "size": str(get_message_file_size(source_msg) or ""),
        "duration": get_message_duration(source_msg),
        "quality": "",
        "language": "",
        "subtitle": "",
        "index": caption_index_value,
        "fileindex": filename_index_value,
    }


def render_template(template: str, context: dict) -> str:
    result = template or ""
    for key, value in context.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def get_parse_mode(value: str | None):
    value = str(value or "").strip().lower()
    if value == "markdown":
        return ParseMode.MARKDOWN
    if value in {"disabled", "none", "off", "text"}:
        return None
    return ParseMode.HTML


def ensure_non_empty_text(value: str | None) -> str:
    value = str(value or "")
    return value if value.strip() else "⁣"


def resolve_downloaded_path(requested_path: str | None, download_result) -> str:
    candidates = []
    if isinstance(download_result, str):
        candidates.append(download_result)
    if isinstance(requested_path, str):
        candidates.append(requested_path)
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return str(download_result or requested_path or "")


def ensure_valid_downloaded_file(file_path: str):
    if not file_path or not os.path.exists(file_path):
        raise RuntimeError("Download complete hone ke baad file temp me nahi mili.")
    try:
        size = os.path.getsize(file_path)
    except Exception:
        size = 0
    if size <= 0:
        raise RuntimeError("Downloaded file ka size 0 B aaya. Source restricted/protected ho sakta hai ya download corrupt hua hai.")
    return file_path


def build_final_caption(source_msg, settings: dict, index_no: int = 0, storage_mode: str | None = None):
    context = build_template_context(source_msg, settings, index_no=index_no)
    caption = source_msg.caption or ""
    caption_state = get_caption_settings_for_mode(settings, storage_mode)

    if caption_state.get("enabled") and caption_state.get("text"):
        caption = render_template(caption_state.get("text", ""), context)

    caption = apply_replace_rules(caption, get_caption_replace_rules(settings))

    prefix = (settings.get("prefix") or "").strip()
    suffix = (settings.get("suffix") or "").strip()

    if caption:
        if prefix:
            caption = f"{prefix} {caption}".strip()
        if suffix:
            caption = f"{caption} {suffix}".strip()

    return caption


def build_final_text(text: str, source_msg, settings: dict, index_no: int = 0, storage_mode: str | None = None):
    context = build_template_context(source_msg, settings, index_no=index_no)
    value = text or ""
    caption_state = get_caption_settings_for_mode(settings, storage_mode)

    if caption_state.get("enabled") and caption_state.get("text"):
        value = render_template(caption_state.get("text", value), context)

    value = apply_replace_rules(value, get_caption_replace_rules(settings))

    prefix = (settings.get("prefix") or "").strip()
    suffix = (settings.get("suffix") or "").strip()

    if prefix:
        value = f"{prefix} {value}".strip()
    if suffix:
        value = f"{value} {suffix}".strip()

    return value or " "


def build_final_filename(original_filename: str, settings: dict, index_no: int = 0):
    original_filename = sanitize_filename(original_filename or "file")
    original_filename = apply_replace_rules(original_filename, get_file_replace_rules(settings))

    base, ext = split_filename_ext(original_filename)
    filename_padding = int(settings.get("filename_index_padding", 2) or 2)
    filename_start = int(settings.get("filename_index_start", 1) or 1)
    filename_index_value = format_index_number(max(0, filename_start + max(0, index_no - 1)), filename_padding)

    context = {"filename": base, "index": filename_index_value}
    rename_template = (settings.get("rename_template") or "").strip()
    auto_rename = (settings.get("auto_rename") or "").strip()
    new_base = base

    if rename_template:
        new_base = render_template(rename_template, context).strip()
    elif settings.get("auto_rename_enabled") and auto_rename:
        if "{filename}" in auto_rename or "{index}" in auto_rename:
            new_base = render_template(auto_rename, context).strip()
        else:
            new_base = auto_rename.strip()

    if settings.get("filename_index_enabled") and "{index}" not in new_base:
        new_base = f"{filename_index_value}_{new_base}".strip("_ ")

    file_prefix = (settings.get("filename_prefix") or "").strip()
    file_suffix = (settings.get("filename_suffix") or "").strip()

    if file_prefix:
        new_base = f"{file_prefix} {new_base}".strip()
    if file_suffix:
        new_base = f"{new_base} {file_suffix}".strip()

    new_base = apply_replace_rules(new_base, get_file_replace_rules(settings))
    new_base = sanitize_filename(new_base)
    return f"{new_base}{ext}"


def build_storage_annotation(source_msg, settings: dict, index_no: int = 0, storage_mode: str | None = None) -> str:
    settings = settings or {}
    parts = []

    if is_media_message(source_msg):
        caption_value = str(build_final_caption(source_msg, settings, index_no=index_no, storage_mode=storage_mode) or "").strip()
    else:
        raw_text = str(getattr(source_msg, "text", "") or getattr(source_msg, "caption", "") or "")
        caption_value = str(build_final_text(raw_text, source_msg, settings, index_no=index_no, storage_mode=storage_mode) or "").strip()

    if caption_value:
        parts.append(caption_value)

    if settings.get("metadata_enabled"):
        metadata_lines = []
        mapping = [
            ("Video Title", "metadata_video_title"),
            ("Video Author", "metadata_video_author"),
            ("Audio Title", "metadata_audio_title"),
            ("Subtitle Title", "metadata_subtitle_title"),
        ]
        for label, key in mapping:
            value = str(settings.get(key, "") or "").strip()
            if value:
                metadata_lines.append(f"{label}: {value}")
        if metadata_lines:
            parts.append("\n".join(metadata_lines))

    return "\n\n".join([part for part in parts if str(part or "").strip()]).strip()


def has_transforming_settings(settings: dict) -> bool:
    settings = settings or {}
    return bool(
        settings.get("thumbnail_enabled")
        or (settings.get("caption_enabled") and settings.get("caption_text"))
        or settings.get("prefix")
        or settings.get("suffix")
        or get_file_replace_rules(settings)
        or get_caption_replace_rules(settings)
        or settings.get("auto_rename_enabled")
        or settings.get("rename_template")
        or settings.get("auto_rename")
        or settings.get("filename_prefix")
        or settings.get("filename_suffix")
        or settings.get("filename_index_enabled")
        or settings.get("metadata_enabled")
    )
