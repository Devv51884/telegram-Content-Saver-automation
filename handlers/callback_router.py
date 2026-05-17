from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *

async def handle_all_callbacks(client, callback_query):
    if is_duplicate_callback_update(callback_query):
        return

    user_id = callback_query.from_user.id
    data = callback_query.data

    blocked = await check_force_sub(client, callback_query.message, user_id=user_id)
    if blocked:
        await callback_query.answer("Pehle required channel join karo.", show_alert=True)
        return

    if is_banned(user_id):
        await callback_query.answer("ðŸš« Aap bot use nahi kar sakte.", show_alert=True)
        return

    cleanup_expired_premium_users()
    s = get_user_settings(user_id)
    storage_mode = normalize_storage_mode(s.get("storage_mode", "telegram"))

    if storage_mode != "telegram" and is_telegram_only_settings_callback(data):
        try:
            await callback_query.message.edit_text(
                settings_home_text(user_id),
                reply_markup=build_settings_home_markup(user_id),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer(build_storage_mode_locked_callback_text(storage_mode), show_alert=True)
        return

    if await handle_admin_callbacks(client, callback_query, user_id, data):
        return

    if await handle_batch_task_callbacks(client, callback_query, user_id, data):
        return

    if await handle_storage_profile_callbacks(client, callback_query, user_id, data, s):
        return

    if await handle_settings_callbacks(client, callback_query, user_id, data, s):
        return

    await callback_query.answer("Unknown action")
    return

