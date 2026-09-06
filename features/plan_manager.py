from __future__ import annotations

import json
import os
from threading import RLock

from config import DATA_DIR, ADMIN_UPI_ID, ADMIN_UPI_NAME

PLANS_FILE = os.path.join(DATA_DIR, "plans.json")
PAYMENT_CONFIG_FILE = os.path.join(DATA_DIR, "payment_config.json")
_PLAN_LOCK = RLock()

DEFAULT_PLANS = {
    "silver": {
        "id": "silver",
        "name": "Silver Plan 🥉",
        "price": 99,
        "duration_days": 30,
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


def save_plan(plan_data: dict):
    plan_id = str(plan_data.get("id", "")).strip().lower()
    if not plan_id:
        raise ValueError("Plan ID cannot be empty")
    with _PLAN_LOCK:
        plans = get_all_plans()
        plans[plan_id] = {
            "id": plan_id,
            "name": str(plan_data.get("name") or plan_id.capitalize()),
            "price": max(1, int(plan_data.get("price", 99))),
            "duration_days": max(1, int(plan_data.get("duration_days", 30))),
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
        }


def save_payment_config(upi_id: str = "", payee_name: str = "", paytm_mid: str = "", paytm_key: str = ""):
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
        _save_json(PAYMENT_CONFIG_FILE, cfg)
        return cfg
