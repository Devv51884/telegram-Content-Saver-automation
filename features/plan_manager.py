from __future__ import annotations

import json
import os
from threading import RLock

from config import DATA_DIR, ADMIN_UPI_ID, ADMIN_UPI_NAME

PLANS_FILE = os.path.join(DATA_DIR, "plans.json")
PAYMENT_CONFIG_FILE = os.path.join(DATA_DIR, "payment_config.json")
_PLAN_LOCK = RLock()

DEFAULT_DURATION_OPTIONS = [
    {"key": "1d", "label": "1 Day", "days": 1, "emoji": "⚡"},
    {"key": "7d", "label": "7 Days", "days": 7, "emoji": "🗓️"},
    {"key": "15d", "label": "15 Days", "days": 15, "emoji": "📅"},
    {"key": "30d", "label": "30 Days", "days": 30, "emoji": "⭐"},
    {"key": "365d", "label": "1 Year", "days": 365, "emoji": "👑"},
    {"key": "lifetime", "label": "Lifetime", "days": 3650, "emoji": "♾️"},
]

DEFAULT_TIER_DURATIONS = {
    "silver": {
        "1d": 19,
        "7d": 49,
        "15d": 69,
        "30d": 99,
        "365d": 499,
        "lifetime": 999,
    },
    "gold": {
        "1d": 29,
        "7d": 79,
        "15d": 119,
        "30d": 199,
        "365d": 899,
        "lifetime": 1499,
    },
    "diamond": {
        "1d": 49,
        "7d": 149,
        "15d": 249,
        "30d": 499,
        "365d": 1999,
        "lifetime": 2999,
    },
    "lifetime": {
        "1d": 59,
        "7d": 199,
        "15d": 349,
        "30d": 499,
        "365d": 799,
        "lifetime": 999,
    },
}

DEFAULT_PLANS = {
    "silver": {
        "id": "silver",
        "name": "Silver Plan 🥉",
        "price": 99,
        "duration_days": 30,
        "durations": DEFAULT_TIER_DURATIONS["silver"],
        "batch_limit": 50,
        "task_limit": 3,
        "storage_modes": "telegram,personal_bot",
        "features": [
            "50 Batch Links Limit",
            "3 Parallel Tasks",
            "Fast Processing Speed",
            "Custom Caption & Prefix",
            "Topic & Group Support",
        ],
        "is_active": True,
    },
    "gold": {
        "id": "gold",
        "name": "Gold Plan 🥈",
        "price": 199,
        "duration_days": 30,
        "durations": DEFAULT_TIER_DURATIONS["gold"],
        "batch_limit": 200,
        "task_limit": 5,
        "storage_modes": "telegram,gdrive,personal_bot",
        "features": [
            "200 Batch Links Limit",
            "5 Parallel Tasks",
            "Google Drive Cloud Upload",
            "Custom Thumbnail Support",
            "Auto Rename Files",
            "High Priority Speed",
        ],
        "is_active": True,
    },
    "diamond": {
        "id": "diamond",
        "name": "Diamond VIP 🥇",
        "price": 499,
        "duration_days": 30,
        "durations": DEFAULT_TIER_DURATIONS["diamond"],
        "batch_limit": 500,
        "task_limit": 8,
        "storage_modes": "telegram,gdrive,rclone,personal_bot",
        "features": [
            "500 Mega Batch Limit",
            "8 Parallel Tasks",
            "All Storage Access (GDrive + Rclone)",
            "Ultra Fast Direct Copy",
            "Custom File Indexing",
            "VIP Priority Queue",
        ],
        "is_active": True,
    },
    "lifetime": {
        "id": "lifetime",
        "name": "Lifetime Elite 👑",
        "price": 999,
        "duration_days": 3650,
        "durations": DEFAULT_TIER_DURATIONS["lifetime"],
        "batch_limit": 1000,
        "task_limit": 10,
        "storage_modes": "telegram,gdrive,rclone,personal_bot",
        "features": [
            "1000 Mega Batch Limit",
            "10 Concurrent Tasks",
            "Lifetime Validity (10 Years)",
            "Full GDrive & Rclone Access",
            "Zero Waiting Time",
        ],
        "is_active": True,
    },
}


def _load_json(file_path: str, default_val):
    if not os.path.exists(file_path):
        return default_val
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default_val


def _save_json(file_path: str, data):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    temp_path = f"{file_path}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, file_path)


def get_all_plans() -> dict:
    with _PLAN_LOCK:
        stored = _load_json(PLANS_FILE, None)
        if stored is None or not isinstance(stored, dict) or not stored:
            _save_json(PLANS_FILE, DEFAULT_PLANS)
            return dict(DEFAULT_PLANS)
        return stored


def get_active_plans() -> list[dict]:
    plans = get_all_plans()
    active = [plan for plan in plans.values() if plan.get("is_active", True)]
    return sorted(active, key=lambda x: int(x.get("price", 0)))


def get_plan_by_id(plan_id: str) -> dict | None:
    plans = get_all_plans()
    return plans.get(str(plan_id).strip().lower())


def get_plan_durations(plan_or_id: str | dict) -> list[dict]:
    if isinstance(plan_or_id, str):
        plan = get_plan_by_id(plan_or_id) or {}
        plan_id = plan_or_id.strip().lower()
    elif isinstance(plan_or_id, dict):
        plan = dict(plan_or_id)
        plan_id = str(plan.get("id", "")).strip().lower()
    else:
        plan = {}
        plan_id = ""

    custom_durations = plan.get("durations") if isinstance(plan.get("durations"), dict) else None
    tier_defaults = DEFAULT_TIER_DURATIONS.get(plan_id, {})
    base_price = int(plan.get("price", 99))

    durations_list = []
    for opt in DEFAULT_DURATION_OPTIONS:
        key = opt["key"]
        label = opt["label"]
        days = opt["days"]
        emoji = opt["emoji"]

        if custom_durations and key in custom_durations:
            price = max(1, int(custom_durations[key]))
        elif key in tier_defaults:
            price = max(1, int(tier_defaults[key]))
        else:
            if key == "1d":
                price = max(9, round(base_price * 0.20))
            elif key == "7d":
                price = max(29, round(base_price * 0.45))
            elif key == "15d":
                price = max(49, round(base_price * 0.70))
            elif key == "30d":
                price = base_price
            elif key == "365d":
                price = max(199, round(base_price * 4.5))
            elif key == "lifetime":
                price = max(399, round(base_price * 8.0))
            else:
                price = base_price

        durations_list.append({
            "key": key,
            "label": label,
            "days": days,
            "price": price,
            "emoji": emoji,
            "display": f"{emoji} {label} — ₹{price}",
        })
    return durations_list


def get_plan_duration_info(plan_or_id: str | dict, duration_key: str) -> dict:
    durations = get_plan_durations(plan_or_id)
    duration_key = str(duration_key or "").strip().lower()
    for d in durations:
        if d["key"] == duration_key:
            return d
    for d in durations:
        if d["key"] == "30d":
            return d
    return durations[0] if durations else {
        "key": "30d",
        "label": "30 Days",
        "days": 30,
        "price": 99,
        "emoji": "⭐",
        "display": "⭐ 30 Days — ₹99",
    }


def save_plan(plan_data: dict):
    plan_id = str(plan_data.get("id", "")).strip().lower()
    if not plan_id:
        raise ValueError("Plan ID cannot be empty")
    with _PLAN_LOCK:
        plans = get_all_plans()
        durations = plan_data.get("durations")
        if not isinstance(durations, dict):
            durations = DEFAULT_TIER_DURATIONS.get(plan_id, {})
        plans[plan_id] = {
            "id": plan_id,
            "name": str(plan_data.get("name") or plan_id.capitalize()),
            "price": max(1, int(plan_data.get("price", 99))),
            "duration_days": max(1, int(plan_data.get("duration_days", 30))),
            "durations": durations,
            "batch_limit": max(1, int(plan_data.get("batch_limit", 50))),
            "task_limit": max(1, int(plan_data.get("task_limit", 3))),
            "storage_modes": str(plan_data.get("storage_modes") or "telegram,personal_bot"),
            "features": list(plan_data.get("features") or []),
            "is_active": bool(plan_data.get("is_active", True)),
        }
        _save_json(PLANS_FILE, plans)
        return plans[plan_id]


def delete_plan(plan_id: str) -> bool:
    plan_id = str(plan_id).strip().lower()
    with _PLAN_LOCK:
        plans = get_all_plans()
        if plan_id in plans:
            del plans[plan_id]
            _save_json(PLANS_FILE, plans)
            return True
        return False


def toggle_plan_status(plan_id: str) -> bool | None:
    plan_id = str(plan_id).strip().lower()
    with _PLAN_LOCK:
        plans = get_all_plans()
        if plan_id not in plans:
            return None
        plans[plan_id]["is_active"] = not plans[plan_id].get("is_active", True)
        _save_json(PLANS_FILE, plans)
        return plans[plan_id]["is_active"]


def update_plan_price(plan_id: str, new_price: int) -> bool:
    plan_id = str(plan_id).strip().lower()
    with _PLAN_LOCK:
        plans = get_all_plans()
        if plan_id not in plans:
            return False
        plans[plan_id]["price"] = max(1, int(new_price))
        _save_json(PLANS_FILE, plans)
        return True


def update_plan_duration_price(plan_id: str, duration_key: str, price: int) -> bool:
    plan_id = str(plan_id).strip().lower()
    duration_key = str(duration_key).strip().lower()
    new_price = max(1, int(price))

    with _PLAN_LOCK:
        plans = get_all_plans()
        if plan_id not in plans:
            return False

        durations = plans[plan_id].get("durations")
        if not isinstance(durations, dict):
            durations = dict(DEFAULT_TIER_DURATIONS.get(plan_id, {}))

        durations[duration_key] = new_price
        plans[plan_id]["durations"] = durations

        if duration_key == "30d":
            plans[plan_id]["price"] = new_price

        _save_json(PLANS_FILE, plans)
        return True


def update_plan_limits(plan_id: str, batch_limit: int, task_limit: int, duration_days: int) -> bool:
    plan_id = str(plan_id).strip().lower()
    with _PLAN_LOCK:
        plans = get_all_plans()
        if plan_id not in plans:
            return False
        if batch_limit > 0:
            plans[plan_id]["batch_limit"] = int(batch_limit)
        if task_limit > 0:
            plans[plan_id]["task_limit"] = int(task_limit)
        if duration_days > 0:
            plans[plan_id]["duration_days"] = int(duration_days)
        _save_json(PLANS_FILE, plans)
        return True


def reset_default_plans() -> dict:
    with _PLAN_LOCK:
        _save_json(PLANS_FILE, DEFAULT_PLANS)
        return dict(DEFAULT_PLANS)


def get_payment_config() -> dict:
    with _PLAN_LOCK:
        cfg = _load_json(PAYMENT_CONFIG_FILE, {})
        return {
            "upi_id": str(cfg.get("upi_id") or ADMIN_UPI_ID or "").strip(),
            "payee_name": str(cfg.get("payee_name") or ADMIN_UPI_NAME or "Code Devil Premium").strip(),
            "paytm_mid": str(cfg.get("paytm_mid") or os.environ.get("PAYTM_MID", "")).strip(),
            "paytm_key": str(cfg.get("paytm_key") or os.environ.get("PAYTM_MERCHANT_KEY", "")).strip(),
            "custom_qr_file_id": str(cfg.get("custom_qr_file_id") or "").strip(),
            "custom_qr_path": str(cfg.get("custom_qr_path") or "").strip(),
            "qr_mode": str(cfg.get("qr_mode") or "auto").strip(),
        }


def save_payment_config(
    upi_id: str = "",
    payee_name: str = "",
    paytm_mid: str = "",
    paytm_key: str = "",
    custom_qr_file_id: str = "",
    custom_qr_path: str = "",
    qr_mode: str = "",
):
    with _PLAN_LOCK:
        cfg = _load_json(PAYMENT_CONFIG_FILE, {})
        if upi_id:
            cfg["upi_id"] = str(upi_id).strip()
        if payee_name:
            cfg["payee_name"] = str(payee_name).strip()
        if paytm_mid:
            cfg["paytm_mid"] = str(paytm_mid).strip()
        if paytm_key:
            cfg["paytm_key"] = str(paytm_key).strip()
        if custom_qr_file_id:
            cfg["custom_qr_file_id"] = str(custom_qr_file_id).strip()
        if custom_qr_path:
            cfg["custom_qr_path"] = str(custom_qr_path).strip()
        if qr_mode:
            cfg["qr_mode"] = str(qr_mode).strip()
        _save_json(PAYMENT_CONFIG_FILE, cfg)
        return cfg


def set_custom_qr(file_id: str = "", file_path: str = ""):
    with _PLAN_LOCK:
        cfg = _load_json(PAYMENT_CONFIG_FILE, {})
        if file_id:
            cfg["custom_qr_file_id"] = str(file_id).strip()
        if file_path:
            cfg["custom_qr_path"] = str(file_path).strip()
        cfg["qr_mode"] = "custom"
        _save_json(PAYMENT_CONFIG_FILE, cfg)
        return cfg


def remove_custom_qr():
    with _PLAN_LOCK:
        cfg = _load_json(PAYMENT_CONFIG_FILE, {})
        cfg["custom_qr_file_id"] = ""
        cfg["custom_qr_path"] = ""
        cfg["qr_mode"] = "auto"
        _save_json(PAYMENT_CONFIG_FILE, cfg)
        return cfg
