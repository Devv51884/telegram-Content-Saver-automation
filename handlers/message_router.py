from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from services.queue_task_service import *
from services.batch_transfer_service import *

async def handle_private_message(client, message):
    if should_ignore_private_update(message):
        return
    if is_duplicate_private_update(message):
        return

    register_user(message.from_user)
    user_id = message.from_user.id
    cleanup_expired_premium_users()

    blocked = await check_force_sub(client, message, user_id=user_id)
    if blocked:
        return

    if is_banned(user_id):
        await message.reply_text("ðŸš« Aapko is bot se ban kiya gaya hai.")
        return

    text_raw = message.text or message.caption or ""
    text = text_raw.strip()
    lowered = text.lower()
    state = get_user_state(user_id)

    if await handle_message_state_and_profile(client, message, user_id, text_raw, text, lowered, state):
        return

    ignored_cmds = (
        "/stop_index",
        "/index_stats",
        "/index_id",
        "/settings",
        "/cancel",
        "/cancelall",
        "/cancel_all",
        "/start",
        "/help",
        "/plan",
        "/terms",
        "/ping",
        "/login",
        "/login_status",
        "/logout",
        "/my_tasks",
        "/set_bot",
        "/bot_status",
        "/remove_bot",
        "/id",
        "/recent_users",
        "/set_batch_limit",
        "/set_task_limit",
        "/set_storage_access",
    )

    if not any(lowered.startswith(cmd) for cmd in ignored_cmds):
        batch_links = extract_batch_links_from_input(text_raw)
        if batch_links:
            await process_batch_links(client, user_id, message, text_raw, links=batch_links)
            return

        info = extract_telegram_link_info(text_raw)
        if info:
            await process_link_task(client, user_id, message, text_raw.strip())
            return

    if not state and is_media_message(message):
        if capture_relay_bridge_message(user_id, message):
            debug_log(f"Captured relay bridge message {getattr(message, 'id', 0)} for user {user_id}")
            return
        if should_ignore_direct_message_payload(user_id, message):
            debug_log(f"Ignored relay bridge message {getattr(message, 'id', 0)} for user {user_id}")
            return
        await enqueue_direct_message_task(client, user_id, message)
        return

    if await handle_message_commands(client, message, user_id, text_raw, lowered, state):
        return
