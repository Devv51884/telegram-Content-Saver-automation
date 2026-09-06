from __future__ import annotations

import asyncio
import time

IGNORED_DIRECT_MESSAGES: dict[int, dict[int, float]] = {}
IGNORED_DIRECT_SIGNATURES: dict[int, dict[str, dict[str, float | int]]] = {}
RELAY_BRIDGE_WAITERS: dict[int, dict[str, list[asyncio.Future]]] = {}
RECENT_PRIVATE_UPDATES: dict[tuple[int, int], float] = {}
RECENT_CALLBACK_UPDATES: dict[str, float] = {}
UPDATE_DEDUPE_TTL_SECONDS = 30.0


def _cleanup_recent_updates(cache: dict, now: float | None = None):
    now = float(now or time.time())
    expired = [key for key, expiry in cache.items() if float(expiry or 0) <= now]
    for key in expired:
        cache.pop(key, None)


def is_duplicate_private_update(message, ttl_seconds: float = UPDATE_DEDUPE_TTL_SECONDS) -> bool:
    message_id = int(getattr(message, "id", 0) or 0)
    chat_id = int(getattr(getattr(message, "chat", None), "id", 0) or 0)
    if not message_id or not chat_id:
        return False
    now = time.time()
    _cleanup_recent_updates(RECENT_PRIVATE_UPDATES, now)
    key = (chat_id, message_id)
    if key in RECENT_PRIVATE_UPDATES:
        return True
    RECENT_PRIVATE_UPDATES[key] = now + float(ttl_seconds or UPDATE_DEDUPE_TTL_SECONDS)
    return False


def is_duplicate_callback_update(callback_query, ttl_seconds: float = UPDATE_DEDUPE_TTL_SECONDS) -> bool:
    callback_id = str(getattr(callback_query, "id", "") or "").strip()
    if not callback_id:
        return False

    now = time.time()
    _cleanup_recent_updates(RECENT_CALLBACK_UPDATES, now)
    if callback_id in RECENT_CALLBACK_UPDATES:
        return True
    RECENT_CALLBACK_UPDATES[callback_id] = now + float(ttl_seconds or UPDATE_DEDUPE_TTL_SECONDS)
    return False


def mark_ignored_direct_message(user_id: int, message_id: int, ttl_seconds: float = 180.0):
    user_id = int(user_id or 0)
    message_id = int(message_id or 0)
    if not user_id or not message_id:
        return
    expiry = time.time() + float(ttl_seconds or 180.0)
    ignored = IGNORED_DIRECT_MESSAGES.setdefault(user_id, {})
    ignored[message_id] = expiry


def should_ignore_direct_message(user_id: int, message_id: int) -> bool:
    user_id = int(user_id or 0)
    message_id = int(message_id or 0)
    if not user_id or not message_id:
        return False

    ignored = IGNORED_DIRECT_MESSAGES.get(user_id) or {}
    if not ignored:
        return False

    now = time.time()
    expired = [mid for mid, expiry in ignored.items() if expiry <= now]
    for mid in expired:
        ignored.pop(mid, None)

    should_ignore = bool(ignored.pop(message_id, None))
    if not ignored:
        IGNORED_DIRECT_MESSAGES.pop(user_id, None)
    return should_ignore


def get_message_media_kind(source_msg) -> str:
    if not source_msg:
        return ""
    for media in ("photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"):
        if getattr(source_msg, media, None):
            return media
    if str(getattr(source_msg, "text", "") or "").strip():
        return "text"
    if str(getattr(source_msg, "caption", "") or "").strip():
        return "caption"
    return str(getattr(source_msg, "media", "") or "").strip().lower()


def get_message_unique_id(source_msg) -> str:
    if not source_msg:
        return ""
    for media in ("photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"):
        obj = getattr(source_msg, media, None)
        if not obj:
            continue
        unique_id = getattr(obj, "file_unique_id", None)
        if unique_id:
            return str(unique_id)
        file_id = getattr(obj, "file_id", None)
        if file_id:
            return str(file_id)
    return ""


def get_message_file_name(source_msg) -> str:
    document = getattr(source_msg, "document", None)
    if document and getattr(document, "file_name", None):
        return document.file_name

    video = getattr(source_msg, "video", None)
    if video and getattr(video, "file_name", None):
        return video.file_name

    audio = getattr(source_msg, "audio", None)
    if audio and getattr(audio, "file_name", None):
        return audio.file_name

    animation = getattr(source_msg, "animation", None)
    if animation and getattr(animation, "file_name", None):
        return animation.file_name

    if getattr(source_msg, "video_note", None):
        return "video_note.mp4"

    sticker = getattr(source_msg, "sticker", None)
    if sticker and getattr(sticker, "file_name", None):
        return sticker.file_name
    if sticker:
        if bool(getattr(sticker, "is_animated", False)):
            return "sticker.tgs"
        if bool(getattr(sticker, "is_video", False)):
            return "sticker.webm"
        return "sticker.webp"

    if getattr(source_msg, "photo", None):
        return "photo.jpg"
    if getattr(source_msg, "voice", None):
        return "voice.ogg"
    return "file"


def get_message_file_size(source_msg) -> int:
    for media in ("document", "video", "audio", "photo", "voice", "animation", "sticker", "video_note"):
        obj = getattr(source_msg, media, None)
        if obj and getattr(obj, "file_size", None):
            return int(getattr(obj, "file_size", 0) or 0)
    return 0


def get_message_duration(source_msg) -> str:
    for media in ("video", "audio", "voice", "animation", "video_note"):
        obj = getattr(source_msg, media, None)
        if obj and getattr(obj, "duration", None):
            return str(getattr(obj, "duration", "") or "")
    return ""


def get_message_file_id(source_msg) -> str:
    if not source_msg:
        return ""
    for media in ("photo", "video", "document", "audio", "voice", "animation", "sticker", "video_note"):
        obj = getattr(source_msg, media, None)
        file_id = getattr(obj, "file_id", None) if obj else None
        if file_id:
            return str(file_id)
    return ""


def build_message_relay_signature(source_msg) -> str:
    if not source_msg:
        return ""
    media_kind = get_message_media_kind(source_msg)
    unique_id = get_message_unique_id(source_msg)
    file_size = str(get_message_file_size(source_msg) or "")
    duration = str(get_message_duration(source_msg) or "")
    text_value = str(getattr(source_msg, "caption", None) or getattr(source_msg, "text", None) or "").strip()
    text_value = text_value[:120]
    return "|".join([media_kind, unique_id, file_size, duration, text_value])


def mark_ignored_direct_signature(user_id: int, source_msg, ttl_seconds: float = 180.0):
    user_id = int(user_id or 0)
    signature = build_message_relay_signature(source_msg)
    if not user_id or not signature:
        return

    expiry = time.time() + float(ttl_seconds or 180.0)
    user_signatures = IGNORED_DIRECT_SIGNATURES.setdefault(user_id, {})
    item = user_signatures.get(signature) or {"count": 0, "expiry": expiry}
    item["count"] = int(item.get("count", 0) or 0) + 1
    item["expiry"] = max(float(item.get("expiry", expiry) or expiry), expiry)
    user_signatures[signature] = item


def should_ignore_direct_message_payload(user_id: int, message) -> bool:
    if should_ignore_direct_message(user_id, getattr(message, "id", 0)):
        return True

    user_id = int(user_id or 0)
    if not user_id:
        return False

    user_signatures = IGNORED_DIRECT_SIGNATURES.get(user_id) or {}
    if not user_signatures:
        return False

    now = time.time()
    expired = [signature for signature, item in user_signatures.items() if float(item.get("expiry", 0) or 0) <= now]
    for signature in expired:
        user_signatures.pop(signature, None)

    signature = build_message_relay_signature(message)
    item = user_signatures.get(signature)
    if not item:
        if not user_signatures:
            IGNORED_DIRECT_SIGNATURES.pop(user_id, None)
        return False

    count = int(item.get("count", 0) or 0)
    if count <= 1:
        user_signatures.pop(signature, None)
    else:
        item["count"] = count - 1
        user_signatures[signature] = item

    if not user_signatures:
        IGNORED_DIRECT_SIGNATURES.pop(user_id, None)
    return True


def _cleanup_relay_waiters(user_id: int, signature: str):
    user_id = int(user_id or 0)
    signature = str(signature or "").strip()
    if not user_id or not signature:
        return
    user_waiters = RELAY_BRIDGE_WAITERS.get(user_id) or {}
    waiters = [future for future in (user_waiters.get(signature) or []) if future and not future.done()]
    if waiters:
        user_waiters[signature] = waiters
        RELAY_BRIDGE_WAITERS[user_id] = user_waiters
        return
    user_waiters.pop(signature, None)
    if user_waiters:
        RELAY_BRIDGE_WAITERS[user_id] = user_waiters
    else:
        RELAY_BRIDGE_WAITERS.pop(user_id, None)


def create_relay_bridge_waiter(user_id: int, source_msg):
    user_id = int(user_id or 0)
    signature = build_message_relay_signature(source_msg)
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    user_waiters = RELAY_BRIDGE_WAITERS.setdefault(user_id, {})
    waiters = user_waiters.setdefault(signature, [])
    waiters.append(future)
    return signature, future


def capture_relay_bridge_message(user_id: int, message) -> bool:
    user_id = int(user_id or 0)
    if not user_id:
        return False
    signature = build_message_relay_signature(message)
    if not signature:
        return False
    user_waiters = RELAY_BRIDGE_WAITERS.get(user_id) or {}
    waiters = user_waiters.get(signature) or []
    while waiters:
        future = waiters.pop(0)
        if not future or future.done():
            continue
        future.set_result(message)
        user_waiters[signature] = waiters
        _cleanup_relay_waiters(user_id, signature)
        return True
    _cleanup_relay_waiters(user_id, signature)
    return False


async def wait_for_relay_bridge_message(user_id: int, source_msg, timeout: float = 8.0):
    signature, future = create_relay_bridge_waiter(user_id, source_msg)
    try:
        return await asyncio.wait_for(future, timeout=timeout)
    finally:
        _cleanup_relay_waiters(user_id, signature)
