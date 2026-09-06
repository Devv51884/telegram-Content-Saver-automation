from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *


async def check_join_again(client, callback_query):
    await callback_query.answer("Checking...")
    blocked = await check_force_sub(
        client,
        callback_query.message,
        user_id=callback_query.from_user.id,
        force_refresh=True,
    )
    if not blocked:
        await callback_query.message.reply_text("Join verify ho gaya.\nAb /start bhejo aur bot use karo.")


async def all_callbacks(client, callback_query):
    try:
        return await handle_all_callbacks(client, callback_query)
    except Exception as exc:
        if "QUERY_ID_INVALID" in str(exc):
            return
        raise


_CALLBACK_HANDLERS_REGISTERED = False


def register_callback_handlers(app):
    global _CALLBACK_HANDLERS_REGISTERED
    if _CALLBACK_HANDLERS_REGISTERED:
        return
    app.on_callback_query(filters.regex("check_join_again"))(check_join_again)
    app.on_callback_query()(all_callbacks)
    _CALLBACK_HANDLERS_REGISTERED = True
