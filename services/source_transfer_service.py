from __future__ import annotations

from runtime_context import *
from services.storage_service import *
from services.task_service import *
from services.delivery_service import *
from services.upload_target_service import *
from services.link_service import *


def build_index_entry_impl(user_id: int, source_msg, link_text: str, info):
    content_type = (
        "photo" if source_msg.photo else
        "video" if source_msg.video else
        "video_note" if source_msg.video_note else
        "document" if source_msg.document else
        "audio" if source_msg.audio else
        "voice" if source_msg.voice else
        "animation" if source_msg.animation else
        "sticker" if source_msg.sticker else
        "text"
    )
    file_obj = (
        source_msg.photo if source_msg.photo else
        source_msg.video if source_msg.video else
        source_msg.video_note if source_msg.video_note else
        source_msg.document if source_msg.document else
        source_msg.audio if source_msg.audio else
        source_msg.voice if source_msg.voice else
        source_msg.animation if source_msg.animation else
        source_msg.sticker if source_msg.sticker else
        None
    )

    return {
        "user_id": user_id,
        "chat_id": getattr(source_msg.chat, "id", 0) if getattr(source_msg, "chat", None) else 0,
        "message_id": source_msg.id,
        "content_type": content_type,
        "text": source_msg.text or "",
        "caption": source_msg.caption or "",
        "file_id": getattr(file_obj, "file_id", "") if file_obj else "",
        "file_name": get_message_file_name(source_msg) if is_media_message(source_msg) else "",
        "file_size": get_message_file_size(source_msg),
        "source_link": (link_text or "").strip(),
        "link_type": info.get("link_type") if info else "",
        "created_at": now_iso(),
    }


async def process_source_message_transfer_impl(client, user_id: int, message, source_msg, task_id: str, settings: dict, destination, source_label: str, info: dict | None = None, user_client=None, fetch_mode: str = "bot", disconnect_user_client: bool = False):
    download_path = None
    delivered_to = []
    delivery_errors = []
    delivery_user_client = user_client
    disconnect_delivery_user_client = False
    delivery_summary = {}

    try:
        validation_error = get_transfer_validation_error(source_msg)
        if validation_error:
            raise RuntimeError(validation_error)

        entry = build_index_entry_impl(user_id, source_msg, source_label, info)
        idx_no = add_index_entry(entry)
        user_count_now = increase_index_user_count(user_id)
        user_index_no = get_next_user_index(user_id) - 1 or 1

        storage_mode = get_effective_storage_mode_for_message(user_id, source_msg, settings)
        if storage_mode != "telegram":
            ensure_storage_runtime_ready({**(settings or {}), "storage_mode": storage_mode}, ensure_shared_user_site_packages)
        telegram_settings = get_primary_telegram_settings(settings)
        source_link_type = normalize_link_type(info)
        client_map = {"main_bot": client, "user_session": None, "personal_bot": None}
        source_access = build_source_access_map(source_link_type, fetch_mode, False)
        if storage_mode == "telegram":
            delivery_user_client, disconnect_delivery_user_client = await get_or_create_delivery_user_client(user_id, user_client)
            client_map["user_session"] = delivery_user_client
            client_map["personal_bot"] = await get_or_create_personal_bot_client(user_id, settings)
            source_access = build_source_access_map(source_link_type, fetch_mode, bool(delivery_user_client))
        destination_label = destination
        if storage_mode == "gdrive":
            destination_label = str(settings.get("gdrive_folder_id", "") or "")
        elif storage_mode == "rclone":
            destination_label = str(settings.get("rclone_remote_path", "") or "")

        if not is_media_message(source_msg):
            if storage_mode == "telegram":
                touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": "Telegram text route", "is_visible": True})
                await update_task_status_message(client, task_id)
                delivered_to, delivery_errors, delivery_summary = await deliver_primary_then_log_routed(
                    client,
                    task_id,
                    source_msg,
                    telegram_settings,
                    destination,
                    user_id=user_id,
                    client_map=client_map,
                    source_access=source_access,
                    index_no=user_index_no,
                )
            else:
                text_path = create_temp_text_file(source_msg, settings, index_no=user_index_no, storage_mode=storage_mode)
                try:
                    touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": f"{storage_mode.title()} text route", "is_visible": True})
                    await update_task_status_message(client, task_id)
                    delivered_to, delivery_errors, storage_info = await upload_to_storage_target(client, task_id, source_msg, telegram_settings, user_id, text_path, storage_mode, index_no=user_index_no, fetch_mode=fetch_mode, user_client=user_client)
                    result_note = f"Index {idx_no} | Count {user_count_now} | {storage_mode.title()}"
                    if storage_info:
                        result_note += f" | {storage_info}"
                finally:
                    if os.path.exists(text_path):
                        try:
                            os.remove(text_path)
                        except Exception:
                            pass
                ensure_task_not_cancelled(task_id)
                touch_task(task_id, {
                    "status": "completed",
                    "current_stage": "completed",
                    "is_visible": True,
                    "index_id": idx_no,
                    "user_index_no": user_index_no,
                    "progress_text": result_note,
                    "delivered_to": delivered_to,
                    "delivery_errors": delivery_errors,
                    "error": "",
                    "destination": str(destination_label or ""),
                    "destination_display": str(destination_label or ""),
                    "storage_mode": storage_mode,
                })
                await update_task_status_message(client, task_id, done=True)
                if str((get_task(task_id) or {}).get("mode", "")).strip().lower() != "batch":
                    await message.reply_text(auto_index_completed_text({
                        "batch_name": entry.get("file_name") or entry.get("content_type") or "Single Link Job",
                        "valid_links": 1,
                        "success": 1,
                        "failed": 0,
                        "destination": str(destination_label or "Not Set"),
                        "index_no": idx_no,
                        "user_index_no": user_index_no,
                        "link_type": entry.get("link_type") or "unknown",
                    }), disable_web_page_preview=True)
                return
        else:
            if storage_mode == "telegram":
                delivered_to, delivery_errors, delivery_summary = await deliver_primary_then_log_routed(
                    client,
                    task_id,
                    source_msg,
                    telegram_settings,
                    destination,
                    user_id=user_id,
                    client_map=client_map,
                    source_access=source_access,
                    index_no=user_index_no,
                )
                download_path = str((delivery_summary or {}).get("download_path") or "")
            else:
                touch_task(task_id, {"status": "downloading", "current_stage": "downloading", "progress_text": f"{storage_mode.title()} fallback download path" if delivery_errors else "", "is_visible": True})
                await update_task_status_message(client, task_id)
                download_hint = get_temp_download_path(source_msg)
                source_client = user_client if user_client else client
                download_path = download_hint
                try:
                    download_result = await source_client.download_media(
                        source_msg,
                        file_name=download_hint,
                        progress=progress_callback,
                        progress_args=(client, task_id, "downloading"),
                    )
                    download_path = resolve_downloaded_path(download_hint, download_result)
                    ensure_valid_downloaded_file(download_path)
                    download_path = rename_downloaded_file(download_path, source_msg, settings, index_no=user_index_no)
                    ensure_valid_downloaded_file(download_path)
                except Exception:
                    safe_delete_local_file(download_path)
                    if download_path != download_hint:
                        safe_delete_local_file(download_hint)
                    raise
                ensure_task_not_cancelled(task_id)
                touch_task(task_id, {"status": "uploading", "current_stage": "uploading", "progress_text": f"{storage_mode.title()} upload route", "is_visible": True})
                await update_task_status_message(client, task_id)
                delivered_to, delivery_errors, storage_info = await upload_to_storage_target(client, task_id, source_msg, telegram_settings, user_id, download_path, storage_mode, index_no=user_index_no, fetch_mode=fetch_mode, user_client=user_client)

        ensure_task_not_cancelled(task_id)
        result_note = f"Index {idx_no} | Count {user_count_now}"
        if storage_mode != "telegram":
            result_note += f" | {storage_mode.title()}"
        route_summaries = (delivery_summary or {}).get("route_summaries") or []
        if route_summaries:
            result_note += " | " + " ; ".join(route_summaries[:2])
        if delivery_errors:
            result_note += " | Partial: " + " ; ".join(delivery_errors[:2])

        touch_task(task_id, {
            "status": "completed",
            "current_stage": "completed",
            "is_visible": True,
            "index_id": idx_no,
            "user_index_no": user_index_no,
            "progress_text": result_note,
            "delivered_to": delivered_to,
            "delivery_errors": delivery_errors,
            "error": "",
            "destination": str(destination_label or destination or ""),
            "destination_display": str(destination_label or destination or ""),
            "storage_mode": storage_mode,
            "delivery_path": str((delivery_summary or {}).get("delivery_path") or ""),
            "delivery_client_kind": str((delivery_summary or {}).get("delivery_client_kind") or ""),
            "route_client_label": str((delivery_summary or {}).get("route_client_label") or ""),
            "fallback_reason": str((delivery_summary or {}).get("fallback_reason") or ""),
        })
        await update_task_status_message(client, task_id, done=True)

        user_destination_text = str(destination_label or destination or settings.get("upload_destination") or "Not Set")
        is_batch_task = str((get_task(task_id) or {}).get("mode", "")).strip().lower() == "batch"
        if not is_batch_task:
            await message.reply_text(
                auto_index_completed_text({
                    "batch_name": entry.get("file_name") or entry.get("content_type") or "Single Link Job",
                    "valid_links": 1,
                    "success": 1,
                    "failed": 0,
                    "destination": user_destination_text,
                    "index_no": idx_no,
                    "user_index_no": user_index_no,
                    "link_type": entry.get("link_type") or "unknown",
                }),
                disable_web_page_preview=True,
            )

        if delivery_errors and not is_batch_task:
            await message.reply_text("ÃƒÂ¢Ã…Â¡Ã‚Â ÃƒÂ¯Ã‚Â¸Ã‚Â Kuch targets par send fail hua:\n" + "\n".join(delivery_errors[:5]))

    finally:
        if disconnect_delivery_user_client and delivery_user_client and delivery_user_client is not user_client:
            if not is_cached_authorized_user_client(user_id, delivery_user_client):
                try:
                    await safe_close_client(delivery_user_client)
                except Exception:
                    pass
        if disconnect_user_client and user_client:
            if not is_cached_authorized_user_client(user_id, user_client):
                try:
                    await safe_close_client(user_client)
                except Exception:
                    pass
        safe_delete_local_file(download_path)


async def _perform_transfer_impl(client, user_id: int, message, link_text: str, task_id: str, settings: dict, destination):
    touch_task(task_id, {"status": "fetching", "current_stage": "fetching", "progress_text": "", "is_visible": False})
    await update_task_status_message(client, task_id)

    ensure_task_not_cancelled(task_id)
    source_msg, info, user_client, fetch_mode = await fetch_message_via_best_client(client, user_id, link_text)
    if not source_msg:
        raise RuntimeError("Source message fetch nahi ho paya. Public access ya authorized login required.")

    await process_source_message_transfer_impl(
        client,
        user_id,
        message,
        source_msg,
        task_id,
        settings,
        destination,
        link_text,
        info=info,
        user_client=user_client,
        fetch_mode=fetch_mode,
        disconnect_user_client=True,
    )
