from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *


async def id_command_in_chat(client, message):
    topic_id = getattr(message, "message_thread_id", None)
    try:
        chat = await client.get_chat(message.chat.id)
        await message.reply_text(id_info_text(chat, topic_id), disable_web_page_preview=True)
    except Exception as e:
        await message.reply_text(f"ID fetch failed: {e}")


def should_ignore_private_update(message) -> bool:
    from_user = getattr(message, "from_user", None)
    if from_user is None:
        return True
    if bool(getattr(message, "outgoing", False)):
        return True
    if bool(getattr(from_user, "is_bot", False)):
        return True
    return False


def should_send_unknown_reply(message, text_raw: str) -> bool:
    text = str(text_raw or "").strip()
    if not text:
        return False
    if not text.startswith("/"):
        return False
    if "\n" in text:
        return False
    if len(text) > 160:
        return False
    if text.count("/") >= 2:
        return False
    if getattr(message, "reply_markup", None) is not None:
        return False
    return True


async def catch_all(client, message):
    try:
        user_info = f"{getattr(message.from_user, 'id', 'unknown')} (@{getattr(message.from_user, 'username', '') or getattr(message.from_user, 'first_name', '')})"
        text_preview = (message.text or message.caption or '<media>').replace('\n', ' ')[:80]
        print(f"[msg] Incoming from {user_info}: {text_preview}")
        return await handle_private_message(client, message)
    except Exception as exc:
        import traceback
        traceback.print_exc()


_MESSAGE_HANDLERS_REGISTERED = False


def register_message_handlers(app):
    global _MESSAGE_HANDLERS_REGISTERED
    if _MESSAGE_HANDLERS_REGISTERED:
        return
    app.on_message(filters.command("id") & (filters.group | filters.channel))(id_command_in_chat)
    app.on_message(filters.private & filters.incoming)(catch_all)
    _MESSAGE_HANDLERS_REGISTERED = True
