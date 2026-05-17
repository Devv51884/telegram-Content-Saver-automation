from __future__ import annotations

CAPTION_MODE_KEYS = {
    "telegram": ("telegram_caption_enabled", "telegram_caption_text"),
    "gdrive": ("gdrive_caption_enabled", "gdrive_caption_text"),
    "rclone": ("rclone_caption_enabled", "rclone_caption_text"),
}


def _to_bool(value, default=False):
    if isinstance(value, bool):
        return value
    if value is None:
        return default
    if isinstance(value, str):
        value = value.strip().lower()
        if value in {"true", "1", "yes", "on"}:
            return True
        if value in {"false", "0", "no", "off"}:
            return False
    try:
        return bool(value)
    except Exception:
        return default


def normalize_storage_mode_key(value: str) -> str:
    value = str(value or "telegram").strip().lower()
    return value if value in CAPTION_MODE_KEYS else "telegram"


def get_caption_setting_keys(storage_mode: str | None = None):
    return CAPTION_MODE_KEYS[normalize_storage_mode_key(storage_mode)]


def get_caption_settings_for_mode(settings: dict | None, storage_mode: str | None = None):
    settings = settings if isinstance(settings, dict) else {}
    mode = normalize_storage_mode_key(storage_mode or settings.get("storage_mode", "telegram"))
    enabled_key, text_key = get_caption_setting_keys(mode)
    return {
        "storage_mode": mode,
        "enabled_key": enabled_key,
        "text_key": text_key,
        "enabled": _to_bool(settings.get(enabled_key, False), False),
        "text": str(settings.get(text_key, "") or "").strip(),
    }
