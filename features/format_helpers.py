from __future__ import annotations


def human_bytes(value: float) -> str:
    try:
        value = float(value)
    except Exception:
        value = 0.0

    units = ["B", "KB", "MB", "GB", "TB"]
    idx = 0
    while value >= 1024 and idx < len(units) - 1:
        value /= 1024.0
        idx += 1
    return f"{value:.2f} {units[idx]}"


def human_speed(bytes_per_sec: float) -> str:
    return f"{human_bytes(bytes_per_sec)}/s"


def human_eta(seconds: float) -> str:
    try:
        seconds = int(max(0, seconds))
    except Exception:
        seconds = 0

    if seconds < 60:
        return f"{seconds}s"
    minutes, sec = divmod(seconds, 60)
    if minutes < 60:
        return f"{minutes}m {sec}s"
    hours, minutes = divmod(minutes, 60)
    return f"{hours}h {minutes}m"


def progress_bar(percent: float, length: int = 10) -> str:
    try:
        percent = max(0.0, min(100.0, float(percent)))
    except Exception:
        percent = 0.0
    filled = int(round((percent / 100.0) * length))
    return "█" * filled + "░" * (length - filled)
