from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *


async def handle_storage_callbacks(client, callback_query, user_id: int, data: str, s: dict):
    if data == "show_storage_mode":
        allowed = [mode for mode in ["telegram", "gdrive", "rclone"] if user_can_use_storage_mode(user_id, mode)] or ["telegram"]
        try:
            await callback_query.message.edit_text(
                advanced_settings_text(user_id),
                reply_markup=storage_mode_buttons(s.get("storage_mode", "telegram"), allowed_modes=allowed),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data == "cycle_storage_mode":
        current_mode = normalize_storage_mode(s.get("storage_mode", "telegram"))
        allowed = [mode for mode in ["telegram", "gdrive", "rclone"] if user_can_use_storage_mode(user_id, mode)] or ["telegram"]
        if len(allowed) == 1 and current_mode == allowed[0]:
            only_mode = allowed[0]
            await callback_query.answer(
                f"Storage Mode abhi {only_mode} par locked hai. Allowed: {', '.join(allowed)}",
                show_alert=True,
            )
            return True
        new_mode = get_next_allowed_storage_mode(current_mode, allowed)
        update_user_settings(user_id, {"storage_mode": new_mode})
        updated_settings = get_user_settings(user_id)
        try:
            await callback_query.message.edit_text(
                settings_home_text(user_id),
                reply_markup=build_settings_home_markup(user_id),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        reminder = build_missing_storage_target_text(updated_settings) if new_mode in {"gdrive", "rclone"} else ""
        answer_text = reminder.replace("`", "") if reminder else f"Storage Mode: {new_mode}"
        await callback_query.answer(answer_text[:180], show_alert=bool(reminder))
        return True

    if data.startswith("set_storage_mode:"):
        mode = normalize_storage_mode(data.split(":", 1)[1])
        if not user_can_use_storage_mode(user_id, mode):
            await callback_query.answer(f"Allowed: {', '.join(get_user_allowed_storage_modes(user_id))}", show_alert=True)
            return True
        update_user_settings(user_id, {"storage_mode": mode})
        updated_settings = get_user_settings(user_id)
        try:
            await callback_query.message.edit_text(
                settings_home_text(user_id),
                reply_markup=build_settings_home_markup(user_id),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        reminder = build_missing_storage_target_text(updated_settings) if mode in {"gdrive", "rclone"} else ""
        answer_text = reminder.replace("`", "") if reminder else f"Storage Mode: {mode}"
        await callback_query.answer(answer_text[:180], show_alert=bool(reminder))
        return True

    if data == "show_telegram_upload_mode":
        try:
            await callback_query.message.edit_text(
                upload_mode_text(user_id),
                reply_markup=upload_mode_buttons(get_user_telegram_upload_mode(user_id)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data == "show_gdrive_settings":
        try:
            await callback_query.message.edit_text(
                gdrive_text(user_id),
                reply_markup=gdrive_buttons(bool(s.get("gdrive_token_path")), bool(s.get("gdrive_folder_id"))),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data == "show_rclone_settings":
        try:
            await callback_query.message.edit_text(
                rclone_text(user_id),
                reply_markup=rclone_buttons(bool(s.get("rclone_config_path")), bool(s.get("rclone_remote_path"))),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data == "show_personal_bot_settings":
        try:
            await callback_query.message.edit_text(
                personal_bot_text(user_id),
                reply_markup=personal_bot_buttons(
                    bool(s.get("personal_bot_token")),
                    str(s.get("bot_delivery_mode", "main")).lower() == "personal",
                ),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data == "set_personal_bot_token":
        set_user_state(user_id, "set_personal_bot_token")
        await callback_query.message.reply_text(
            "Ab BotFather wala bot token bhejo.\nExample: `123456:ABCDEF...`\n\n/cancel bhej kar cancel kar sakte ho."
        )
        await callback_query.answer()
        return True

    if data == "show_route_template":
        try:
            await callback_query.message.edit_text(
                route_template_text(user_id),
                reply_markup=route_template_buttons(s.get("route_template", "off")),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data.startswith("set_route_template:"):
        template = str(data.split(":", 1)[1] or "off").strip().lower()
        if template not in {"off", "smart", "docs_to_gdrive", "media_to_telegram", "archives_to_rclone"}:
            template = "off"
        update_user_settings(user_id, {"route_template": template})
        try:
            await callback_query.message.edit_text(
                route_template_text(user_id),
                reply_markup=route_template_buttons(template),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer(f"Template: {template}")
        return True

    if data == "set_gdrive_token_file":
        set_user_state(user_id, "set_gdrive_token_file")
        await callback_query.message.reply_text(
            "Ab token.pickle file bhejo.\n\n/cancel bhej kar cancel kar sakte ho."
        )
        await callback_query.answer()
        return True

    if data == "set_gdrive_folder_id":
        set_user_state(user_id, "set_gdrive_folder_id")
        await callback_query.message.reply_text(
            "Ab Google Drive folder ID bhejo.\n\n/cancel bhej kar cancel kar sakte ho."
        )
        await callback_query.answer()
        return True

    if data == "clear_gdrive_settings":
        update_user_settings(user_id, {"gdrive_folder_id": "", "gdrive_token_path": "", "gdrive_last_file_link": ""})
        try:
            await callback_query.message.edit_text(
                gdrive_text(user_id),
                reply_markup=gdrive_buttons(False, False),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer("GDrive cleared")
        return True

    if data == "validate_gdrive_settings":
        try:
            result = await validate_gdrive_settings_for_user(get_user_settings(user_id))
            await callback_query.answer(f"OK {result.get('name', 'ok')}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"Error {e}", show_alert=True)
        return True

    if data == "set_rclone_config_file":
        set_user_state(user_id, "set_rclone_config_file")
        await callback_query.message.reply_text(
            "Ab rclone.conf file bhejo.\n\n/cancel bhej kar cancel kar sakte ho."
        )
        await callback_query.answer()
        return True

    if data == "set_rclone_remote_path":
        set_user_state(user_id, "set_rclone_remote_path")
        await callback_query.message.reply_text(
            "Ab remote path bhejo. Example: myremote:Telegram/Folder\n\n/cancel bhej kar cancel kar sakte ho."
        )
        await callback_query.answer()
        return True

    if data == "clear_rclone_settings":
        update_user_settings(user_id, {"rclone_config_path": "", "rclone_remote_path": "", "rclone_last_file_path": ""})
        try:
            await callback_query.message.edit_text(
                rclone_text(user_id),
                reply_markup=rclone_buttons(False, False),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer("Rclone cleared")
        return True

    if data == "validate_rclone_settings":
        try:
            result = await validate_rclone_settings_for_user(get_user_settings(user_id))
            await callback_query.answer(f"OK {result.get('path', 'ok')}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"Error {e}", show_alert=True)
        return True

    if data == "validate_current_destination":
        await callback_query.answer("Ye button settings se hata diya gaya hai.", show_alert=True)
        return True

    if data == "validate_personal_bot":
        token = str(s.get("personal_bot_token", "") or "").strip()
        if not token:
            await callback_query.answer("Bot token missing", show_alert=True)
            return True
        try:
            me = await validate_personal_bot_token(user_id, token)
            update_user_settings(user_id, {"personal_bot_username": getattr(me, "username", "") or ""})
            await callback_query.answer(f"OK @{getattr(me, 'username', 'unknown')}", show_alert=True)
        except Exception as e:
            await callback_query.answer(f"Error {e}", show_alert=True)
        return True

    if data == "toggle_personal_bot_mode":
        mode = "personal" if str(s.get("bot_delivery_mode", "main")).lower() != "personal" else "main"
        update_user_settings(user_id, {"bot_delivery_mode": mode})
        try:
            await callback_query.message.edit_text(
                personal_bot_text(user_id),
                reply_markup=personal_bot_buttons(bool(get_user_settings(user_id).get("personal_bot_token")), mode == "personal"),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer(f"Delivery bot: {mode}")
        return True

    if data == "remove_personal_bot":
        update_user_settings(user_id, {"personal_bot_token": "", "personal_bot_username": "", "bot_delivery_mode": "main"})
        await cleanup_personal_bot_client(user_id)
        try:
            await callback_query.message.edit_text(
                personal_bot_text(user_id),
                reply_markup=personal_bot_buttons(False, False),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer("Personal bot removed")
        return True

    if data == "show_id_help":
        await callback_query.answer("/id ko us channel/group/topic me chalao jahan bot admin ho", show_alert=True)
        return True

    if data == "noop":
        await callback_query.answer()
        return True

    return False
