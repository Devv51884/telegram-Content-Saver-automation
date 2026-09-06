from __future__ import annotations

import os
import uuid

from storage import get_user_settings, update_user_settings


def normalize_target(target):
    if target is None:
        return None
    if isinstance(target, int):
        return target
    target = (target or "").strip() if isinstance(target, str) else str(target or "").strip()
    if not target:
        return None
    if target.lstrip("-").isdigit():
        return int(target)
    return target


def safe_topic_id(value):
    if value is None:
        return None
    if isinstance(value, int):
        return value
    value = (value or "").strip() if isinstance(value, str) else str(value or "").strip()
    if value.lstrip("-").isdigit():
        return int(value)
    return None


def make_task_id() -> str:
    return uuid.uuid4().hex[:12]


def sanitize_filename(name: str) -> str:
    if not name:
        return "file"
    INVALID_FILENAME_CHARS = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    for char in INVALID_FILENAME_CHARS:
        name = name.replace(char, " ")
    return " ".join(name.split()).strip() or "file"


def split_filename_ext(filename: str):
    filename = filename or ""
    if "." in filename:
        return os.path.splitext(filename)
    return filename, ""


def apply_replace_rules(value: str, rules: str) -> str:
    value = value or ""
    rules = (rules or "").strip()
    if not rules:
        return value

    parts = rules.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            old, new = part.split(":", 1)
            value = value.replace(old.strip(), new.strip())
        else:
            value = value.replace(part, "")
    return " ".join(value.split()).strip()


def get_file_replace_rules(settings: dict | None) -> str:
    settings = settings or {}
    return str(settings.get("replace_words_file") or settings.get("replace_words") or "").strip()


def get_caption_replace_rules(settings: dict | None) -> str:
    settings = settings or {}
    return str(settings.get("replace_words_caption") or settings.get("replace_words") or "").strip()


def update_replace_rule_settings(
    user_id: int,
    settings: dict | None = None,
    *,
    file_rules: str | None = None,
    caption_rules: str | None = None,
):
    current = dict(settings if settings is not None else (get_user_settings(user_id) or {}))
    next_file_rules = str(get_file_replace_rules(current) if file_rules is None else file_rules or "").strip()
    next_caption_rules = str(get_caption_replace_rules(current) if caption_rules is None else caption_rules or "").strip()
    legacy_rules = next_file_rules if next_file_rules and next_file_rules == next_caption_rules else ""
    payload = {
        "replace_words": legacy_rules,
        "replace_words_file": next_file_rules,
        "replace_words_caption": next_caption_rules,
    }
    update_user_settings(user_id, payload)
    current.update(payload)
    return current
