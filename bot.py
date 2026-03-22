from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant

from config import API_ID, API_HASH, BOT_TOKEN, SESSION_NAME, FORCE_SUB, OWNER_ID, ADMIN_IDS
from keyboards import join_required_buttons, start_buttons, settings_buttons
from texts import start_text, help_text, plan_text, terms_text, settings_text, unknown_text
from storage import (
    WAITING_KEYS,
    ban_user,
    banned_count,
    clear_user_state,
    get_recent_users,
    get_user_settings,
    get_user_state,
    is_banned,
    register_user,
    reset_user_settings,
    set_user_state,
    unban_user,
    update_user_settings,
    user_count,
)

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_force_sub(client, message):
    if not FORCE_SUB:
        return False

    try:
        await client.get_chat_member(FORCE_SUB, message.from_user.id)
        return False
    except UserNotParticipant:
        await message.reply_text(
            '❌ Bot use karne ke liye pehle required Telegram channel join karna zaroori hai.\n\nChannel join karne ke baad dubara /start bhejo.',
            reply_markup=join_required_buttons(),
        )
        return True
    except Exception as e:
        await message.reply_text(f'⚠️ Join check me issue aa gaya:\n{e}\n\n/start dubara bhejo.')
        return True


@app.on_callback_query(filters.regex('check_join_again'))
async def check_join_again(client, callback_query):
    blocked = await check_force_sub(client, callback_query.message)
    if not blocked:
        await callback_query.message.reply_text('✅ Join verify ho gaya.\nAb /start bhejo aur bot use karo.')
    await callback_query.answer()


@app.on_callback_query()
async def all_callbacks(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if is_banned(user_id):
        await callback_query.answer('🚫 Aap bot use nahi kar sakte.', show_alert=True)
        return

    if data == 'toggle_upload_mode':
        s = get_user_settings(user_id)
        s['upload_mode'] = 'Document' if s['upload_mode'] == 'Telegram' else 'Telegram'
        update_user_settings(user_id, s)
    elif data == 'toggle_thumbnail':
        s = get_user_settings(user_id)
        s['thumbnail'] = not s['thumbnail']
        update_user_settings(user_id, s)
    elif data == 'toggle_caption':
        s = get_user_settings(user_id)
        s['caption'] = not s['caption']
        update_user_settings(user_id, s)
    elif data == 'toggle_metadata':
        s = get_user_settings(user_id)
        s['metadata'] = not s['metadata']
        update_user_settings(user_id, s)
    elif data in WAITING_KEYS:
        set_user_state(user_id, data)
        nice_name = WAITING_KEYS[data].replace('_', ' ').title()
        await callback_query.message.reply_text(f'✍️ Ab `{nice_name}` ki value bhejo.\n\nCancel karna ho to /cancel bhejo.')
        await callback_query.answer()
        return
    elif data == 'reset_all_settings':
        reset_user_settings(user_id)
        clear_user_state(user_id)

    try:
        await callback_query.message.edit_text(settings_text(user_id), reply_markup=settings_buttons())
    except Exception:
        pass

    await callback_query.answer('✅ Updated')


async def handle_admin_commands(client, message, lowered: str):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return False

    if lowered.startswith('/stats'):
        recent = get_recent_users(5)
        recent_text = '\n'.join(
            [f"• {u.get('first_name') or 'User'} ({u.get('id')})" for u in recent]
        ) or 'No recent users'
        await message.reply_text(
            '📊 **Bot Stats**\n\n'
            f'**Total Users:** {user_count()}\n'
            f'**Banned Users:** {banned_count()}\n'
            f'**Admins:** {len(ADMIN_IDS)}\n\n'
            f'**Recent Users:**\n{recent_text}'
        )
        return True

    if lowered.startswith('/users'):
        recent = get_recent_users(15)
        if not recent:
            await message.reply_text('Abhi tak koi user data nahi mila.')
            return True
        text = '👥 **Recent Users**\n\n' + '\n'.join(
            [f"• {u.get('first_name') or 'User'} | `{u.get('id')}` | @{u.get('username') or 'no_username'}" for u in recent]
        )
        await message.reply_text(text)
        return True

    if lowered.startswith('/ban'):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text('Use: /ban user_id')
            return True
        target = int(parts[1].strip())
        if target == OWNER_ID:
            await message.reply_text('Owner ko ban nahi kar sakte.')
            return True
        ban_user(target)
        await message.reply_text(f'🚫 User `{target}` ko ban kar diya gaya.')
        return True

    if lowered.startswith('/unban'):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text('Use: /unban user_id')
            return True
        target = int(parts[1].strip())
        unban_user(target)
        await message.reply_text(f'✅ User `{target}` ko unban kar diya gaya.')
        return True

    if lowered.startswith('/broadcast'):
        parts = message.text.split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip():
            await message.reply_text('Use: /broadcast your message')
            return True
        msg = parts[1].strip()
        users = get_recent_users(100000)
        sent = 0
        failed = 0
        status = await message.reply_text('📢 Broadcast start ho raha hai...')
        for u in users:
            uid = u.get('id')
            if not uid or is_banned(uid):
                continue
            try:
                await client.send_message(uid, f'📢 **Code Devil Broadcast**\n\n{msg}')
                sent += 1
            except Exception:
                failed += 1
        await status.edit_text(
            '📢 **Broadcast Complete**\n\n'
            f'✅ Sent: {sent}\n'
            f'❌ Failed: {failed}'
        )
        return True

    return False


@app.on_message(filters.private)
async def catch_all(client, message):
    print('MESSAGE RECEIVED =>', repr(message.text))
    register_user(message.from_user)

    user_id = message.from_user.id
    if is_banned(user_id):
        await message.reply_text('🚫 Aapko is bot se ban kiya gaya hai.')
        return

    text_raw = message.text or ''
    text = text_raw.strip()
    lowered = text.lower()

    state = get_user_state(user_id)
    if state and not lowered.startswith('/cancel'):
        setting_key = WAITING_KEYS.get(state)
        if setting_key:
            update_user_settings(user_id, {setting_key: text})
            clear_user_state(user_id)
            await message.reply_text(f"✅ `{setting_key.replace('_', ' ').title()}` update ho gaya.\n\n/settings bhejo dekhne ke liye.")
            return

    if await handle_admin_commands(client, message, lowered):
        return

    if lowered.startswith('/cancel'):
        clear_user_state(user_id)
        await message.reply_text('❌ Current input mode cancel kar diya gaya.')
        return

    if lowered.startswith('/ping'):
        await message.reply_text('✅ Bot online hai aur sahi se reply kar raha hai.')
        return

    if lowered.startswith('/start'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return
        await message.reply_text(start_text(), reply_markup=start_buttons(), disable_web_page_preview=True)
        return

    if lowered.startswith('/help'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return
        await message.reply_text(help_text())
        return

    if lowered.startswith('/plan'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return
        await message.reply_text(plan_text())
        return

    if lowered.startswith('/terms'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return
        await message.reply_text(terms_text())
        return

    if lowered.startswith('/settings'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return
        await message.reply_text(settings_text(user_id), reply_markup=settings_buttons())
        return

    blocked = await check_force_sub(client, message)
    if blocked:
        return

    await message.reply_text(unknown_text())
