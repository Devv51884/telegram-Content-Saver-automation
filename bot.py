from pyrogram import Client, filters
from pyrogram.errors import UserNotParticipant

from config import API_ID, API_HASH, BOT_TOKEN, SESSION_NAME, FORCE_SUB, OWNER_ID, ADMIN_IDS
from keyboards import (
    join_required_buttons, start_buttons, settings_home_buttons, submenu_nav,
    thumbnail_buttons, caption_buttons, simple_set_buttons, metadata_buttons, metadata_field_buttons
)
from texts import (
    start_text, help_text, plan_text, terms_text, settings_home_text, upload_mode_text,
    thumbnail_text, caption_text, prefix_text, suffix_text, auto_rename_text, destination_text,
    topic_id_text, replace_words_text, metadata_home_text, metadata_field_text,
    unknown_text, index_started_text, index_stopped_text, index_stats_text
)
from storage import (
    WAITING_KEYS,
    add_index_entry,
    ban_user,
    banned_count,
    clear_user_state,
    get_recent_users,
    get_user_settings,
    get_user_state,
    increase_index_user_count,
    is_banned,
    is_index_mode,
    register_user,
    reset_user_settings,
    set_index_mode,
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


def parse_index_entry(message):
    content_type = 'text'
    file_id = ''
    file_name = ''
    file_size = 0
    caption = message.caption or ''
    text = message.text or ''
    if message.photo:
        content_type = 'photo'
        file_id = message.photo.file_id
        file_size = getattr(message.photo, 'file_size', 0) or 0
    elif message.video:
        content_type = 'video'
        file_id = message.video.file_id
        file_name = getattr(message.video, 'file_name', '') or ''
        file_size = getattr(message.video, 'file_size', 0) or 0
    elif message.document:
        content_type = 'document'
        file_id = message.document.file_id
        file_name = getattr(message.document, 'file_name', '') or ''
        file_size = getattr(message.document, 'file_size', 0) or 0
    elif message.audio:
        content_type = 'audio'
        file_id = message.audio.file_id
        file_name = getattr(message.audio, 'file_name', '') or ''
        file_size = getattr(message.audio, 'file_size', 0) or 0
    elif message.voice:
        content_type = 'voice'
        file_id = message.voice.file_id
        file_size = getattr(message.voice, 'file_size', 0) or 0
    elif message.sticker:
        content_type = 'sticker'
        file_id = message.sticker.file_id
    return {
        'user_id': message.from_user.id,
        'chat_id': message.chat.id,
        'message_id': message.id,
        'content_type': content_type,
        'text': text,
        'caption': caption,
        'file_id': file_id,
        'file_name': file_name,
        'file_size': file_size,
    }


async def handle_admin_commands(client, message, lowered: str):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return False

    if lowered.startswith('/stats'):
        recent = get_recent_users(5)
        recent_text = '\n'.join([f"• {u.get('first_name') or 'User'} ({u.get('id')})" for u in recent]) or 'No recent users'
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
        await status.edit_text('📢 **Broadcast Complete**\n\n' f'✅ Sent: {sent}\n' f'❌ Failed: {failed}')
        return True

    if lowered.startswith('/index_id'):
        set_index_mode(user_id, True)
        await message.reply_text(index_started_text(user_id))
        return True

    if lowered.startswith('/stop_index'):
        set_index_mode(user_id, False)
        await message.reply_text(index_stopped_text(user_id))
        return True

    if lowered.startswith('/index_stats'):
        await message.reply_text(index_stats_text(user_id))
        return True

    return False


@app.on_callback_query()
async def all_callbacks(client, callback_query):
    user_id = callback_query.from_user.id
    data = callback_query.data

    if is_banned(user_id):
        await callback_query.answer('🚫 Aap bot use nahi kar sakte.', show_alert=True)
        return

    s = get_user_settings(user_id)

    if data == 'show_settings_home':
        text = settings_home_text(user_id)
        kb = settings_home_buttons()
    elif data == 'show_upload_mode':
        text = upload_mode_text()
        kb = submenu_nav()
    elif data == 'show_thumbnail':
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(s['thumbnail_enabled'])
    elif data == 'toggle_thumbnail_enabled':
        s['thumbnail_enabled'] = not s['thumbnail_enabled']
        update_user_settings(user_id, s)
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(s['thumbnail_enabled'])
    elif data == 'set_thumbnail_photo':
        set_user_state(user_id, 'set_thumbnail_photo')
        await callback_query.message.reply_text('🖼 Ab ek photo bhejo jise custom thumbnail save karna hai.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_thumbnail':
        update_user_settings(user_id, {'thumbnail_file_id': '', 'thumbnail_enabled': False})
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(False)
    elif data == 'show_caption':
        text = caption_text(user_id)
        kb = caption_buttons(s['caption_enabled'])
    elif data == 'toggle_caption_enabled':
        s['caption_enabled'] = not s['caption_enabled']
        update_user_settings(user_id, s)
        text = caption_text(user_id)
        kb = caption_buttons(s['caption_enabled'])
    elif data == 'set_caption_text':
        set_user_state(user_id, 'set_caption_text')
        await callback_query.message.reply_text('📝 Ab custom caption bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_caption':
        update_user_settings(user_id, {'caption_text': '', 'caption_enabled': False})
        text = caption_text(user_id)
        kb = caption_buttons(False)
    elif data == 'show_prefix':
        text = prefix_text(user_id)
        kb = simple_set_buttons('set_prefix', 'remove_prefix')
    elif data == 'set_prefix':
        set_user_state(user_id, 'set_prefix')
        await callback_query.message.reply_text('🏷 Ab prefix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_prefix':
        update_user_settings(user_id, {'prefix': ''})
        text = prefix_text(user_id)
        kb = simple_set_buttons('set_prefix', 'remove_prefix')
    elif data == 'show_suffix':
        text = suffix_text(user_id)
        kb = simple_set_buttons('set_suffix', 'remove_suffix')
    elif data == 'set_suffix':
        set_user_state(user_id, 'set_suffix')
        await callback_query.message.reply_text('🔖 Ab suffix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_suffix':
        update_user_settings(user_id, {'suffix': ''})
        text = suffix_text(user_id)
        kb = simple_set_buttons('set_suffix', 'remove_suffix')
    elif data == 'show_auto_rename':
        text = auto_rename_text(user_id)
        kb = simple_set_buttons('set_auto_rename', 'remove_auto_rename')
    elif data == 'set_auto_rename':
        set_user_state(user_id, 'set_auto_rename')
        await callback_query.message.reply_text('✍️ Ab auto rename value bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_auto_rename':
        update_user_settings(user_id, {'auto_rename': ''})
        text = auto_rename_text(user_id)
        kb = simple_set_buttons('set_auto_rename', 'remove_auto_rename')
    elif data == 'show_destination':
        text = destination_text(user_id)
        kb = simple_set_buttons('set_destination', 'remove_destination')
    elif data == 'set_destination':
        set_user_state(user_id, 'set_destination')
        await callback_query.message.reply_text('📍 Ab upload destination bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_destination':
        update_user_settings(user_id, {'upload_destination': ''})
        text = destination_text(user_id)
        kb = simple_set_buttons('set_destination', 'remove_destination')
    elif data == 'show_topic_id':
        text = topic_id_text(user_id)
        kb = simple_set_buttons('set_topic_id', 'remove_topic_id')
    elif data == 'set_topic_id':
        set_user_state(user_id, 'set_topic_id')
        await callback_query.message.reply_text('🧵 Ab topic id bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_topic_id':
        update_user_settings(user_id, {'topic_id': ''})
        text = topic_id_text(user_id)
        kb = simple_set_buttons('set_topic_id', 'remove_topic_id')
    elif data == 'show_replace_words':
        text = replace_words_text(user_id)
        kb = simple_set_buttons('set_replace_words', 'remove_replace_words')
    elif data == 'set_replace_words':
        set_user_state(user_id, 'set_replace_words')
        await callback_query.message.reply_text('🔁 Ab remove/replace rules bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_replace_words':
        update_user_settings(user_id, {'replace_words': ''})
        text = replace_words_text(user_id)
        kb = simple_set_buttons('set_replace_words', 'remove_replace_words')
    elif data == 'show_metadata':
        text = metadata_home_text(user_id)
        kb = metadata_buttons(s['metadata_enabled'])
    elif data == 'toggle_metadata_enabled':
        s['metadata_enabled'] = not s['metadata_enabled']
        update_user_settings(user_id, s)
        text = metadata_home_text(user_id)
        kb = metadata_buttons(s['metadata_enabled'])
    elif data == 'show_metadata_video_title':
        text = metadata_field_text(user_id, 'Video Title', 'metadata_video_title')
        kb = metadata_field_buttons('set_metadata_video_title', 'remove_metadata_video_title')
    elif data == 'set_metadata_video_title':
        set_user_state(user_id, 'set_metadata_video_title')
        await callback_query.message.reply_text('🎬 Ab Video Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_metadata_video_title':
        update_user_settings(user_id, {'metadata_video_title': ''})
        text = metadata_field_text(user_id, 'Video Title', 'metadata_video_title')
        kb = metadata_field_buttons('set_metadata_video_title', 'remove_metadata_video_title')
    elif data == 'show_metadata_video_author':
        text = metadata_field_text(user_id, 'Video Author', 'metadata_video_author')
        kb = metadata_field_buttons('set_metadata_video_author', 'remove_metadata_video_author')
    elif data == 'set_metadata_video_author':
        set_user_state(user_id, 'set_metadata_video_author')
        await callback_query.message.reply_text('👤 Ab Video Author bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_metadata_video_author':
        update_user_settings(user_id, {'metadata_video_author': ''})
        text = metadata_field_text(user_id, 'Video Author', 'metadata_video_author')
        kb = metadata_field_buttons('set_metadata_video_author', 'remove_metadata_video_author')
    elif data == 'show_metadata_audio_title':
        text = metadata_field_text(user_id, 'Audio Title', 'metadata_audio_title')
        kb = metadata_field_buttons('set_metadata_audio_title', 'remove_metadata_audio_title')
    elif data == 'set_metadata_audio_title':
        set_user_state(user_id, 'set_metadata_audio_title')
        await callback_query.message.reply_text('🎵 Ab Audio Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_metadata_audio_title':
        update_user_settings(user_id, {'metadata_audio_title': ''})
        text = metadata_field_text(user_id, 'Audio Title', 'metadata_audio_title')
        kb = metadata_field_buttons('set_metadata_audio_title', 'remove_metadata_audio_title')
    elif data == 'show_metadata_subtitle_title':
        text = metadata_field_text(user_id, 'Subtitle Title', 'metadata_subtitle_title')
        kb = metadata_field_buttons('set_metadata_subtitle_title', 'remove_metadata_subtitle_title')
    elif data == 'set_metadata_subtitle_title':
        set_user_state(user_id, 'set_metadata_subtitle_title')
        await callback_query.message.reply_text('💬 Ab Subtitle Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return
    elif data == 'remove_metadata_subtitle_title':
        update_user_settings(user_id, {'metadata_subtitle_title': ''})
        text = metadata_field_text(user_id, 'Subtitle Title', 'metadata_subtitle_title')
        kb = metadata_field_buttons('set_metadata_subtitle_title', 'remove_metadata_subtitle_title')
    elif data == 'reset_all_settings':
        reset_user_settings(user_id)
        clear_user_state(user_id)
        text = settings_home_text(user_id)
        kb = settings_home_buttons()
    elif data == 'close_settings':
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        await callback_query.answer('Closed')
        return
    else:
        await callback_query.answer('Unknown action')
        return

    try:
        await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass
    await callback_query.answer('✅ Updated')


@app.on_message(filters.private)
async def catch_all(client, message):
    register_user(message.from_user)
    user_id = message.from_user.id

    if is_banned(user_id):
        await message.reply_text('🚫 Aapko is bot se ban kiya gaya hai.')
        return

    text_raw = message.text or ''
    text = text_raw.strip()
    lowered = text.lower()

    # real-time indexing for admins in index mode
    if is_admin(user_id) and is_index_mode(user_id):
        if not lowered.startswith('/stop_index') and not lowered.startswith('/index_stats') and not lowered.startswith('/index_id'):
            entry = parse_index_entry(message)
            idx_no = add_index_entry(entry)
            user_count_now = increase_index_user_count(user_id)
            await message.reply_text(
                f'📚 Indexed successfully\n\n'
                f'Index No: **{idx_no}**\n'
                f'Type: **{entry["content_type"]}**\n'
                f'Your Total Indexed: **{user_count_now}**'
            )
            return

    state = get_user_state(user_id)
    if state and not lowered.startswith('/cancel'):
        setting_key = WAITING_KEYS.get(state)
        if setting_key == 'thumbnail_file_id':
            if message.photo:
                update_user_settings(user_id, {'thumbnail_file_id': message.photo.file_id, 'thumbnail_enabled': True})
                clear_user_state(user_id)
                await message.reply_text('✅ Custom thumbnail save ho gaya.\n\n/settings bhejo dekhne ke liye.')
                return
            else:
                await message.reply_text('❌ Thumbnail ke liye photo bhejna zaroori hai. /cancel bhej kar cancel kar sakte ho.')
                return
        if setting_key:
            update_user_settings(user_id, {setting_key: text})
            if setting_key == 'caption_text':
                update_user_settings(user_id, {'caption_enabled': True})
            if setting_key.startswith('metadata_'):
                update_user_settings(user_id, {'metadata_enabled': True})
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
        await message.reply_text(settings_home_text(user_id), reply_markup=settings_home_buttons())
        return

    blocked = await check_force_sub(client, message)
    if blocked:
        return

    await message.reply_text(unknown_text())
     