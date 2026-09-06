from __future__ import annotations

import asyncio
from runtime_context import LOG_CHANNEL
from services.task_service import debug_log
from config import FREE_MAX_BATCH_LINKS, FREE_MAX_TASKS_PER_USER
from storage import (
    get_all_premium_users,
    is_premium_expired,
    remove_premium,
    save_user_limit_record,
)


_EXPIRY_MONITOR_STARTED = False


async def check_and_revoke_expired_plans(client):
    try:
        premium_map = get_all_premium_users()
        for uid_str, record in list(premium_map.items()):
            if not record.get("is_premium"):
                continue
            try:
                uid = int(uid_str)
            except Exception:
                continue

            if is_premium_expired(uid):
                plan_name = str(record.get("plan_name") or "Premium")
                debug_log(f"Plan expired for user {uid} ({plan_name}). Revoking access...")
                remove_premium(uid)
                save_user_limit_record(uid, {
                    "batch_limit": FREE_MAX_BATCH_LINKS,
                    "task_limit": FREE_MAX_TASKS_PER_USER,
                    "allowed_storage_modes": "telegram",
                })

                msg = (
                    f"⚠️ **Subscription Expired!**\n\n"
                    f"Aapka **{plan_name}** period poora ho gaya hai aur access revoke kar diya gaya hai.\n\n"
                    f"**Current Free Limits:**\n"
                    f"• Batch Limit: `{FREE_MAX_BATCH_LINKS} Links`\n"
                    f"• Task Limit: `{FREE_MAX_TASKS_PER_USER} Tasks`\n"
                    f"• Storage: `Telegram Only`\n\n"
                    f"🚀 Naya plan lene ya renew karne ke liye /buy ya /plan use karein."
                )

                try:
                    await client.send_message(uid, msg)
                except Exception as exc:
                    debug_log(f"Failed to notify user {uid} about plan expiry: {exc}")

                if LOG_CHANNEL:
                    try:
                        await client.send_message(
                            LOG_CHANNEL,
                            f"🔒 **Plan Expired & Revoked**\nUser: `{uid}`\nPlan: `{plan_name}`",
                        )
                    except Exception:
                        pass
    except Exception as exc:
        debug_log(f"Error in check_and_revoke_expired_plans: {exc}")


async def _expiry_monitor_loop(client):
    while True:
        try:
            await check_and_revoke_expired_plans(client)
        except Exception:
            pass
        await asyncio.sleep(60)


def start_expiry_monitor_task(client):
    global _EXPIRY_MONITOR_STARTED
    if _EXPIRY_MONITOR_STARTED:
        return
    _EXPIRY_MONITOR_STARTED = True
    try:
        asyncio.create_task(_expiry_monitor_loop(client))
    except Exception:
        loop = getattr(client, "loop", None)
        if loop and loop.is_running():
            try:
                asyncio.run_coroutine_threadsafe(_expiry_monitor_loop(client), loop)
            except Exception as err:
                debug_log(f"start_expiry_monitor_task threadsafe failed: {err}")

