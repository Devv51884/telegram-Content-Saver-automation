from __future__ import annotations

import json
import os
import re
import time
import uuid
from threading import Lock

from config import DATA_DIR
from features.plan_manager import get_plan_by_id

ORDERS_FILE = os.path.join(DATA_DIR, "orders.json")
_ORDER_LOCK = Lock()
ORDER_EXPIRY_SECONDS = 300  # 5 minutes


def _load_orders() -> dict:
    if not os.path.exists(ORDERS_FILE):
        return {}
    try:
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _save_orders(orders: dict):
    os.makedirs(os.path.dirname(ORDERS_FILE), exist_ok=True)
    temp_path = f"{ORDERS_FILE}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(orders, f, indent=2, ensure_ascii=False)
    os.replace(temp_path, ORDERS_FILE)


def create_order(user_id: int, plan_id: str) -> dict:
    plan = get_plan_by_id(plan_id)
    if not plan:
        raise ValueError(f"Plan '{plan_id}' nahi mila.")

    now = int(time.time())
    order_id = f"CD{now % 1000000}{uuid.uuid4().hex[:4].upper()}"

    order = {
        "order_id": order_id,
        "user_id": int(user_id),
        "plan_id": plan["id"],
        "plan_name": plan["name"],
        "amount": int(plan["price"]),
        "duration_days": int(plan["duration_days"]),
        "batch_limit": int(plan["batch_limit"]),
        "task_limit": int(plan["task_limit"]),
        "storage_modes": str(plan["storage_modes"]),
        "features": list(plan["features"]),
        "created_at": now,
        "expires_at": now + ORDER_EXPIRY_SECONDS,
        "status": "pending",
        "utr_number": "",
        "verified_via": "",
        "verified_at": 0,
    }

    with _ORDER_LOCK:
        orders = _load_orders()
        orders[order_id] = order
        _save_orders(orders)

    return order


def get_order(order_id: str) -> dict | None:
    orders = _load_orders()
    return orders.get(str(order_id).strip())


def get_user_pending_order(user_id: int) -> dict | None:
    orders = _load_orders()
    now = int(time.time())
    for order in orders.values():
        if int(order.get("user_id", 0)) == int(user_id) and order.get("status") == "pending":
            if int(order.get("expires_at", 0)) > now:
                return order
    return None


def is_order_expired(order: dict) -> bool:
    if not order:
        return True
    if order.get("status") != "pending":
        return False
    return int(time.time()) > int(order.get("expires_at", 0))


def cancel_order(order_id: str) -> bool:
    with _ORDER_LOCK:
        orders = _load_orders()
        order = orders.get(order_id)
        if order and order.get("status") == "pending":
            order["status"] = "cancelled"
            _save_orders(orders)
            return True
        return False


def submit_order_utr(order_id: str, utr: str) -> tuple[bool, str]:
    utr = str(utr or "").strip()
    if not re.match(r"^\d{12}$", utr):
        return False, "❌ UTR number 12 digits ka hona chahiye (e.g. 424212345678)."

    with _ORDER_LOCK:
        orders = _load_orders()
        order = orders.get(order_id)
        if not order:
            return False, "❌ Order nahi mila."

        if order.get("status") != "pending":
            return False, f"❌ Order already {order.get('status')} ho chuka hai."

        now = int(time.time())
        if now > int(order.get("expires_at", 0)):
            order["status"] = "expired"
            _save_orders(orders)
            return False, "⏱️ Yeh order 5 minute me expire ho chuka hai. Naya order create karein."

        for oid, other in orders.items():
            if oid != order_id and other.get("utr_number") == utr and other.get("status") in {"paid", "pending"}:
                return False, "❌ Yeh UTR number already use kiya ja chuka hai."

        order["utr_number"] = utr
        order["utr_submitted_at"] = now
        _save_orders(orders)

    return True, "✅ UTR successfully submit ho gaya hai."


def mark_order_paid(order_id: str, verified_via: str = "paytm_auto", utr: str = "") -> dict | None:
    with _ORDER_LOCK:
        orders = _load_orders()
        order = orders.get(order_id)
        if not order:
            return None

        if order.get("status") == "paid":
            return order

        now = int(time.time())
        order["status"] = "paid"
        order["verified_via"] = str(verified_via)
        order["verified_at"] = now
        if utr:
            order["utr_number"] = str(utr)

        _save_orders(orders)
        return order


def get_pending_orders() -> list[dict]:
    orders = _load_orders()
    now = int(time.time())
    pending = []
    for order in orders.values():
        if order.get("status") == "pending" and int(order.get("expires_at", 0)) > now:
            pending.append(order)
    return sorted(pending, key=lambda x: int(x.get("created_at", 0)), reverse=True)
