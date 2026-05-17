from __future__ import annotations

from runtime_context import *
from services.delivery_service import *


async def clone_known_message_to_target_impl(
    client,
    from_chat_id,
    message_id,
    target,
    settings: dict | None = None,
    *,
    strict: bool = False,
):
    if not from_chat_id or not message_id:
        remember_delivery_error_codes(settings, [])
        return None

    topic_id = safe_topic_id((settings or {}).get("topic_id", ""))
    target = normalize_target(target)
    await ensure_target_peer_ready(client, target)

    attempts = []
    error_codes = []
    operations = (
        (
            "copy",
            lambda extra: client.copy_message(
                chat_id=target,
                from_chat_id=from_chat_id,
                message_id=message_id,
                **extra,
            ),
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
