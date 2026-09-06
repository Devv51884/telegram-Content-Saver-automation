from __future__ import annotations

from runtime_context import *
from services.storage_service import *
from services.task_service import *
from services.clone_delivery_service import (
    clone_known_message_to_target,
    clone_known_message_to_target_impl,
)
from services.link_service import (
    get_temp_download_path,
    rename_downloaded_file,
    safe_delete_local_file,
    try_direct_copy,
)

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


async def send_cached_media_to_target(client, target, source_msg, settings: dict, index_no: int = 0):
    target = normalize_target(target)
    await ensure_target_peer_ready(client, target)
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    caption = build_final_caption(source_msg, settings, index_no=index_no, storage_mode="telegram")
    caption = caption if str(caption or "").strip() else None
    caption_parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html")) if caption else None
    file_id = get_message_file_id(source_msg)
    if not file_id:
        return None

    if source_msg.photo:
        return await execute_topic_aware_send(
            lambda **extra: client.send_photo(
                chat_id=target,
                photo=file_id,
                caption=caption,
                parse_mode=caption_parse_mode,
                **extra,
            ),
            topic_id,
        )
    if source_msg.video:
        return await execute_topic_aware_send(
            lambda **extra: client.send_video(
                chat_id=target,
                video=file_id,
                caption=caption,
                parse_mode=caption_parse_mode,
                duration=getattr(source_msg.video, "duration", None),
                width=getattr(source_msg.video, "width", None),
                height=getattr(source_msg.video, "height", None),
                supports_streaming=bool(getattr(source_msg.video, "supports_streaming", False)),
                **extra,
            ),
            topic_id,
        )
    if source_msg.document:
        return await execute_topic_aware_send(
            lambda **extra: client.send_document(
                chat_id=target,
                document=file_id,
                caption=caption,
                parse_mode=caption_parse_mode,
                **extra,
            ),
            topic_id,
        )
    if source_msg.audio:
        return await execute_topic_aware_send(
            lambda **extra: client.send_audio(
                chat_id=target,
                audio=file_id,
                caption=caption,
                parse_mode=caption_parse_mode,
                duration=getattr(source_msg.audio, "duration", None),
                performer=getattr(source_msg.audio, "performer", None),
                title=getattr(source_msg.audio, "title", None),
                **extra,
            ),
            topic_id,
        )
    if source_msg.voice:
        return await execute_topic_aware_send(
            lambda **extra: client.send_voice(
                chat_id=target,
                voice=file_id,
                caption=caption,
                parse_mode=caption_parse_mode,
                duration=getattr(source_msg.voice, "duration", None),
                **extra,
            ),
            topic_id,
        )
    if source_msg.animation:
        return await execute_topic_aware_send(
            lambda **extra: client.send_animation(
                chat_id=target,
                animation=file_id,
                caption=caption,
                parse_mode=caption_parse_mode,
                duration=getattr(source_msg.animation, "duration", None),
                width=getattr(source_msg.animation, "width", None),
                height=getattr(source_msg.animation, "height", None),
                **extra,
            ),
            topic_id,
        )
    if source_msg.sticker:
        return await execute_topic_aware_send(
            lambda **extra: client.send_sticker(
                chat_id=target,
                sticker=file_id,
                **extra,
            ),
            topic_id,
        )
    if source_msg.video_note:
        return await execute_topic_aware_send(
            lambda **extra: client.send_video_note(
                chat_id=target,
                video_note=file_id,
                duration=getattr(source_msg.video_note, "duration", None),
                length=getattr(source_msg.video_note, "length", None),
                **extra,
            ),
            topic_id,
        )
    return None


async def try_direct_forward_with_user_client(user_client, source_msg, target, settings: dict, index_no: int = 0):
    result = await clone_known_message_to_target(
        user_client,
        getattr(getattr(source_msg, "chat", None), "id", None),
        getattr(source_msg, "id", None),
        target,
        settings,
        strict=False,
        source_msg=source_msg,
        index_no=index_no,
    )
    if result:
        return result
    debug_log(f"User direct save failed for {target}")
    return None


async def probe_target_client_access(client_obj, client_kind: str, target):
    info = {
        "client": client_obj,
        "client_kind": client_kind,
        "target": normalize_target(target),
        "resolved": False,
        "writable": False,
        "chat_id": 0,
        "chat_type": "",
        "member_status": "",
        "title": "",
        "error": "",
    }
    if not client_obj:
        return info

    cache_key = (id(client_obj), str(client_kind or ""), str(info["target"]))
    now = time.time()
    expired_cache_keys = [key for key, entry in TARGET_ACCESS_CACHE.items() if float((entry or {}).get("expires_at", 0) or 0) <= now]
    for key in expired_cache_keys:
        TARGET_ACCESS_CACHE.pop(key, None)
    cached_entry = TARGET_ACCESS_CACHE.get(cache_key)
    if cached_entry:
        cached_info = dict(cached_entry.get("info") or {})
        cached_info["client"] = client_obj
        return cached_info

    try:
        chat = await client_obj.get_chat(info["target"])
        info["resolved"] = True
        info["chat_id"] = getattr(chat, "id", 0) or 0
        info["chat_type"] = normalize_chat_type(getattr(chat, "type", ""))
        info["title"] = getattr(chat, "title", None) or getattr(chat, "first_name", None) or ""
        TARGET_PEER_READY_CACHE[(id(client_obj), str(info["target"]))] = now + TARGET_PEER_READY_TTL
    except Exception as exc:
        info["error"] = str(exc)
        TARGET_ACCESS_CACHE[cache_key] = {"expires_at": now + TARGET_ACCESS_CACHE_TTL, "info": dict(info)}
        return info

    try:
        me = getattr(client_obj, "me", None) or await client_obj.get_me()
    except Exception as exc:
        info["error"] = str(exc)
        TARGET_ACCESS_CACHE[cache_key] = {"expires_at": now + TARGET_ACCESS_CACHE_TTL, "info": dict(info)}
        return info

    member_status = ""
    if info["chat_type"] in {"private", "bot"}:
        member_status = "member"
    else:
        try:
            member = await client_obj.get_chat_member(info["chat_id"], me.id)
            member_status = normalize_member_status(getattr(member, "status", ""))
        except Exception as exc:
            info["error"] = str(exc)
            member_status = ""

    info["member_status"] = member_status
    info["writable"] = is_positive_writable_target(info["chat_type"], member_status)
    TARGET_ACCESS_CACHE[cache_key] = {"expires_at": now + TARGET_ACCESS_CACHE_TTL, "info": dict(info)}
    return info


async def probe_target_access_map(client_map: dict, target):
    client_kinds = ("main_bot", "user_session", "personal_bot")
    results = await asyncio.gather(*[
        probe_target_client_access(client_map.get(client_kind), client_kind, target)
        for client_kind in client_kinds
    ])
    return {client_kind: result for client_kind, result in zip(client_kinds, results)}


async def copy_result_to_target(client, delivered_message, target, settings: dict):
    if not delivered_message:
        return None
    return await copy_known_message_to_target(
        client,
        getattr(getattr(delivered_message, "chat", None), "id", None),
        getattr(delivered_message, "id", None),
        target,
        settings,
    )


async def copy_known_message_to_target(client, from_chat_id, message_id, target, settings: dict, source_msg=None, index_no: int = 0):
    return await clone_known_message_to_target(
        client,
        from_chat_id,
        message_id,
        target,
        settings,
        strict=False,
        source_msg=source_msg,
        index_no=index_no,
    )


async def ensure_downloaded_source_file(ui_client, task_id: str, source_msg, settings: dict, index_no: int, download_state: dict, source_access: dict, client_map: dict):
    download_state = download_state or {}
    current_path = str(download_state.get("path") or "").strip()
    if current_path and os.path.exists(current_path):
        return current_path

    download_client_kind = select_download_client_kind(source_access, client_map)
    if not download_client_kind:
        raise RuntimeError("Source message readable client nahi mila, isliye download start nahi ho paya.")

    fallback_reason = str(download_state.get("fallback_reason") or "").strip()
    reason_text = f"Fallback: {fallback_reason}" if fallback_reason else "Preparing fallback download"
    touch_task(task_id, {
        "status": "downloading",
        "current_stage": "downloading",
        "progress_text": reason_text,
        "is_visible": True,
        "fallback_reason": fallback_reason,
        "delivery_path": "download_upload",
        "delivery_client_kind": download_client_kind,
    })
    await update_task_status_message(ui_client, task_id)

    source_client = client_map.get(download_client_kind)
    download_hint = get_temp_download_path(source_msg)
    download_path = download_hint
    try:
        download_result = await asyncio.wait_for(
            source_client.download_media(
                source_msg,
                file_name=download_hint,
                progress=progress_callback,
                progress_args=(ui_client, task_id, "downloading"),
            ),
            timeout=300,
        )
        download_path = resolve_downloaded_path(download_hint, download_result)
        ensure_valid_downloaded_file(download_path)
        download_path = rename_downloaded_file(download_path, source_msg, settings, index_no=index_no)
        ensure_valid_downloaded_file(download_path)
    except Exception:
        safe_delete_local_file(download_path)
        if download_path != download_hint:
            safe_delete_local_file(download_hint)
        raise

    download_state["path"] = download_path
    download_state["download_client_kind"] = download_client_kind
    return download_path


async def relay_message_via_log_channel(client_map: dict, source_msg, relay_target, target, settings: dict, index_no: int = 0):
    relay_target = normalize_target(relay_target)
    target = normalize_target(target)
    relay_source_kind = str((settings or {}).get("_relay_source_client_kind") or "").strip().lower()
    relay_client_kind = str((settings or {}).get("_relay_client_kind") or "").strip().lower()

    relay_source_client = client_map.get(relay_source_kind)
    relay_client = client_map.get(relay_client_kind)
    if not relay_source_client or not relay_client:
        raise RuntimeError("Relay clients unavailable")

    relay_settings = dict(settings or {})
    relay_settings["topic_id"] = ""
    relay_settings.pop("_relay_source_client_kind", None)
    relay_settings.pop("_relay_client_kind", None)

    if relay_source_kind == "user_session":
        bridge_message = await try_direct_forward_with_user_client(relay_source_client, source_msg, relay_target, relay_settings, index_no=index_no)
    elif relay_source_kind == "main_bot":
        bridge_message = await try_direct_copy(relay_source_client, source_msg, relay_target, relay_settings, index_no=index_no)
    else:
        raise RuntimeError("Relay source client unsupported")

    if not bridge_message:
        raise RuntimeError("Relay bridge send failed")

    delivery_message = await copy_result_to_target(relay_client, bridge_message, target, settings)
    if not delivery_message:
        raise RuntimeError("Relay destination copy failed")

    return bridge_message, delivery_message


async def get_main_bot_bridge_target(bot_client):
    me = getattr(bot_client, "me", None) or await bot_client.get_me()
    username = str(getattr(me, "username", "") or "").strip()
    if username:
        return f"@{username}"
    return int(getattr(me, "id", 0) or 0)


def can_use_bot_pm_relay(source_access: dict | None, target_access: dict | None, client_map: dict | None = None) -> bool:
    source_access = source_access or {}
    target_access = target_access or {}
    client_map = client_map or {}
    if not source_access.get("user_session"):
        return False
    if not (client_map.get("user_session") and client_map.get("main_bot")):
        return False
    main_bot_access = target_access.get("main_bot") or {}
    if main_bot_access.get("writable"):
        return True
    if main_bot_access.get("resolved"):
        return True
    return False


async def relay_message_via_bot_pm(client_map: dict, source_msg, user_id: int, target, settings: dict, index_no: int = 0):
    relay_source_client = client_map.get("user_session")
    relay_client = client_map.get("main_bot")
    if not relay_source_client or not relay_client:
        raise RuntimeError("Bot PM relay clients unavailable")

    bridge_target = await get_main_bot_bridge_target(relay_client)
    relay_settings = dict(settings or {})
    relay_settings["topic_id"] = ""
    mark_ignored_direct_signature(user_id, source_msg)
    bridge_future = asyncio.create_task(wait_for_relay_bridge_message(user_id, source_msg))

    bridge_message = await try_direct_forward_with_user_client(
        relay_source_client,
        source_msg,
        bridge_target,
        relay_settings,
        index_no=index_no,
    )
    if not bridge_message:
        bridge_future.cancel()
        raise RuntimeError("Bot PM relay bridge send failed")

    bot_bridge_message = None
    try:
        await asyncio.sleep(0)
        if bridge_future.done():
            bot_bridge_message = await bridge_future
    except Exception:
        bot_bridge_message = None
    if bot_bridge_message:
        mark_ignored_direct_message(user_id, getattr(bot_bridge_message, "id", None))

    try:
        delivery_message = None
        for attempt in range(4):
            copy_candidates = []
            bridge_chat_id = getattr(getattr(bot_bridge_message, "chat", None), "id", None)
            bridge_message_id = getattr(bot_bridge_message, "id", None)
            if bridge_chat_id and bridge_message_id:
                copy_candidates.append((bridge_chat_id, bridge_message_id))
            copy_candidates.append((int(user_id), getattr(bridge_message, "id", None)))

            seen_pairs = set()
            for from_chat_id, message_id in copy_candidates:
                pair = (int(from_chat_id or 0), int(message_id or 0))
                if not pair[0] or not pair[1] or pair in seen_pairs:
                    continue
                seen_pairs.add(pair)
                delivery_message = await copy_known_message_to_target(
                    relay_client,
                    from_chat_id,
                    message_id,
                    target,
                    settings,
                )
                if delivery_message:
                    break
            if delivery_message:
                break
            if attempt >= 3:
                break

            wait_timeout = 0.35 * (attempt + 1)
            if not bot_bridge_message:
                try:
                    bot_bridge_message = await asyncio.wait_for(asyncio.shield(bridge_future), timeout=wait_timeout)
                except Exception:
                    bot_bridge_message = None
                if bot_bridge_message:
                    mark_ignored_direct_message(user_id, getattr(bot_bridge_message, "id", None))
                    continue
            await asyncio.sleep(wait_timeout)

        if not delivery_message and not bot_bridge_message:
            try:
                bot_bridge_message = await asyncio.wait_for(asyncio.shield(bridge_future), timeout=1.0)
            except Exception:
                bot_bridge_message = None
            if bot_bridge_message:
                mark_ignored_direct_message(user_id, getattr(bot_bridge_message, "id", None))
                delivery_message = await copy_known_message_to_target(
                    relay_client,
                    getattr(getattr(bot_bridge_message, "chat", None), "id", None) or int(user_id),
                    getattr(bot_bridge_message, "id", None) or getattr(bridge_message, "id", None),
                    target,
                    settings,
                )
        if not delivery_message:
            raise RuntimeError("Bot PM relay destination copy failed")
        return bridge_message, delivery_message
    finally:
        if bridge_future and not bridge_future.done():
            bridge_future.cancel()
            with contextlib.suppress(asyncio.CancelledError, Exception):
                await bridge_future
        await safe_delete_message(bridge_message)
        if bot_bridge_message and getattr(bot_bridge_message, "id", None) != getattr(bridge_message, "id", None):
            await safe_delete_message(bot_bridge_message)


async def deliver_target_with_routing(ui_client, task_id: str, source_msg, settings: dict, target, *, client_map: dict, source_access: dict, index_no: int = 0, download_state: dict | None = None, allow_download_fallback: bool = True):
    target = normalize_target(target)
    ensure_task_not_cancelled(task_id)
    user_id = int((settings or {}).get("_delivery_user_id") or 0)
    source_is_media = is_media_message(source_msg)
    has_cached_file_id = bool(get_message_file_id(source_msg))
    telegram_delivery = analyze_telegram_media_delivery(source_msg, settings) if source_is_media else {
        "requires_local_upload": False,
        "direct_copy_blocked": False,
        "cached_send_allowed": False,
    }
    has_transforming = bool(telegram_delivery.get("requires_local_upload"))
    is_protected = source_has_protected_content(source_msg)
    relay_target_available = bool(LOG_CHANNEL and str(normalize_target(LOG_CHANNEL)) != str(target))
    if relay_target_available:
        access_map, relay_access_map = await asyncio.gather(
            probe_target_access_map(client_map, target),
            probe_target_access_map(client_map, LOG_CHANNEL),
        )
    else:
        access_map = await probe_target_access_map(client_map, target)
        relay_access_map = {}
    prefer_personal_upload = str((settings or {}).get("bot_delivery_mode", "main") or "main").strip().lower() == "personal"
    bot_pm_relay_available = bool(user_id) and can_use_bot_pm_relay(source_access, access_map, client_map)
    allow_main_bot_direct = bool(ENABLE_DIRECT_PUBLIC_COPY and cfg.PREFER_COPY_OVER_DOWNLOAD)
    allow_user_session_direct = bool(cfg.ALLOW_FORWARD_AS_FALLBACK and ENABLE_DIRECT_PRIVATE_COPY)

    plan = build_target_delivery_plan(
        is_media=source_is_media,
        has_cached_file_id=has_cached_file_id,
        has_transforming=has_transforming,
        is_protected=is_protected,
        source_access=source_access,
        target_access=access_map,
        allow_main_bot_direct=allow_main_bot_direct,
        allow_user_session_direct=allow_user_session_direct,
        prefer_personal_upload=prefer_personal_upload,
        direct_copy_blocked=bool(telegram_delivery.get("direct_copy_blocked")),
        cached_send_allowed=bool(telegram_delivery.get("cached_send_allowed")),
        relay_access=relay_access_map,
        relay_target_available=relay_target_available,
        bot_pm_relay_available=bot_pm_relay_available,
    )

    if plan.get("error"):
        raise RuntimeError(build_target_access_error(target, access_map))

    delivery_message = None
    bridge_message = None
    delivery_client_kind = plan.get("direct_client_kind") or plan.get("cached_client_kind") or plan.get("upload_client_kind")
    route_client_label = delivery_client_kind
    delivery_path = describe_delivery_path(plan.get("mode", ""), delivery_client_kind)

    if plan.get("mode") == "direct":
        touch_task(task_id, {
            "status": "copying",
            "current_stage": "copying",
            "progress_text": describe_target_route(target, delivery_path, route_client_label),
            "is_visible": True,
            "delivery_path": delivery_path,
            "delivery_client_kind": delivery_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)

        if plan.get("direct_client_kind") == "main_bot":
            try:
                delivery_message = await try_direct_copy(client_map["main_bot"], source_msg, target, settings, index_no=index_no)
            except Exception:
                delivery_message = None
        elif plan.get("direct_client_kind") == "user_session":
            delivery_message = await try_direct_forward_with_user_client(client_map["user_session"], source_msg, target, settings, index_no=index_no)

        ensure_task_not_cancelled(task_id)
        if delivery_message:
            return {
                "message": delivery_message,
                "target": target,
                "delivery_path": delivery_path,
                "delivery_client_kind": delivery_client_kind,
                "route_client_label": route_client_label,
                "fallback_reason": "",
                "target_access": access_map,
            }

        if download_state is None:
            download_state = {}
        direct_error_codes = consume_delivery_error_codes(settings)
        if "chat_forwards_restricted" in direct_error_codes:
            download_state["fallback_reason"] = "protected_content"
            plan = {
                "mode": "upload" if source_is_media else "text",
                "direct_client_kind": None,
                "cached_client_kind": None,
                "relay_source_client_kind": None,
                "relay_client_kind": None,
                "relay_via": "",
                "upload_client_kind": choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload),
                "fallback_reason": "protected_content",
                "error": "",
            }
        else:
            download_state["fallback_reason"] = "direct_attempt_failed"
            plan = build_followup_delivery_plan_after_direct_failure(
                failed_client_kind=plan.get("direct_client_kind") or "",
                is_media=source_is_media,
                has_cached_file_id=has_cached_file_id,
                has_transforming=has_transforming,
                is_protected=is_protected,
                source_access=source_access,
                target_access=access_map,
                allow_main_bot_direct=allow_main_bot_direct,
                allow_user_session_direct=allow_user_session_direct,
                prefer_personal_upload=prefer_personal_upload,
                direct_copy_blocked=bool(telegram_delivery.get("direct_copy_blocked")),
                cached_send_allowed=bool(telegram_delivery.get("cached_send_allowed")),
                relay_access=relay_access_map,
                relay_target_available=relay_target_available,
                bot_pm_relay_available=bot_pm_relay_available,
            )
        if plan.get("error"):
            raise RuntimeError(build_target_access_error(target, access_map))
        if plan.get("mode") == "direct":
            next_direct_kind = plan.get("direct_client_kind")
            next_delivery_path = describe_delivery_path("direct", next_direct_kind)
            next_route_label = next_direct_kind
            touch_task(task_id, {
                "status": "copying",
                "current_stage": "copying",
                "progress_text": describe_target_route(target, next_delivery_path, next_route_label),
                "is_visible": True,
                "delivery_path": next_delivery_path,
                "delivery_client_kind": next_direct_kind,
                "fallback_reason": "",
            })
            await update_task_status_message(ui_client, task_id)
            ensure_task_not_cancelled(task_id)
            if next_direct_kind == "main_bot":
                try:
                    delivery_message = await try_direct_copy(client_map["main_bot"], source_msg, target, settings, index_no=index_no)
                except Exception:
                    delivery_message = None
            elif next_direct_kind == "user_session":
                delivery_message = await try_direct_forward_with_user_client(client_map["user_session"], source_msg, target, settings, index_no=index_no)
            ensure_task_not_cancelled(task_id)
            if delivery_message:
                return {
                    "message": delivery_message,
                    "target": target,
                    "delivery_path": next_delivery_path,
                    "delivery_client_kind": next_direct_kind,
                    "route_client_label": next_route_label,
                    "fallback_reason": "",
                    "target_access": access_map,
                }
            plan = build_followup_delivery_plan_after_direct_failure(
                failed_client_kind=next_direct_kind or "",
                is_media=source_is_media,
                has_cached_file_id=has_cached_file_id,
                has_transforming=has_transforming,
                is_protected=is_protected,
                source_access=source_access,
                target_access=access_map,
                allow_main_bot_direct=False,
                allow_user_session_direct=False,
                prefer_personal_upload=prefer_personal_upload,
                direct_copy_blocked=bool(telegram_delivery.get("direct_copy_blocked")),
                cached_send_allowed=bool(telegram_delivery.get("cached_send_allowed")),
                relay_access=relay_access_map,
                relay_target_available=relay_target_available,
                bot_pm_relay_available=bot_pm_relay_available,
            )
            if plan.get("error"):
                raise RuntimeError(build_target_access_error(target, access_map))
        if plan.get("mode") in {"upload", "text"} and not plan.get("upload_client_kind"):
            plan["upload_client_kind"] = choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload)
            if not plan["upload_client_kind"]:
                raise RuntimeError(build_target_access_error(target, access_map))
        delivery_client_kind = plan.get("direct_client_kind") or plan.get("cached_client_kind") or plan.get("relay_client_kind") or plan.get("upload_client_kind")
        route_client_label = delivery_client_kind
        delivery_path = describe_delivery_path(plan.get("mode", ""), plan.get("direct_client_kind") or plan.get("relay_client_kind") or delivery_client_kind)

    if plan.get("mode") == "cached":
        cached_client_kind = plan.get("cached_client_kind")
        cached_client = client_map.get(cached_client_kind)
        if not cached_client:
            raise RuntimeError(build_target_access_error(target, access_map))

        touch_task(task_id, {
            "status": "copying",
            "current_stage": "copying",
            "progress_text": describe_target_route(target, "cached_send", cached_client_kind),
            "is_visible": True,
            "delivery_path": "cached_send",
            "delivery_client_kind": cached_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)

        try:
            delivery_message = normalize_message_result(await send_cached_media_to_target(cached_client, target, source_msg, settings, index_no=index_no))
        except Exception:
            delivery_message = None

        ensure_task_not_cancelled(task_id)
        if delivery_message:
            return {
                "message": delivery_message,
                "target": target,
                "delivery_path": "cached_send",
                "delivery_client_kind": cached_client_kind,
                "route_client_label": cached_client_kind,
                "fallback_reason": "",
                "target_access": access_map,
            }

        if download_state is None:
            download_state = {}
        download_state["fallback_reason"] = "cached_send_failed"
        can_preserve_with_relay = not bool(telegram_delivery.get("direct_copy_blocked"))
        relay_plan = None
        if can_preserve_with_relay:
            relay_plan = choose_relay_delivery_plan(
                source_access,
                access_map,
                relay_access_map,
                relay_target_available=relay_target_available,
                prefer_personal_upload=prefer_personal_upload,
                bot_pm_relay_available=bot_pm_relay_available,
            )
        if relay_plan:
            plan["mode"] = "relay"
            plan.update(relay_plan)
            plan["fallback_reason"] = "cached_send_failed"
        else:
            plan["mode"] = "upload"
            plan["upload_client_kind"] = choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload)
            plan["fallback_reason"] = "cached_send_failed"
            if not plan["upload_client_kind"]:
                raise RuntimeError(build_target_access_error(target, access_map))
            delivery_client_kind = plan["upload_client_kind"]
            route_client_label = delivery_client_kind
            delivery_path = "download_upload"

    if plan.get("mode") == "relay":
        relay_source_kind = plan.get("relay_source_client_kind")
        relay_client_kind = plan.get("relay_client_kind")
        relay_via = str(plan.get("relay_via") or "log_channel").strip().lower()
        relay_label = f"{relay_source_kind}->{relay_client_kind}"
        if relay_via == "bot_pm":
            relay_label = f"{relay_label}(pm)"
        relay_settings = dict(settings or {})
        relay_settings["_relay_source_client_kind"] = relay_source_kind
        relay_settings["_relay_client_kind"] = relay_client_kind
        touch_task(task_id, {
            "status": "copying",
            "current_stage": "copying",
            "progress_text": describe_target_route(target, "relay_copy", relay_label),
            "is_visible": True,
            "delivery_path": "relay_copy",
            "delivery_client_kind": relay_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        ensure_task_not_cancelled(task_id)

        try:
            if relay_via == "bot_pm":
                bridge_message, delivery_message = await relay_message_via_bot_pm(
                    client_map,
                    source_msg,
                    user_id,
                    target,
                    relay_settings,
                    index_no=index_no,
                )
            else:
                bridge_message, delivery_message = await relay_message_via_log_channel(
                    client_map,
                    source_msg,
                    LOG_CHANNEL,
                    target,
                    relay_settings,
                    index_no=index_no,
                )
        except Exception:
            bridge_message = None
            delivery_message = None

        ensure_task_not_cancelled(task_id)
        if delivery_message:
            relay_target_value = ""
            if relay_via == "log_channel":
                relay_target_value = str(normalize_target(LOG_CHANNEL))
            return {
                "message": delivery_message,
                "bridge_message": bridge_message,
                "relay_target": relay_target_value,
                "relay_source_client_kind": relay_source_kind,
                "target": target,
                "delivery_path": "relay_copy",
                "delivery_client_kind": relay_client_kind,
                "route_client_label": relay_label,
                "relay_via": relay_via,
                "fallback_reason": "",
                "target_access": access_map,
            }

        if download_state is None:
            download_state = {}
        download_state["fallback_reason"] = "relay_copy_failed"
        plan["mode"] = "upload" if source_is_media else "text"
        plan["upload_client_kind"] = choose_upload_client_kind(access_map, prefer_personal_upload=prefer_personal_upload)
        plan["fallback_reason"] = "relay_copy_failed"
        if not plan["upload_client_kind"]:
            raise RuntimeError(build_target_access_error(target, access_map))
        delivery_client_kind = plan["upload_client_kind"]
        route_client_label = delivery_client_kind
        delivery_path = "download_upload" if source_is_media else "text_send"

    if plan.get("mode") == "text":
        text_client_kind = plan.get("upload_client_kind")
        text_client = client_map.get(text_client_kind)
        if not text_client:
            raise RuntimeError(build_target_access_error(target, access_map))
        touch_task(task_id, {
            "status": "uploading",
            "current_stage": "uploading",
            "progress_text": describe_target_route(target, "text_send", text_client_kind),
            "is_visible": True,
            "delivery_path": "text_send",
            "delivery_client_kind": text_client_kind,
            "fallback_reason": "",
        })
        await update_task_status_message(ui_client, task_id)
        from services.upload_target_service import send_text_to_target
        delivery_message = await send_text_to_target(text_client, target, source_msg, settings, index_no=index_no)
        ensure_task_not_cancelled(task_id)
        return {
            "message": delivery_message,
            "target": target,
            "delivery_path": "text_send",
            "delivery_client_kind": text_client_kind,
            "route_client_label": text_client_kind,
            "fallback_reason": "",
            "target_access": access_map,
        }

    if download_state is None:
        download_state = {}
    if not download_state.get("fallback_reason"):
        download_state["fallback_reason"] = plan.get("fallback_reason", "")
    if not allow_download_fallback:
        fallback_reason = str(download_state.get("fallback_reason") or plan.get("fallback_reason") or "download_fallback_required")
        raise RuntimeError(f"Download fallback disabled for target {target} ({fallback_reason})")

    download_path = await ensure_downloaded_source_file(
        ui_client,
        task_id,
        source_msg,
        settings,
        index_no,
        download_state,
        source_access,
        client_map,
    )

    upload_client_kind = plan.get("upload_client_kind")
    upload_client = client_map.get(upload_client_kind)
    if not upload_client:
        raise RuntimeError(build_target_access_error(target, access_map))

    touch_task(task_id, {
        "status": "uploading",
        "current_stage": "uploading",
        "progress_text": describe_target_route(target, "download_upload", upload_client_kind),
        "is_visible": True,
        "delivery_path": "download_upload",
        "delivery_client_kind": upload_client_kind,
        "fallback_reason": str(download_state.get("fallback_reason") or ""),
    })
    await update_task_status_message(ui_client, task_id)
    from services.upload_target_service import upload_file_to_target
    delivery_message = await upload_file_to_target(upload_client, task_id, target, download_path, source_msg, settings, index_no=index_no)
    ensure_task_not_cancelled(task_id)
    return {
        "message": delivery_message,
        "target": target,
        "delivery_path": "download_upload",
        "delivery_client_kind": upload_client_kind,
        "route_client_label": upload_client_kind,
        "fallback_reason": str(download_state.get("fallback_reason") or ""),
        "target_access": access_map,
    }


async def deliver_primary_then_log_routed(ui_client, task_id: str, source_msg, settings: dict, destination, *, user_id: int = 0, client_map: dict, source_access: dict, index_no: int = 0):
    if not destination and not LOG_CHANNEL:
        raise RuntimeError("No destination configured. Destination aur log channel dono blank hain.")

    ensure_task_not_cancelled(task_id)
    routing_settings = dict(settings or {})
    routing_settings["_delivery_user_id"] = int(user_id or 0)
    delivered_to = []
    delivery_errors = []
    route_summaries = []
    download_state = {"path": None, "fallback_reason": ""}
    primary_result = None
    primary_route = None

    if destination:
        try:
            primary_route = await deliver_target_with_routing(
                ui_client,
                task_id,
                source_msg,
                routing_settings,
                destination,
                client_map=client_map,
                source_access=source_access,
                index_no=index_no,
                download_state=download_state,
            )
            primary_result = primary_route.get("message")
            if primary_result:
                delivered_to.append(str(destination))
                route_summaries.append(describe_target_route(destination, primary_route.get("delivery_path", ""), primary_route.get("route_client_label") or primary_route.get("delivery_client_kind")))
            else:
                delivery_errors.append(f"{destination}: send returned empty response")
        except Exception as exc:
            delivery_errors.append(f"{destination}: {exc}")

    ensure_task_not_cancelled(task_id)
    relay_log_delivered = False
    relay_target = str((primary_route or {}).get("relay_target") or "").strip()
    if relay_target and str(normalize_target(LOG_CHANNEL)) == relay_target and str(LOG_CHANNEL) != str(destination):
        relay_log_delivered = True
        if str(LOG_CHANNEL) not in delivered_to:
            delivered_to.append(str(LOG_CHANNEL))
        route_summaries.append(
            describe_target_route(
                LOG_CHANNEL,
                "direct_forward",
                (primary_route or {}).get("relay_source_client_kind") or (primary_route or {}).get("delivery_client_kind"),
            )
        )

    if LOG_CHANNEL and str(LOG_CHANNEL) != str(destination) and not relay_log_delivered:
        ensure_task_not_cancelled(task_id)
        log_access_map = await probe_target_access_map(client_map, LOG_CHANNEL)
        copied = None
        if primary_result and primary_route and ENABLE_LOG_FROM_DESTINATION:
            copy_client_kind = choose_log_copy_client_kind(
                (primary_route or {}).get("target_access"),
                log_access_map,
                preferred_client_kind=primary_route.get("delivery_client_kind"),
            )
            if copy_client_kind:
                try:
                    copied = await copy_result_to_target(client_map.get(copy_client_kind), primary_result, LOG_CHANNEL, settings)
                    ensure_task_not_cancelled(task_id)
                    if copied:
                        delivered_to.append(str(LOG_CHANNEL))
                        route_summaries.append(describe_target_route(LOG_CHANNEL, "direct_copy", copy_client_kind))
                except Exception as exc:
                    debug_log(f"Silent copy_result_to_target failed: {exc}")

        if not copied and primary_result:
            try:
                dest_chat_id = getattr(getattr(primary_result, "chat", None), "id", destination)
                msg_id = getattr(primary_result, "id", None)
                if dest_chat_id and msg_id:
                    copied = await copy_known_message_to_target(
                        client_map.get("main_bot") or ui_client,
                        dest_chat_id,
                        msg_id,
                        LOG_CHANNEL,
                        settings,
                    )
                    if copied:
                        delivered_to.append(str(LOG_CHANNEL))
                        route_summaries.append(describe_target_route(LOG_CHANNEL, "direct_copy", "main_bot"))
            except Exception as exc:
                debug_log(f"Silent direct log copy via main_bot failed: {exc}")

        if not copied:
            try:
                log_route = await deliver_target_with_routing(
                    ui_client,
                    task_id,
                    source_msg,
                    routing_settings,
                    LOG_CHANNEL,
                    client_map=client_map,
                    source_access=source_access,
                    index_no=index_no,
                    download_state=download_state,
                    allow_download_fallback=not bool(primary_result),
                )
                log_result = log_route.get("message")
                if log_result:
                    delivered_to.append(str(LOG_CHANNEL))
                    route_summaries.append(describe_target_route(LOG_CHANNEL, log_route.get("delivery_path", ""), log_route.get("route_client_label") or log_route.get("delivery_client_kind")))
                else:
                    if not primary_result:
                        delivery_errors.append(f"{LOG_CHANNEL}: send returned empty response")
                    else:
                        debug_log(f"Silent log send returned empty response for {LOG_CHANNEL}")
            except Exception as exc:
                if not primary_result:
                    delivery_errors.append(f"{LOG_CHANNEL}: {exc}")
                else:
                    debug_log(f"Silent log send error for {LOG_CHANNEL}: {exc}")

    if not delivered_to:
        raise RuntimeError("Delivery failed: " + " | ".join(delivery_errors))

    return delivered_to, delivery_errors, {
        "delivery_path": str(primary_route.get("delivery_path") if primary_route else ""),
        "delivery_client_kind": str(primary_route.get("delivery_client_kind") if primary_route else ""),
        "route_client_label": str((primary_route or {}).get("route_client_label") or (primary_route or {}).get("delivery_client_kind") or ""),
        "fallback_reason": str(download_state.get("fallback_reason") or ""),
        "route_summaries": route_summaries,
        "download_path": str(download_state.get("path") or ""),
    }

