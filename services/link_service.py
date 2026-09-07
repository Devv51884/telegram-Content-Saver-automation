from __future__ import annotations

from runtime_context import *
from services.storage_service import (
    AUTHORIZED_USER_CLIENTS,
    is_client_connection_ready,
    is_cached_authorized_user_client,
    cleanup_authorized_user_client,
)
from services.clone_delivery_service import (
    clone_known_message_to_target,
)
from services.task_service import *

def extract_telegram_link_info(text: str):
    if not text:
        return None

    text = str(text).strip()
    if text.startswith("t.me/"):
        text = "https://" + text
    elif text.startswith("http://"):
        text = "https://" + text[7:]
    text = re.sub(r"^https://(?:telegram\.(?:me|dog))/+", "https://t.me/", text)
    text = text.split("?", 1)[0].split("#", 1)[0].rstrip("/")

    bot_match = re.search(r"https?://(?:t|telegram)\.(?:me|dog)/b/([A-Za-z0-9_]+)/(\d+)$", text)
    private_topic_match = re.search(r"https?://(?:t|telegram)\.(?:me|dog)/c/(\d+)/(\d+)/(\d+)$", text)
    private_match = re.search(r"https?://(?:t|telegram)\.(?:me|dog)/c/(\d+)/(\d+)$", text)
    public_topic_match = re.search(r"https?://(?:t|telegram)\.(?:me|dog)/([A-Za-z0-9_]+)/(\d+)/(\d+)$", text)
    public_match = re.search(r"https?://(?:t|telegram)\.(?:me|dog)/([A-Za-z0-9_]+)/(\d+)$", text)

    if bot_match:
        bot_username = bot_match.group(1)
        msg_id = int(bot_match.group(2))
        return {"chat_id": bot_username, "message_id": msg_id, "link_type": "bot"}

    if private_topic_match:
        raw_chat_id = private_topic_match.group(1)
        topic_id = int(private_topic_match.group(2))
        msg_id = int(private_topic_match.group(3))
        chat_id = int(f"-100{raw_chat_id}")
        return {"chat_id": chat_id, "message_id": msg_id, "topic_id": topic_id, "link_type": "private_topic"}

    if private_match:
        raw_chat_id = private_match.group(1)
        msg_id = int(private_match.group(2))
        chat_id = int(f"-100{raw_chat_id}")
        return {"chat_id": chat_id, "message_id": msg_id, "link_type": "private"}

    if public_topic_match:
        username = public_topic_match.group(1)
        topic_id = int(public_topic_match.group(2))
        msg_id = int(public_topic_match.group(3))
        if username.lower() not in {"c", "b"}:
            return {"chat_id": username, "message_id": msg_id, "topic_id": topic_id, "link_type": "public_topic"}

    if public_match:
        username = public_match.group(1)
        msg_id = int(public_match.group(2))
        if username.lower() not in {"c", "b"}:
            return {"chat_id": username, "message_id": msg_id, "link_type": "public"}

    return None


def extract_batch_links_from_input(raw_text: str) -> list[str]:
    normalized_text = str(raw_text or "").strip()
    if not normalized_text:
        return []

    links = parse_batch_links(normalized_text)
    if not links:
        return []

    token_count = len([part for part in normalized_text.split() if part.strip()])
    if len(links) > 1 or token_count > 1 or "\n" in normalized_text:
        return links
    return []


def get_temp_download_path(source_msg):
    os.makedirs(TEMP_DIR, exist_ok=True)
    unique = uuid.uuid4().hex[:8]
    base_name = f"cd_{int(time.time())}_{source_msg.id}_{unique}"

    if source_msg.document and getattr(source_msg.document, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.document.file_name)}")
    if source_msg.video and getattr(source_msg.video, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.video.file_name)}")
    if source_msg.audio and getattr(source_msg.audio, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.audio.file_name)}")
    if source_msg.animation and getattr(source_msg.animation, "file_name", None):
        return os.path.join(TEMP_DIR, f"{unique}_{sanitize_filename(source_msg.animation.file_name)}")
    if source_msg.video_note:
        return os.path.join(TEMP_DIR, f"{base_name}.mp4")
    if source_msg.sticker:
        if bool(getattr(source_msg.sticker, "is_animated", False)):
            return os.path.join(TEMP_DIR, f"{base_name}.tgs")
        if bool(getattr(source_msg.sticker, "is_video", False)):
            return os.path.join(TEMP_DIR, f"{base_name}.webm")
        return os.path.join(TEMP_DIR, f"{base_name}.webp")
    if source_msg.photo:
        return os.path.join(TEMP_DIR, f"{base_name}.jpg")
    if source_msg.voice:
        return os.path.join(TEMP_DIR, f"{base_name}.ogg")
    return os.path.join(TEMP_DIR, f"{base_name}.bin")


def rename_downloaded_file(file_path: str, source_msg, settings: dict, index_no: int = 0):
    if not file_path or not os.path.exists(file_path):
        return file_path

    original_name = get_message_file_name(source_msg) or os.path.basename(file_path)
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
    user_id = int(user_id or 0)
    cached = AUTHORIZED_USER_CLIENTS.get(user_id)
    if cached:
        if is_client_connection_ready(cached):
            return cached
        AUTHORIZED_USER_CLIENTS.pop(user_id, None)
        try:
            await safe_close_client(cached)
        except Exception:
            pass

    session_string = get_user_session_string(user_id)
    if not session_string:
        return None

    client = Client(
        name=f"user_session_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session_string,
        in_memory=True,
        workers=1,
    )
    await client.start()
    AUTHORIZED_USER_CLIENTS[user_id] = client
    return client


async def get_or_create_delivery_user_client(user_id: int, existing_client=None):
    if existing_client:
        if is_client_connection_ready(existing_client):
            return existing_client, False
        if is_cached_authorized_user_client(user_id, existing_client):
            AUTHORIZED_USER_CLIENTS.pop(int(user_id or 0), None)
        try:
            await safe_close_client(existing_client)
        except Exception:
            pass
    if not has_user_session(user_id):
        return None, False
    try:
        client = await get_authorized_client_for_user(user_id)
    except Exception as exc:
        debug_log(f"Delivery user client unavailable for {user_id}: {exc}")
        return None, False
    return client, bool(client)


async def safe_close_client(client_obj):
    if not client_obj:
        return
    try:
        await client_obj.stop()
        return
    except Exception:
        pass
    try:
        await client_obj.disconnect()
    except Exception:
        pass


def safe_delete_local_file(file_path: str):
    file_path = str(file_path or "").strip()
    if not file_path:
        return
    try:
        if os.path.isfile(file_path):
            os.remove(file_path)
    except Exception:
        pass


async def fetch_message_via_best_client(bot_client, user_id: int, link_text: str):
    info = extract_telegram_link_info(link_text)
    if not info:
        return None, None, None, "bot"

    link_type = normalize_link_type(info)
    if link_type in {"private", "private_topic"}:
        if not has_user_session(user_id):
            return None, info, None, "bot"
        user_client = await get_authorized_client_for_user(user_id)
        if not user_client:
            return None, info, None, "bot"
        try:
            await asyncio.sleep(0)
            msg = await user_client.get_messages(info["chat_id"], info["message_id"])
            if msg and not getattr(msg, "empty", False):
                return msg, info, user_client, "user"
        except Exception as exc:
            err_str = str(exc).upper()
            if any(k in err_str for k in ("PEER_ID_INVALID", "CHANNEL_INVALID")):
                try:
                    await user_client.get_chat(info["chat_id"])
                    msg = await user_client.get_messages(info["chat_id"], info["message_id"])
                    if msg and not getattr(msg, "empty", False):
                        return msg, info, user_client, "user"
                except Exception:
                    pass
            if any(k in err_str for k in ("AUTH_KEY_UNREGISTERED", "USER_DEACTIVATED", "SESSION_REVOKED", "SESSION_EXPIRED")):
                await cleanup_authorized_user_client(user_id)
            raise
        return None, info, user_client, "user"

    try:
        await asyncio.sleep(0)
        msg = await bot_client.get_messages(info["chat_id"], info["message_id"])
        if msg and not getattr(msg, "empty", False):
            return msg, info, None, "bot"
    except Exception:
        pass

    if has_user_session(user_id):
        user_client = await get_authorized_client_for_user(user_id)
        if user_client:
            try:
                await asyncio.sleep(0)
                msg = await user_client.get_messages(info["chat_id"], info["message_id"])
                if msg and not getattr(msg, "empty", False):
                    return msg, info, user_client, "user"
            except Exception as exc:
                err_str = str(exc).upper()
                if any(k in err_str for k in ("PEER_ID_INVALID", "CHANNEL_INVALID")):
                    try:
                        await user_client.get_chat(info["chat_id"])
                        msg = await user_client.get_messages(info["chat_id"], info["message_id"])
                        if msg and not getattr(msg, "empty", False):
                            return msg, info, user_client, "user"
                    except Exception:
                        pass
                if any(k in err_str for k in ("AUTH_KEY_UNREGISTERED", "USER_DEACTIVATED", "SESSION_REVOKED", "SESSION_EXPIRED")):
                    await cleanup_authorized_user_client(user_id)
                raise

    return None, info, None, "bot"


def can_direct_copy(source_msg, settings: dict, fetch_mode: str = "bot") -> bool:
    if not is_media_message(source_msg):
        return False
    if source_has_protected_content(source_msg):
        return False
    profile = analyze_telegram_media_delivery(source_msg, settings)
    if profile.get("direct_copy_blocked"):
        return False
    if fetch_mode == "bot":
        return bool(ENABLE_DIRECT_PUBLIC_COPY and cfg.PREFER_COPY_OVER_DOWNLOAD)
    # Private/user-session sources ko bot client se direct copy nahi karna chahiye.
    # Unke liye alag user-client fast path use hota hai.
    return False


async def try_direct_copy(client, source_msg, target, settings: dict, index_no: int = 0):
    return await clone_known_message_to_target(
        client,
        getattr(getattr(source_msg, "chat", None), "id", None),
        getattr(source_msg, "id", None),
        target,
        settings,
        strict=True,
        source_msg=source_msg,
        index_no=index_no,
    )


async def get_thumbnail_temp_path(client, settings: dict, task_id: str = ""):
    thumb_file_id = (settings.get("thumbnail_file_id") or "").strip()
    if not settings.get("thumbnail_enabled") or not thumb_file_id:
        return None

    os.makedirs(TEMP_DIR, exist_ok=True)
    thumb_path = os.path.join(TEMP_DIR, f"thumb_{task_id or uuid.uuid4().hex[:8]}.jpg")

    try:
        await asyncio.sleep(0)
        result = await client.download_media(thumb_file_id, file_name=thumb_path)
        if result and os.path.exists(result):
            return result
    except Exception:
        pass
    return None


