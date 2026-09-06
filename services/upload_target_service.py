from __future__ import annotations

from runtime_context import *
from services.storage_service import *
from services.task_service import *
from services.delivery_service import *
from services.link_service import (
    get_thumbnail_temp_path,
    can_direct_copy,
    try_direct_copy,
)


async def upload_to_storage_target(client, task_id: str, source_msg, settings: dict, user_id: int, file_path: str, storage_mode: str, index_no: int = 0, fetch_mode: str = "bot", user_client=None):
    storage_mode = normalize_storage_mode(storage_mode)
    if storage_mode == "gdrive":
        info = await upload_file_to_gdrive(user_id, settings, file_path, source_msg=source_msg, index_no=index_no)
        delivered_to = ["gdrive"]
        delivery_errors = []
        if LOG_CHANNEL:
            try:
                log_settings = get_primary_telegram_settings(settings)
                await deliver_log_channel_with_best_effort(client, task_id, source_msg, log_settings, file_path, index_no=index_no, fetch_mode=fetch_mode, user_client=user_client)
                delivered_to.append(str(LOG_CHANNEL))
            except Exception as e:
                delivery_errors.append(f"{LOG_CHANNEL}: {e}")
        return delivered_to, delivery_errors, info
    if storage_mode == "rclone":
        info = await upload_file_to_rclone(user_id, settings, file_path, source_msg=source_msg, index_no=index_no)
        delivered_to = ["rclone"]
        delivery_errors = []
        if LOG_CHANNEL:
            try:
                log_settings = get_primary_telegram_settings(settings)
                await deliver_log_channel_with_best_effort(client, task_id, source_msg, log_settings, file_path, index_no=index_no, fetch_mode=fetch_mode, user_client=user_client)
                delivered_to.append(str(LOG_CHANNEL))
            except Exception as e:
                delivery_errors.append(f"{LOG_CHANNEL}: {e}")
        return delivered_to, delivery_errors, info
    raise RuntimeError("Unsupported storage mode")


async def upload_file_to_target(client, task_id: str, target, file_path: str, source_msg, settings: dict, index_no: int = 0):
    target = normalize_target(target)
    ensure_task_not_cancelled(task_id)
    caption = build_final_caption(source_msg, settings, index_no=index_no, storage_mode="telegram")
    caption = caption if str(caption or "").strip() else None
    caption_parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html")) if caption else None
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    thumb_path = None

    try:
        upload_mode = str(settings.get("upload_mode", "media") or "media").strip().lower()

        if source_msg.video or source_msg.document or source_msg.audio or source_msg.animation:
            await asyncio.sleep(0)
            thumb_path = await get_thumbnail_temp_path(client, settings, task_id=task_id)

        if source_msg.sticker:
            result = await execute_topic_aware_send(
                lambda **extra: client.send_sticker(
                    chat_id=target,
                    sticker=file_path,
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Sticker upload failed for {target}")
            return result

        if source_msg.video_note:
            result = await execute_topic_aware_send(
                lambda **extra: client.send_video_note(
                    chat_id=target,
                    video_note=file_path,
                    duration=getattr(source_msg.video_note, "duration", None),
                    length=getattr(source_msg.video_note, "length", None),
                    progress=progress_callback if ENABLE_UPLOAD_PROGRESS else None,
                    progress_args=(client, task_id, "uploading"),
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Video note upload failed for {target}")
            return result

        if upload_mode == "document":
            result = await execute_topic_aware_send(
                lambda **extra: client.send_document(
                    chat_id=target,
                    document=file_path,
                    caption=caption,
                    parse_mode=caption_parse_mode,
                    thumb=thumb_path if thumb_path else None,
                    progress=progress_callback if ENABLE_UPLOAD_PROGRESS else None,
                    progress_args=(client, task_id, "uploading"),
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Document upload failed for {target}")
            return result

        if source_msg.photo:
            result = await execute_topic_aware_send(
                lambda **extra: client.send_photo(
                    chat_id=target,
                    photo=file_path,
                    caption=caption,
                    parse_mode=caption_parse_mode,
                    progress=progress_callback if ENABLE_UPLOAD_PROGRESS else None,
                    progress_args=(client, task_id, "uploading"),
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Photo upload failed for {target}")
            return result

        if source_msg.video or source_msg.animation:
            result = await execute_topic_aware_send(
                lambda **extra: client.send_video(
                    chat_id=target,
                    video=file_path,
                    caption=caption,
                    parse_mode=caption_parse_mode,
                    thumb=thumb_path if thumb_path else None,
                    progress=progress_callback if ENABLE_UPLOAD_PROGRESS else None,
                    progress_args=(client, task_id, "uploading"),
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Video upload failed for {target}")
            return result

        if source_msg.audio:
            result = await execute_topic_aware_send(
                lambda **extra: client.send_audio(
                    chat_id=target,
                    audio=file_path,
                    caption=caption,
                    parse_mode=caption_parse_mode,
                    thumb=thumb_path if thumb_path else None,
                    progress=progress_callback if ENABLE_UPLOAD_PROGRESS else None,
                    progress_args=(client, task_id, "uploading"),
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Audio upload failed for {target}")
            return result

        if source_msg.voice:
            result = await execute_topic_aware_send(
                lambda **extra: client.send_voice(
                    chat_id=target,
                    voice=file_path,
                    caption=caption,
                    parse_mode=caption_parse_mode,
                    progress=progress_callback if ENABLE_UPLOAD_PROGRESS else None,
                    progress_args=(client, task_id, "uploading"),
                    **extra,
                ),
                topic_id,
            )
            if not result:
                raise RuntimeError(f"Voice upload failed for {target}")
            return result

        result = await execute_topic_aware_send(
            lambda **extra: client.send_document(
                chat_id=target,
                document=file_path,
                caption=caption,
                parse_mode=caption_parse_mode,
                thumb=thumb_path if thumb_path else None,
                progress=progress_callback,
                progress_args=(client, task_id, "uploading"),
                **extra,
            ),
            topic_id,
        )
        if not result:
            raise RuntimeError(f"Fallback document upload failed for {target}")
        return result
    finally:
        if thumb_path and os.path.exists(thumb_path):
            try:
                os.remove(thumb_path)
            except Exception:
                pass


async def send_text_to_target(client, target, source_msg, settings: dict, index_no: int = 0):
    target = normalize_target(target)
    topic_id = safe_topic_id(settings.get("topic_id", ""))
    raw_text = build_final_text(source_msg.text or source_msg.caption or "", source_msg, settings, index_no=index_no, storage_mode="telegram")
    final_text = ensure_non_empty_text(raw_text)
    parse_mode = get_parse_mode(settings.get("caption_parse_mode", "html")) if str(raw_text or "").strip() else None
    result = await execute_topic_aware_send(
        lambda **extra: client.send_message(
            chat_id=target,
            text=final_text,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
            **extra,
        ),
        topic_id,
    )
    if not result:
        raise RuntimeError(f"Text send failed for {target}")
    return result


async def copy_result_to_log_channel(client, delivered_message, settings: dict):
    if not LOG_CHANNEL:
        return None
    return await copy_result_to_target(client, delivered_message, LOG_CHANNEL, settings)


async def deliver_log_channel_with_best_effort(client, task_id: str, source_msg, telegram_settings: dict, download_path: str | None = None, index_no: int = 0, fetch_mode: str = "bot", user_client=None):
    if not LOG_CHANNEL:
        return None

    delivery_profile = analyze_telegram_media_delivery(source_msg, telegram_settings) if is_media_message(source_msg) else {}

    try:
        if is_media_message(source_msg):
            if fetch_mode == "bot" and can_direct_copy(source_msg, telegram_settings, fetch_mode="bot"):
                await asyncio.sleep(0)
                return await try_direct_copy(client, source_msg, LOG_CHANNEL, telegram_settings, index_no=index_no)
            if fetch_mode == "user" and user_client:
                direct = await try_direct_forward_with_user_client(user_client, source_msg, LOG_CHANNEL, telegram_settings, index_no=index_no)
                if direct:
                    return direct
            if delivery_profile.get("cached_send_allowed"):
                cached_client = user_client if fetch_mode == "user" and user_client else client
                await asyncio.sleep(0)
                cached = await send_cached_media_to_target(cached_client, LOG_CHANNEL, source_msg, telegram_settings, index_no=index_no)
                if cached:
                    return cached
    except Exception:
        pass

    if not download_path:
        return await deliver_one_target(client, task_id, source_msg, telegram_settings, LOG_CHANNEL, None, index_no=index_no)

    await asyncio.sleep(0)
    return await upload_file_to_target(client, task_id, LOG_CHANNEL, download_path, source_msg, telegram_settings, index_no=index_no)


async def deliver_one_target(client, task_id: str, source_msg, settings: dict, target, download_path=None, index_no: int = 0):
    if download_path:
        return await upload_file_to_target(client, task_id, target, download_path, source_msg, settings, index_no=index_no)

    if is_media_message(source_msg):
        if can_direct_copy(source_msg, settings, fetch_mode="bot"):
            direct = await try_direct_copy(client, source_msg, target, settings, index_no=index_no)
            if direct:
                return direct
        delivery_profile = analyze_telegram_media_delivery(source_msg, settings)
        if delivery_profile.get("cached_send_allowed"):
            cached = await send_cached_media_to_target(client, target, source_msg, settings, index_no=index_no)
            if cached:
                return cached
        download_path = await ensure_downloaded_source_file(
            client,
            task_id,
            source_msg,
            settings,
            index_no,
            {"path": None, "fallback_reason": "telegram_output_transform"},
            {"main_bot": True, "user_session": False, "personal_bot": False},
            {"main_bot": client, "user_session": None, "personal_bot": None},
        )
        return await upload_file_to_target(client, task_id, target, download_path, source_msg, settings, index_no=index_no)

    return await send_text_to_target(client, target, source_msg, settings, index_no=index_no)
