from __future__ import annotations

from runtime_context import *
from features.media_transforms import build_final_caption, get_parse_mode
from features.storage_mode_helpers import analyze_telegram_media_delivery


async def ensure_target_peer_ready(client, target):
    if not client:
        return
    target = normalize_target(target)
    cache_key = (id(client), str(target))
    now = time.time()
    expired_peer_keys = [key for key, expiry in TARGET_PEER_READY_CACHE.items() if expiry <= now]
    for key in expired_peer_keys:
        TARGET_PEER_READY_CACHE.pop(key, None)
    if TARGET_PEER_READY_CACHE.get(cache_key, 0) > now:
        return
    try:
        await client.get_chat(target)
        TARGET_PEER_READY_CACHE[cache_key] = now + TARGET_PEER_READY_TTL
    except Exception:
        pass



async def clone_known_message_to_target_impl(
    client,
    from_chat_id,
    message_id,
    target,
    settings: dict | None = None,
    *,
    strict: bool = False,
    source_msg=None,
    index_no: int = 0,
):
    if not from_chat_id or not message_id:
        remember_delivery_error_codes(settings, [])
        return None

    topic_id = safe_topic_id((settings or {}).get("topic_id", ""))
    target = normalize_target(target)
    await ensure_target_peer_ready(client, target)

    attempts = []
    error_codes = []

    copy_kwargs_extra = {}
    if source_msg and settings:
        try:
            analysis = analyze_telegram_media_delivery(source_msg, settings)
            if analysis.get("caption_transform"):
                custom_caption = build_final_caption(source_msg, settings, index_no=index_no, storage_mode="telegram")
                caption_parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html"))
                copy_kwargs_extra["caption"] = custom_caption
                copy_kwargs_extra["parse_mode"] = caption_parse_mode
        except Exception as exc:
            debug_log(f"direct copy caption formatting error: {exc}")

    def _copy_call(extra):
        kwargs = {
            "chat_id": target,
            "from_chat_id": from_chat_id,
            "message_id": message_id,
            **copy_kwargs_extra,
            **extra,
        }
        return client.copy_message(**kwargs)

    operations = (
        (
            "copy",
            _copy_call,
        ),
        (
            "forward",
            lambda extra: client.forward_messages(
                chat_id=target,
                from_chat_id=from_chat_id,
                message_ids=message_id,
                drop_author=False,
                **extra,
            ),
        ),
    )

    for action_name, operation in operations:
        for message_thread_id in iter_optional_topic_ids(topic_id):
            extra = {}
            suffix = ""
            if message_thread_id:
                extra["message_thread_id"] = message_thread_id
            else:
                suffix = "(no-topic)"
            try:
                await asyncio.sleep(0)
                result = normalize_message_result(await operation(extra))
                if result:
                    remember_delivery_error_codes(settings, [])
                    return result
            except Exception as exc:
                attempts.append(f"{action_name}{suffix}: {exc}")
                error_codes.append(classify_delivery_error(exc))

    remember_delivery_error_codes(settings, error_codes)
    if strict:
        detail = " | ".join(attempts) if attempts else "no direct result"
        raise RuntimeError(f"Direct copy failed for destination {target} | {detail}")
    return None


clone_known_message_to_target = clone_known_message_to_target_impl

