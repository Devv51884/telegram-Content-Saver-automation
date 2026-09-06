from __future__ import annotations

import asyncio
from runtime_context import LOG_CHANNEL, OWNER_ID
from services.task_service import debug_log
from storage import (
    add_premium,
    set_user_plan_name,
    set_user_plan_features,
    save_user_limit_record,
    get_premium_expiry_text,
)
from features.payment_manager import get_order, mark_order_paid


async def activate_user_plan(client, order_id: str, verified_via: str = "auto", utr: str = "") -> tuple[bool, str]:
    order = get_order(order_id)
    if not order:
        return False, "Order nahi mila."

    if order.get("status") == "paid" and order.get("verified_at"):
        return True, "Order already activated hai."

    paid_order = mark_order_paid(order_id, verified_via=verified_via, utr=utr)
    if not paid_order:
        return False, "Order status update fail hua."

    user_id = int(order["user_id"])
    duration_days = int(order.get("duration_days", 30))
    plan_name = str(order.get("plan_name", "Premium"))
    batch_limit = int(order.get("batch_limit", 50))
    task_limit = int(order.get("task_limit", 3))
    storage_modes = str(order.get("storage_modes", "telegram,personal_bot"))
    features = list(order.get("features", []))

    add_premium(user_id, f"{duration_days}d", plan_name=plan_name)
    set_user_plan_name(user_id, plan_name)
    set_user_plan_features(user_id, features)
    save_user_limit_record(user_id, {
        "batch_limit": batch_limit,
        "task_limit": task_limit,
        "allowed_storage_modes": storage_modes,
    })

    expiry_text = get_premium_expiry_text(user_id) or f"{duration_days} days"

    features_str = "\n".join([f"• {f}" for f in features]) if features else "• Unlimited access"

    user_msg = (
        f"🎉 **Congratulations! Payment Verified!**\n\n"
        f"💎 **Plan:** `{plan_name}`\n"
        f"⏳ **Expiry:** `{expiry_text}`\n"
        f"📦 **Batch Limit:** `{batch_limit} Links`\n"
        f"⚡ **Parallel Tasks:** `{task_limit} Simultaneous`\n"
        f"☁️ **Storage Access:** `{storage_modes}`\n\n"
        f"**Plan Features:**\n{features_str}\n\n"
        f"🚀 Aapka premium plan activate ho chuka hai! Details dekhne ke liye /plan use karein."
    )

    try:
        await client.send_message(user_id, user_msg)
    except Exception as exc:
        debug_log(f"Failed to send plan activation message to user {user_id}: {exc}")

    log_msg = (
        f"🧾 **New Subscription Activated**\n\n"
        f"User: `{user_id}`\n"
        f"Order ID: `{order_id}`\n"
        f"Amount: `₹{order.get('amount', 0)}`\n"
        f"Plan: `{plan_name}`\n"
        f"Duration: `{duration_days} Days`\n"
        f"Verified via: `{verified_via}`\n"
        f"UTR: `{utr or order.get('utr_number') or 'Auto-Gateway'}`"
    )

    if LOG_CHANNEL:
        try:
            await client.send_message(LOG_CHANNEL, log_msg)
        except Exception:
            pass

    return True, f"Plan '{plan_name}' successfully activated for user {user_id}."
