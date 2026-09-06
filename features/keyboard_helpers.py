from __future__ import annotations


def safe_url(value: str, fallback: str = "https://t.me/"):
    value = str(value or "").strip()
    fallback = str(fallback or "https://t.me/").strip()

    if value.startswith("http://") or value.startswith("https://"):
        return value
    if value.startswith("@"):
        return f"https://t.me/{value[1:]}"
    if value.startswith("t.me/"):
        return f"https://{value}"
    return fallback


def upload_mode_button_label(mode: str) -> str:
    mode = (mode or "media").strip().lower()
    if mode == "document":
        return "📄 Send As Document"
    return "🎞 Send As Media"


def premium_label(is_premium: bool) -> str:
    return "💎 Premium" if is_premium else "🆓 Free"


def yes_no_label(enabled: bool, on_text: str, off_text: str) -> str:
    return on_text if enabled else off_text


def task_status_badge(status: str) -> str:
    value = (status or "checking").strip().lower()
    mapping = TASK_STATUS_MAPPING = {
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


def storage_mode_label(mode: str) -> str:
    mode = (mode or "telegram").strip().lower()
    return {"telegram": "📨 Telegram", "gdrive": "☁️ Google Drive", "rclone": "🗂 Rclone"}.get(mode, "📨 Telegram")
