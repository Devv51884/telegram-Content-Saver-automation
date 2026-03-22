from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant

from config import API_ID, API_HASH, BOT_TOKEN, SESSION_NAME, FORCE_SUB
from keyboards import join_required_buttons, start_buttons, settings_buttons
from texts import start_text, help_text, plan_text, terms_text, settings_text, unknown_text
from storage import (
    WAITING_KEYS,
    clear_user_state,
    get_user_state,
    get_user_settings,
    reset_user_settings,
    set_user_state,
    update_user_settings,
)

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)


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


@app.on_message(filters.private)
async def catch_all(client, message):
    print('MESSAGE RECEIVED =>', repr(message.text))

    user_id = message.from_user.id
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
