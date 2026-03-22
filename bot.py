import os
import re
import uuid
import time

from pyrogram import Client, filters
from pyrogram.errors import (
    UserNotParticipant,
    SessionPasswordNeeded,
    PhoneCodeInvalid,
    PasswordHashInvalid,
    PhoneNumberInvalid,
    FloodWait,
)

from config import (
    API_ID,
    API_HASH,
    BOT_TOKEN,
    SESSION_NAME,
    FORCE_SUB,
    OWNER_ID,
    ADMIN_IDS,
    LOG_CHANNEL,
    TEMP_DIR,
    MAX_TASKS_PER_USER,
)

from keyboards import (
    join_required_buttons,
    start_buttons,
    settings_home_buttons,
    submenu_nav,
    thumbnail_buttons,
    caption_buttons,
    caption_index_buttons,
    simple_set_buttons,
    metadata_buttons,
    metadata_field_buttons,
    index_buttons,
    login_buttons,
    task_buttons,
    my_tasks_buttons,
    auto_rename_buttons,
    filename_index_buttons,
)

from texts import (
    start_text,
    help_text,
    plan_text,
    terms_text,
    settings_home_text,
    upload_mode_text,
    thumbnail_text,
    caption_text,
    prefix_text,
    suffix_text,
    auto_rename_text,
    destination_text,
    topic_id_text,
    replace_words_text,
    metadata_home_text,
    metadata_field_text,
    unknown_text,
    index_started_text,
    index_stopped_text,
    index_stats_text,
    index_info_text,
    login_intro_text,
    ask_phone_text,
    ask_code_text,
    ask_password_text,
    login_success_text,
    login_failed_text,
    login_status_text,
    logout_success_text,
    logout_missing_text,
    task_running_text,
    task_completed_text,
    task_failed_text,
    my_tasks_text,
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
    save_user_session,
    get_user_session_string,
    has_user_session,
    delete_user_session,
    set_login_temp,
    get_login_temp,
    set_task,
    get_task,
    get_user_tasks,
    count_running_tasks,
    format_index_number,
)

app = Client(
    SESSION_NAME,
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN,
    in_memory=True,
)

TEMP_LOGIN_CLIENTS = {}


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


def normalize_target(target: str):
    target = (target or "").strip()
    if not target:
        return None
    if target.lstrip("-").isdigit():
        return int(target)
    if target.startswith("@"):
        return target
    return target


def safe_topic_id(value: str):
    value = (value or "").strip()
    if value.isdigit():
        return int(value)
    return None


def make_task_id() -> str:
    return uuid.uuid4().hex[:12]


def sanitize_filename(name: str) -> str:
    if not name:
        return "file"
    for ch in ['\\', '/', ':', '*', '?', '"', '<', '>', '|']:
        name = name.replace(ch, ' ')
    return ' '.join(name.split()).strip() or "file"


def split_filename_ext(filename: str):
    filename = filename or ""
    if "." in filename:
        base, ext = os.path.splitext(filename)
        return base, ext
    return filename, ""


def apply_replace_rules(value: str, rules: str) -> str:
    value = value or ""
    rules = (rules or "").strip()
    if not rules:
        return value

    for part in rules.split(","):
        part = part.strip()
        if not part:
            continue
        if ":" in part:
            old, new = part.split(":", 1)
            value = value.replace(old.strip(), new.strip())
        else:
            value = value.replace(part, "")
    return " ".join(value.split()).strip()


def build_template_context(source_msg, settings: dict, index_no: int = 0):
    filename = ""
    if source_msg.document and getattr(source_msg.document, "file_name", None):
        filename = source_msg.document.file_name
    elif source_msg.video and getattr(source_msg.video, "file_name", None):
        filename = source_msg.video.file_name
    elif source_msg.audio and getattr(source_msg.audio, "file_name", None):
        filename = source_msg.audio.file_name
    elif source_msg.photo:
        filename = "photo.jpg"
    elif source_msg.voice:
        filename = "voice.ogg"
    elif source_msg.animation:
        filename = "animation.mp4"

    filename = sanitize_filename(filename)
    filename = apply_replace_rules(filename, settings.get("replace_words", ""))

    caption_padding = int(settings.get("caption_index_padding", 2) or 2)
    caption_start = int(settings.get("caption_index_start", 1) or 1)
    filename_padding = int(settings.get("filename_index_padding", 2) or 2)
    filename_start = int(settings.get("filename_index_start", 1) or 1)

    caption_index_value = format_index_number(max(0, caption_start + max(0, index_no - 1)), caption_padding)
    filename_index_value = format_index_number(max(0, filename_start + max(0, index_no - 1)), filename_padding)

    size = ""
    if source_msg.document:
        size = str(getattr(source_msg.document, "file_size", "") or "")
    elif source_msg.video:
        size = str(getattr(source_msg.video, "file_size", "") or "")
    elif source_msg.audio:
        size = str(getattr(source_msg.audio, "file_size", "") or "")
    elif source_msg.photo:
        size = str(getattr(source_msg.photo, "file_size", "") or "")
    elif source_msg.voice:
        size = str(getattr(source_msg.voice, "file_size", "") or "")

    duration = ""
    if source_msg.video:
        duration = str(getattr(source_msg.video, "duration", "") or "")
    elif source_msg.audio:
        duration = str(getattr(source_msg.audio, "duration", "") or "")
    elif source_msg.voice:
        duration = str(getattr(source_msg.voice, "duration", "") or "")

    return {
        "filename": filename,
        "size": size,
        "duration": duration,
        "quality": "",
        "language": "",
        "subtitle": "",
        "index": caption_index_value,
        "fileindex": filename_index_value,
    }


def render_template(template: str, context: dict) -> str:
    result = template or ""
    for key, value in context.items():
        result = result.replace("{" + key + "}", str(value))
    return result


def build_final_caption(source_msg, settings: dict, index_no: int = 0):
    context = build_template_context(source_msg, settings, index_no=index_no)

    caption = source_msg.caption or ""
    if settings.get("caption_enabled") and settings.get("caption_text"):
        caption = render_template(settings.get("caption_text", ""), context)

    caption = apply_replace_rules(caption, settings.get("replace_words", ""))

    prefix = settings.get("prefix", "").strip()
    suffix = settings.get("suffix", "").strip()

    if caption:
        if prefix:
            caption = f"{prefix} {caption}".strip()
        if suffix:
            caption = f"{caption} {suffix}".strip()

    return caption


def build_final_text(text: str, source_msg, settings: dict, index_no: int = 0):
    context = build_template_context(source_msg, settings, index_no=index_no)

    value = text or ""
    if settings.get("caption_enabled") and settings.get("caption_text"):
        value = render_template(settings.get("caption_text", value), context)

    value = apply_replace_rules(value, settings.get("replace_words", ""))

    prefix = settings.get("prefix", "").strip()
    suffix = settings.get("suffix", "").strip()

    if prefix:
        value = f"{prefix} {value}".strip()
    if suffix:
        value = f"{value} {suffix}".strip()

    return value


def build_final_filename(original_filename: str, settings: dict, index_no: int = 0):
    original_filename = sanitize_filename(original_filename or "file")
    original_filename = apply_replace_rules(original_filename, settings.get("replace_words", ""))

    base, ext = split_filename_ext(original_filename)

    filename_padding = int(settings.get("filename_index_padding", 2) or 2)
    filename_start = int(settings.get("filename_index_start", 1) or 1)
    filename_index_value = format_index_number(max(0, filename_start + max(0, index_no - 1)), filename_padding)

    context = {
        "filename": base,
        "index": filename_index_value,
    }

    rename_template = (settings.get("rename_template") or "").strip()
    auto_rename = (settings.get("auto_rename") or "").strip()

    new_base = base

    if rename_template:
        new_base = render_template(rename_template, context).strip()
    elif settings.get("auto_rename_enabled") and auto_rename:
        if "{filename}" in auto_rename or "{index}" in auto_rename:
            new_base = render_template(auto_rename, context).strip()
        else:
            new_base = auto_rename.strip()

    if settings.get("filename_index_enabled") and "{index}" not in new_base:
        new_base = f"{filename_index_value}_{new_base}".strip("_ ")

    file_prefix = (settings.get("filename_prefix") or "").strip()
    file_suffix = (settings.get("filename_suffix") or "").strip()

    if file_prefix:
        new_base = f"{file_prefix} {new_base}".strip()
    if file_suffix:
        new_base = f"{new_base} {file_suffix}".strip()

    new_base = apply_replace_rules(new_base, settings.get("replace_words", ""))
    new_base = sanitize_filename(new_base)

    return f"{new_base}{ext}"


async def update_task_status_message(client, task_id: str, done: bool = False):
    task = get_task(task_id)
    if not task:
        return

    chat_id = task.get("status_chat_id")
    message_id = task.get("status_message_id")
    if not chat_id or not message_id:
        return

    try:
        text = task_completed_text(task) if done and task.get("status") == "completed" else (
            task_failed_text(task) if done and task.get("status") == "failed" else task_running_text(task)
        )
        await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=task_buttons(task_id, done=done),
            disable_web_page_preview=True,
        )
    except Exception:
        pass


async def create_task_status_message(message, task_id: str):
    task = get_task(task_id)
    if not task:
        return

    sent = await message.reply_text(
        task_running_text(task),
        reply_markup=task_buttons(task_id, done=False),
        disable_web_page_preview=True,
    )

    set_task(task_id, {
        "status_chat_id": sent.chat.id,
        "status_message_id": sent.id,
    })


async def throttled_progress_update(client, task_id: str):
    task = get_task(task_id)
    if not task:
        return

    now = time.time()
    last = float(task.get("last_ui_update", 0) or 0)
    if now - last < 2:
        return

    set_task(task_id, {"last_ui_update": now})
    await update_task_status_message(client, task_id, done=False)


async def progress_callback(current, total, client, task_id: str, stage: str):
    percent = 0
    if total:
        percent = round((current / total) * 100, 2)

    set_task(task_id, {
        "status": stage,
        "progress_text": f"{percent:.2f}% ({current}/{total})",
    })
    await throttled_progress_update(client, task_id)


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
        'user_id': message.from_user.id if message.from_user else 0,
        'chat_id': message.chat.id if message.chat else 0,
        'message_id': message.id,
        'content_type': content_type,
        'text': text,
        'caption': caption,
        'file_id': file_id,
        'file_name': file_name,
        'file_size': file_size,
    }


def extract_telegram_link_info(text: str):
    if not text:
        return None

    text = text.strip()

    public_match = re.search(r"https?://t\.me/([A-Za-z0-9_]+)/(\d+)", text)
    private_match = re.search(r"https?://t\.me/c/(\d+)/(\d+)", text)

    if private_match:
        raw_chat_id = private_match.group(1)
        msg_id = int(private_match.group(2))
        chat_id = int(f"-100{raw_chat_id}")
        return {"chat_id": chat_id, "message_id": msg_id, "link_type": "private"}

    if public_match:
        username = public_match.group(1)
        msg_id = int(public_match.group(2))
        if username.lower() != "c":
            return {"chat_id": username, "message_id": msg_id, "link_type": "public"}

    return None


def get_temp_download_path(source_msg):
    os.makedirs(TEMP_DIR, exist_ok=True)
    base_name = f"cd_{int(time.time())}_{source_msg.id}"

    if source_msg.document and getattr(source_msg.document, "file_name", None):
        return os.path.join(TEMP_DIR, source_msg.document.file_name)

    if source_msg.video and getattr(source_msg.video, "file_name", None):
        return os.path.join(TEMP_DIR, source_msg.video.file_name)

    if source_msg.audio and getattr(source_msg.audio, "file_name", None):
        return os.path.join(TEMP_DIR, source_msg.audio.file_name)

    if source_msg.photo:
        return os.path.join(TEMP_DIR, f"{base_name}.jpg")

    if source_msg.voice:
        return os.path.join(TEMP_DIR, f"{base_name}.ogg")

    if source_msg.animation:
        return os.path.join(TEMP_DIR, f"{base_name}.mp4")

    return os.path.join(TEMP_DIR, f"{base_name}.bin")


def rename_downloaded_file(file_path: str, source_msg, settings: dict, index_no: int = 0):
    if not file_path or not os.path.exists(file_path):
        return file_path

    original_name = os.path.basename(file_path)
    final_name = build_final_filename(original_name, settings, index_no=index_no)
    final_path = os.path.join(os.path.dirname(file_path), final_name)

    if final_path == file_path:
        return file_path

    try:
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(file_path, final_path)
        return final_path
    except Exception:
        return file_path


async def get_authorized_client_for_user(user_id: int):
    session_string = get_user_session_string(user_id)
    if not session_string:
        return None

    client = Client(
        name=f"user_session_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True,
    )
    await client.connect()
    return client


async def fetch_message_via_best_client(bot_client, user_id: int, link_text: str):
    info = extract_telegram_link_info(link_text)
    if not info:
        return None, None, None

    try:
        msg = await bot_client.get_messages(info["chat_id"], info["message_id"])
        if msg:
            return msg, info, None
    except Exception:
        pass

    if has_user_session(user_id):
        user_client = await get_authorized_client_for_user(user_id)
        try:
            msg = await user_client.get_messages(info["chat_id"], info["message_id"])
            if msg:
                return msg, info, user_client
        except Exception:
            await user_client.disconnect()
            raise

    return None, info, None


async def upload_file_to_target(client, task_id: str, target, file_path: str, source_msg, settings: dict, index_no: int = 0):
    caption = build_final_caption(source_msg, settings, index_no=index_no)
    topic_id = safe_topic_id(settings.get("topic_id", ""))

    if source_msg.photo:
        return await client.send_photo(
            chat_id=target,
            photo=file_path,
            caption=caption if caption else None,
            message_thread_id=topic_id if topic_id else None,
            progress=progress_callback,
            progress_args=(client, task_id, "uploading"),
        )

    if source_msg.video or source_msg.animation:
        return await client.send_video(
            chat_id=target,
            video=file_path,
            caption=caption if caption else None,
            message_thread_id=topic_id if topic_id else None,
            progress=progress_callback,
            progress_args=(client, task_id, "uploading"),
        )

    if source_msg.audio:
        return await client.send_audio(
            chat_id=target,
            audio=file_path,
            caption=caption if caption else None,
            message_thread_id=topic_id if topic_id else None,
            progress=progress_callback,
            progress_args=(client, task_id, "uploading"),
        )

    if source_msg.voice:
        return await client.send_voice(
            chat_id=target,
            voice=file_path,
            caption=caption if caption else None,
            message_thread_id=topic_id if topic_id else None,
            progress=progress_callback,
            progress_args=(client, task_id, "uploading"),
        )

    return await client.send_document(
        chat_id=target,
        document=file_path,
        caption=caption if caption else None,
        message_thread_id=topic_id if topic_id else None,
        progress=progress_callback,
        progress_args=(client, task_id, "uploading"),
    )


async def send_text_to_target(client, target, source_msg, settings: dict, index_no: int = 0):
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    final_text = build_final_text(source_msg.text or source_msg.caption or "", source_msg, settings, index_no=index_no)

    return await client.send_message(
        chat_id=target,
        text=final_text or " ",
        message_thread_id=topic_id if topic_id else None,
        disable_web_page_preview=True,
    )


async def process_link_task(client, user_id: int, message, link_text: str):
    if count_running_tasks(user_id) >= MAX_TASKS_PER_USER:
        await message.reply_text(
            f'⚠️ Ek time par max {MAX_TASKS_PER_USER} running tasks allowed hain.'
        )
        return

    task_id = make_task_id()
    settings = get_user_settings(user_id)
    destination = normalize_target(settings.get("upload_destination", ""))

    set_task(task_id, {
        "task_id": task_id,
        "user_id": user_id,
        "source": link_text.strip(),
        "destination": str(destination or "Not Set"),
        "status": "queued",
        "progress_text": "",
        "error": "",
        "created_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    })

    await create_task_status_message(message, task_id)

    user_client = None
    download_path = None

    try:
        set_task(task_id, {"status": "fetching", "progress_text": "Finding source message..."})
        await update_task_status_message(client, task_id)

        source_msg, info, user_client = await fetch_message_via_best_client(client, user_id, link_text)

        if not source_msg:
            set_task(task_id, {
                "status": "failed",
                "error": "Source message fetch nahi ho paya. Public access ya authorized login required."
            })
            await update_task_status_message(client, task_id, done=True)
            return

        entry = {
            'user_id': user_id,
            'chat_id': getattr(source_msg.chat, 'id', 0) if getattr(source_msg, 'chat', None) else 0,
            'message_id': source_msg.id,
            'content_type': (
                'photo' if source_msg.photo else
                'video' if source_msg.video else
                'document' if source_msg.document else
                'audio' if source_msg.audio else
                'voice' if source_msg.voice else
                'sticker' if source_msg.sticker else
                'text'
            ),
            'text': source_msg.text or '',
            'caption': source_msg.caption or '',
            'file_id': (
                source_msg.photo.file_id if source_msg.photo else
                source_msg.video.file_id if source_msg.video else
                source_msg.document.file_id if source_msg.document else
                source_msg.audio.file_id if source_msg.audio else
                source_msg.voice.file_id if source_msg.voice else
                source_msg.sticker.file_id if source_msg.sticker else
                ''
            ),
            'file_name': (
                getattr(source_msg.video, 'file_name', '') if source_msg.video else
                getattr(source_msg.document, 'file_name', '') if source_msg.document else
                getattr(source_msg.audio, 'file_name', '') if source_msg.audio else
                ''
            ),
            'file_size': (
                getattr(source_msg.photo, 'file_size', 0) if source_msg.photo else
                getattr(source_msg.video, 'file_size', 0) if source_msg.video else
                getattr(source_msg.document, 'file_size', 0) if source_msg.document else
                getattr(source_msg.audio, 'file_size', 0) if source_msg.audio else
                getattr(source_msg.voice, 'file_size', 0) if source_msg.voice else
                0
            ),
            'source_link': link_text.strip(),
            'link_type': info.get('link_type') if info else '',
        }

        idx_no = add_index_entry(entry)
        user_count_now = increase_index_user_count(user_id)

        if not (source_msg.photo or source_msg.video or source_msg.document or source_msg.audio or source_msg.voice or source_msg.animation):
            set_task(task_id, {"status": "uploading", "progress_text": "Sending text/message..."})
            await update_task_status_message(client, task_id)

            if destination:
                await send_text_to_target(client, destination, source_msg, settings, index_no=idx_no)

            if LOG_CHANNEL:
                await send_text_to_target(client, LOG_CHANNEL, source_msg, settings, index_no=idx_no)

            set_task(task_id, {
                "status": "completed",
                "progress_text": f"Index {idx_no} | Count {user_count_now}"
            })
            await update_task_status_message(client, task_id, done=True)

            await message.reply_text(
                f'⚡ **Auto Link Process Done (V7)**\n\n'
                f'📚 Index No: **{idx_no}**\n'
                f'📦 Type: **{entry["content_type"]}**\n'
                f'📊 Your Total Indexed: **{user_count_now}**\n'
                f'📍 Destination: **{destination or "Not Set"}**\n'
                f'🔗 Link Type: **{entry["link_type"] or "unknown"}**'
            )
            return

        set_task(task_id, {"status": "downloading", "progress_text": "Starting download..."})
        await update_task_status_message(client, task_id)

        download_path = get_temp_download_path(source_msg)
        source_client = user_client if user_client else client

        await source_client.download_media(
            source_msg,
            file_name=download_path,
            progress=progress_callback,
            progress_args=(client, task_id, "downloading"),
        )

        download_path = rename_downloaded_file(download_path, source_msg, settings, index_no=idx_no)

        set_task(task_id, {"status": "uploading", "progress_text": "Preparing upload..."})
        await update_task_status_message(client, task_id)

        if destination:
            await upload_file_to_target(client, task_id, destination, download_path, source_msg, settings, index_no=idx_no)

        if LOG_CHANNEL:
            await upload_file_to_target(client, task_id, LOG_CHANNEL, download_path, source_msg, settings, index_no=idx_no)

        set_task(task_id, {
            "status": "completed",
            "progress_text": f"Index {idx_no} | Count {user_count_now}"
        })
        await update_task_status_message(client, task_id, done=True)

        await message.reply_text(
            f'⚡ **Auto Link Process Done (V7)**\n\n'
            f'📚 Index No: **{idx_no}**\n'
            f'📦 Type: **{entry["content_type"]}**\n'
            f'📊 Your Total Indexed: **{user_count_now}**\n'
            f'📍 Destination: **{destination or "Not Set"}**\n'
            f'🔗 Link Type: **{entry["link_type"] or "unknown"}**'
        )

    except FloodWait as e:
        set_task(task_id, {"status": "failed", "error": f"FloodWait: wait {e.value}s"})
        await update_task_status_message(client, task_id, done=True)
        await message.reply_text(f'❌ FloodWait: {e.value}s wait karo.')
    except Exception as e:
        set_task(task_id, {"status": "failed", "error": str(e)})
        await update_task_status_message(client, task_id, done=True)
        await message.reply_text(f'❌ Task failed:\n{e}')
    finally:
        if user_client:
            try:
                await user_client.disconnect()
            except Exception:
                pass
        if download_path and os.path.exists(download_path):
            try:
                os.remove(download_path)
            except Exception:
                pass


async def start_login_client(user_id: int):
    login_client = Client(
        name=f"login_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
    )
    await login_client.connect()
    TEMP_LOGIN_CLIENTS[user_id] = login_client
    return login_client


async def get_or_create_login_client(user_id: int):
    existing = TEMP_LOGIN_CLIENTS.get(user_id)
    if existing:
        return existing
    return await start_login_client(user_id)


async def cleanup_login_client(user_id: int):
    client = TEMP_LOGIN_CLIENTS.pop(user_id, None)
    if client:
        try:
            await client.disconnect()
        except Exception:
            pass


async def begin_login_flow(user_id: int, phone: str):
    login_client = await get_or_create_login_client(user_id)
    sent = await login_client.send_code(phone)
    set_login_temp(user_id, "phone", phone)
    set_login_temp(user_id, "phone_code_hash", sent.phone_code_hash)
    set_user_state(user_id, "login_code")


async def finish_login_with_code(user_id: int, code: str):
    phone = get_login_temp(user_id, "phone", "")
    phone_code_hash = get_login_temp(user_id, "phone_code_hash", "")

    if not phone or not phone_code_hash:
        raise RuntimeError("Login session data missing. Dobara /login try karo.")

    login_client = await get_or_create_login_client(user_id)

    try:
        await login_client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=code,
        )
    except SessionPasswordNeeded:
        set_user_state(user_id, "login_password")
        raise

    me = await login_client.get_me()
    session_string = await login_client.export_session_string()
    save_user_session(user_id, session_string, tg_user_id=me.id, phone=phone)
    clear_user_state(user_id)
    await cleanup_login_client(user_id)
    return me, phone


async def finish_login_with_password(user_id: int, password: str):
    phone = get_login_temp(user_id, "phone", "")
    login_client = await get_or_create_login_client(user_id)
    await login_client.check_password(password=password)

    me = await login_client.get_me()
    session_string = await login_client.export_session_string()
    save_user_session(user_id, session_string, tg_user_id=me.id, phone=phone)
    clear_user_state(user_id)
    await cleanup_login_client(user_id)
    return me, phone


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

        await status.edit_text(
            '📢 **Broadcast Complete**\n\n'
            f'✅ Sent: {sent}\n'
            f'❌ Failed: {failed}'
        )
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

    if data.startswith('task_refresh:'):
        task_id = data.split(':', 1)[1]
        await update_task_status_message(client, task_id, done=get_task(task_id).get("status") in {"completed", "failed", "cancelled"})
        await callback_query.answer('♻️ Refreshed')
        return

    elif data.startswith('task_cancel:'):
        task_id = data.split(':', 1)[1]
        task = get_task(task_id)
        if task:
            set_task(task_id, {"status": "cancelled", "error": "Cancelled by user"})
            await update_task_status_message(client, task_id, done=True)
        await callback_query.answer('🛑 Cancelled')
        return

    elif data == 'show_my_tasks':
        tasks = get_user_tasks(user_id, limit=10)
        try:
            await callback_query.message.edit_text(
                my_tasks_text(tasks),
                reply_markup=my_tasks_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    elif data == 'show_login_info':
        try:
            await callback_query.message.edit_text(
                login_intro_text(),
                reply_markup=login_buttons(has_user_session(user_id)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    elif data == 'show_login_status':
        try:
            await callback_query.message.edit_text(
                login_status_text(user_id),
                reply_markup=login_buttons(has_user_session(user_id)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    elif data == 'start_login_flow':
        set_user_state(user_id, 'login_phone')
        try:
            await callback_query.message.edit_text(
                ask_phone_text(),
                reply_markup=login_buttons(has_user_session(user_id)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return

    elif data == 'do_logout':
        if has_user_session(user_id):
            delete_user_session(user_id)
            await cleanup_login_client(user_id)
            try:
                await callback_query.message.edit_text(
                    logout_success_text(),
                    reply_markup=login_buttons(False),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        else:
            try:
                await callback_query.message.edit_text(
                    logout_missing_text(),
                    reply_markup=login_buttons(False),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        await callback_query.answer()
        return

    if data == 'show_settings_home':
        text = settings_home_text(user_id)
        kb = settings_home_buttons(has_user_session(user_id))

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

    elif data == 'show_caption_index_settings':
        text = caption_text(user_id)
        kb = caption_index_buttons(s.get('caption_index_enabled', True))

    elif data == 'toggle_caption_index_enabled':
        s['caption_index_enabled'] = not s.get('caption_index_enabled', True)
        update_user_settings(user_id, s)
        text = caption_text(user_id)
        kb = caption_index_buttons(s.get('caption_index_enabled', True))

    elif data == 'set_caption_index_padding':
        set_user_state(user_id, 'set_caption_index_padding')
        await callback_query.message.reply_text('🔢 Ab caption index padding bhejo.\nExample: 2\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'set_caption_index_start':
        set_user_state(user_id, 'set_caption_index_start')
        await callback_query.message.reply_text('🚀 Ab caption index start value bhejo.\nExample: 1\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'set_caption_text':
        set_user_state(user_id, 'set_caption_text')
        await callback_query.message.reply_text('📝 Ab custom caption bhejo.\n{index} use kar sakte ho.\n\n/cancel bhej kar cancel kar sakte ho.')
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
        kb = auto_rename_buttons(s.get('auto_rename_enabled', False))

    elif data == 'toggle_auto_rename_enabled':
        s['auto_rename_enabled'] = not s.get('auto_rename_enabled', False)
        update_user_settings(user_id, s)
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(s.get('auto_rename_enabled', False))

    elif data == 'set_auto_rename':
        set_user_state(user_id, 'set_auto_rename')
        await callback_query.message.reply_text('✍️ Ab simple auto rename value bhejo.\n{index} aur {filename} use kar sakte ho.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'set_rename_template':
        set_user_state(user_id, 'set_rename_template')
        await callback_query.message.reply_text('🧩 Ab rename template bhejo.\nExample: Movie_{index}\nYa: {index}_{filename}\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'set_filename_prefix':
        set_user_state(user_id, 'set_filename_prefix')
        await callback_query.message.reply_text('🏷 Ab filename prefix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'set_filename_suffix':
        set_user_state(user_id, 'set_filename_suffix')
        await callback_query.message.reply_text('🔖 Ab filename suffix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'show_filename_index_settings':
        text = auto_rename_text(user_id)
        kb = filename_index_buttons(s.get('filename_index_enabled', False))

    elif data == 'toggle_filename_index_enabled':
        s['filename_index_enabled'] = not s.get('filename_index_enabled', False)
        update_user_settings(user_id, s)
        text = auto_rename_text(user_id)
        kb = filename_index_buttons(s.get('filename_index_enabled', False))

    elif data == 'set_filename_index_padding':
        set_user_state(user_id, 'set_filename_index_padding')
        await callback_query.message.reply_text('🔢 Ab filename index padding bhejo.\nExample: 2\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'set_filename_index_start':
        set_user_state(user_id, 'set_filename_index_start')
        await callback_query.message.reply_text('🚀 Ab filename index start value bhejo.\nExample: 1\n\n/cancel bhej kar cancel kar sakte ho.')
        await callback_query.answer()
        return

    elif data == 'remove_auto_rename':
        update_user_settings(user_id, {
            'auto_rename': '',
            'rename_template': '',
            'filename_prefix': '',
            'filename_suffix': '',
            'auto_rename_enabled': False,
            'filename_index_enabled': False,
        })
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(False)

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
        await callback_query.message.reply_text('🔁 Ab remove/replace rules bhejo.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.')
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

    elif data == 'show_index_settings':
        text = index_info_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == 'toggle_index_mode':
        current = is_index_mode(user_id)
        set_index_mode(user_id, not current)
        text = settings_home_text(user_id)
        kb = settings_home_buttons(has_user_session(user_id))

    elif data == 'show_index_stats':
        text = index_stats_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == 'show_index_info':
        text = index_info_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == 'reset_all_settings':
        reset_user_settings(user_id)
        clear_user_state(user_id)
        text = settings_home_text(user_id)
        kb = settings_home_buttons(has_user_session(user_id))

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

    state = get_user_state(user_id)

    if state == 'login_phone' and not lowered.startswith('/cancel'):
        phone = text.replace(" ", "")
        try:
            await begin_login_flow(user_id, phone)
            await message.reply_text(ask_code_text())
            return
        except PhoneNumberInvalid:
            await message.reply_text(login_failed_text("Invalid phone number."))
            return
        except FloodWait as e:
            await message.reply_text(login_failed_text(f"FloodWait: {e.value}s"))
            return
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return

    if state == 'login_code' and not lowered.startswith('/cancel'):
        code = text.replace(" ", "")
        try:
            me, phone = await finish_login_with_code(user_id, code)
            await message.reply_text(login_success_text(phone))
            return
        except SessionPasswordNeeded:
            await message.reply_text(ask_password_text())
            return
        except PhoneCodeInvalid:
            await message.reply_text(login_failed_text("Invalid OTP / code."))
            return
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return

    if state == 'login_password' and not lowered.startswith('/cancel'):
        try:
            me, phone = await finish_login_with_password(user_id, text)
            await message.reply_text(login_success_text(phone))
            return
        except PasswordHashInvalid:
            await message.reply_text(login_failed_text("Wrong password."))
            return
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return

    if is_index_mode(user_id):
        ignored_cmds = (
            '/stop_index',
            '/index_stats',
            '/index_id',
            '/settings',
            '/cancel',
            '/start',
            '/help',
            '/plan',
            '/terms',
            '/ping',
            '/login',
            '/login_status',
            '/logout',
            '/my_tasks',
        )

        if not any(lowered.startswith(cmd) for cmd in ignored_cmds):
            info = extract_telegram_link_info(text_raw)
            if info:
                await process_link_task(client, user_id, message, text_raw.strip())
                return

    if state and not lowered.startswith('/cancel'):
        setting_key = WAITING_KEYS.get(state)

        if setting_key == 'thumbnail_file_id':
            if message.photo:
                update_user_settings(
                    user_id,
                    {
                        'thumbnail_file_id': message.photo.file_id,
                        'thumbnail_enabled': True
                    }
                )
                clear_user_state(user_id)
                await message.reply_text('✅ Custom thumbnail save ho gaya.\n\n/settings bhejo dekhne ke liye.')
                return
            else:
                await message.reply_text('❌ Thumbnail ke liye photo bhejna zaroori hai. /cancel bhej kar cancel kar sakte ho.')
                return

        if setting_key:
            value = text

            if setting_key in {
                'caption_index_padding',
                'caption_index_start',
                'filename_index_padding',
                'filename_index_start',
            }:
                if not value.isdigit():
                    await message.reply_text('❌ Yahan sirf number bhejo.\n/cancel bhej kar cancel kar sakte ho.')
                    return
                value = int(value)

            update_user_settings(user_id, {setting_key: value})

            if setting_key == 'caption_text':
                update_user_settings(user_id, {'caption_enabled': True})

            if setting_key in {'auto_rename', 'rename_template', 'filename_prefix', 'filename_suffix'}:
                update_user_settings(user_id, {'auto_rename_enabled': True})

            if setting_key.startswith('metadata_'):
                update_user_settings(user_id, {'metadata_enabled': True})

            clear_user_state(user_id)
            await message.reply_text(
                f"✅ `{setting_key.replace('_', ' ').title()}` update ho gaya.\n\n/settings bhejo dekhne ke liye."
            )
            return

    if await handle_admin_commands(client, message, lowered):
        return

    if lowered.startswith('/cancel'):
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        await message.reply_text('❌ Current input mode cancel kar diya gaya.')
        return

    if lowered.startswith('/ping'):
        await message.reply_text('✅ Bot online hai aur sahi se reply kar raha hai.')
        return

    if lowered.startswith('/start'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return
        await message.reply_text(
            start_text(),
            reply_markup=start_buttons(has_user_session(user_id)),
            disable_web_page_preview=True,
        )
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
        await message.reply_text(
            settings_home_text(user_id),
            reply_markup=settings_home_buttons(has_user_session(user_id)),
            disable_web_page_preview=True,
        )
        return

    if lowered.startswith('/login'):
        blocked = await check_force_sub(client, message)
        if blocked:
            return

        if has_user_session(user_id):
            await message.reply_text(login_status_text(user_id), reply_markup=login_buttons(True))
            return

        set_user_state(user_id, 'login_phone')
        await message.reply_text(ask_phone_text())
        return

    if lowered.startswith('/login_status'):
        await message.reply_text(login_status_text(user_id), reply_markup=login_buttons(has_user_session(user_id)))
        return

    if lowered.startswith('/logout'):
        if has_user_session(user_id):
            delete_user_session(user_id)
            await cleanup_login_client(user_id)
            await message.reply_text(logout_success_text(), reply_markup=login_buttons(False))
        else:
            await message.reply_text(logout_missing_text(), reply_markup=login_buttons(False))
        return

    if lowered.startswith('/my_tasks'):
        tasks = get_user_tasks(user_id, limit=10)
        await message.reply_text(
            my_tasks_text(tasks),
            reply_markup=my_tasks_buttons(),
            disable_web_page_preview=True,
        )
        return

    blocked = await check_force_sub(client, message)
    if blocked:
        return

    await message.reply_text(unknown_text())