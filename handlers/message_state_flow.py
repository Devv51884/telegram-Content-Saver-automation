from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from features.payment_manager import submit_order_utr, get_order
from keyboards import admin_payment_approval_markup


async def handle_message_state_and_profile(client, message, user_id: int, text_raw: str, text: str, lowered: str, state: str):
    if lowered.startswith("/login"):
        if has_user_session(user_id):
            await message.reply_text(login_status_text(user_id), reply_markup=login_buttons(True))
            return True
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        set_user_state(user_id, "login_phone")
        await message.reply_text(ask_phone_text())
        return True

    if lowered.startswith("/set_bot"):
        token = (message.text or "").split(maxsplit=1)
        if len(token) < 2:
            await message.reply_text("Use: /set_bot <bot_token>")
            return True
        bot_token = token[1].strip()
        try:
            me = await validate_personal_bot_token(user_id, bot_token)
            await cleanup_personal_bot_client(user_id)
            update_user_settings(
                user_id,
                {
                    "personal_bot_token": bot_token,
                    "personal_bot_username": getattr(me, "username", "") or "",
                    "bot_delivery_mode": "personal",
                },
            )
            await message.reply_text(f"Personal bot saved: @{getattr(me, 'username', 'unknown')}")
        except Exception as e:
            await message.reply_text(f"Personal bot invalid: {e}")
        return True

    if lowered.startswith("/bot_status"):
        await message.reply_text(personal_bot_text(user_id), disable_web_page_preview=True)
        return True

    if lowered.startswith("/remove_bot"):
        update_user_settings(user_id, {"personal_bot_token": "", "personal_bot_username": "", "bot_delivery_mode": "main"})
        await cleanup_personal_bot_client(user_id)
        await message.reply_text("Personal bot removed.")
        return True

    if lowered.startswith("/id"):
        try:
            chat = await client.get_chat(message.chat.id)
            await message.reply_text(
                id_info_text(chat, getattr(message, "message_thread_id", None)),
                disable_web_page_preview=True,
            )
        except Exception as e:
            await message.reply_text(f"ID fetch failed: {e}")
        return True

    if state == "login_phone" and not lowered.startswith("/"):
        phone = text.replace(" ", "")
        try:
            await begin_login_flow(user_id, phone)
            await message.reply_text(ask_code_text())
            return True
        except PhoneNumberInvalid:
            await message.reply_text(login_failed_text("Invalid phone number."))
            return True
        except FloodWait as e:
            await message.reply_text(login_failed_text(f"FloodWait: {e.value}s"))
            return True
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return True

    if state == "login_code" and not lowered.startswith("/"):
        code = text.replace(" ", "")
        try:
            _, phone = await finish_login_with_code(user_id, code)
            await message.reply_text(login_success_text(phone))
            return True
        except SessionPasswordNeeded:
            await message.reply_text(ask_password_text())
            return True
        except PhoneCodeInvalid:
            await message.reply_text(login_failed_text("Invalid OTP / code."))
            return True
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return True

    if state == "login_password" and not lowered.startswith("/"):
        try:
            _, phone = await finish_login_with_password(user_id, text)
            await message.reply_text(login_success_text(phone))
            return True
        except PasswordHashInvalid:
            await message.reply_text(login_failed_text("Wrong password."))
            return True
        except Exception as e:
            await message.reply_text(login_failed_text(str(e)))
            return True

    if state == "set_batch_links" and not lowered.startswith("/"):
        save_batch_input(user_id, text_raw)
        clear_user_state(user_id)
        await message.reply_text("Batch links save ho gaye.\n/settings me Batch section se Start Batch chala sakte ho.")
        return True

    if state in {"set_gdrive_token_file", "set_rclone_config_file"} and message.document and not lowered.startswith("/cancel"):
        if state == "set_gdrive_token_file":
            dest_path = derive_gdrive_token_dest(user_id, message.document.file_name or "token.pickle")
        else:
            dest_path = derive_rclone_config_dest(user_id, message.document.file_name or "rclone.conf")
        try:
            result = await message.download(file_name=dest_path)
            final_path = resolve_downloaded_path(dest_path, result)
            ensure_valid_downloaded_file(final_path)
            if state == "set_gdrive_token_file":
                update_user_settings(user_id, {"gdrive_token_path": final_path})
                success_text = "token.pickle save ho gayi.\n\n/settings bhejo dekhne ke liye."
            else:
                update_user_settings(user_id, {"rclone_config_path": final_path})
                success_text = "rclone config file save ho gayi.\n\n/settings bhejo dekhne ke liye."
            clear_user_state(user_id)
            await message.reply_text(success_text)
        except Exception as e:
            await message.reply_text(f"File save failed: {e}")
        return True

    if state and not lowered.startswith("/cancel"):
        if state.startswith("AWAITING_PAYMENT_UTR:"):
            order_id = state.split(":", 1)[1]
            utr = text.strip()
            ok, response_msg = submit_order_utr(order_id, utr)
            if not ok:
                await message.reply_text(f"{response_msg}\n\nDobara sahi 12-digit UTR bhejo ya /cancel karo.")
                return True

            clear_user_state(user_id)
            order = get_order(order_id) or {}
            await message.reply_text(
                f"✅ **UTR Received (#{utr})**\n\n"
                f"Aapka UTR submit ho gaya hai. Verification hote hi aapka **{order.get('plan_name', 'Plan')}** activate ho jayega."
            )

            admin_card = (
                f"🔔 **New Payment UTR Submitted!**\n\n"
                f"🆔 **Order:** `#{order_id}`\n"
                f"👤 **User:** `{user_id}`\n"
                f"📦 **Plan:** `{order.get('plan_name')}`\n"
                f"💰 **Amount:** `₹{order.get('amount')}`\n"
                f"🧾 **UTR:** `{utr}`\n"
                f"⏱️ **Time:** Just now\n\n"
                f"Verify karke neeche button dabayein:"
            )
            admin_markup = admin_payment_approval_markup(order_id)
            if OWNER_ID:
                try:
                    await client.send_message(OWNER_ID, admin_card, reply_markup=admin_markup)
                except Exception:
                    pass
            if LOG_CHANNEL and str(LOG_CHANNEL) != str(OWNER_ID):
                try:
                    await client.send_message(LOG_CHANNEL, admin_card, reply_markup=admin_markup)
                except Exception:
                    pass
            return True

        setting_key = WAITING_KEYS.get(state)

        if setting_key == "thumbnail_file_id":
            if message.photo:
                update_user_settings(user_id, {"thumbnail_file_id": message.photo.file_id, "thumbnail_enabled": True})
                clear_user_state(user_id)
                await message.reply_text("Custom thumbnail save ho gaya.\n\n/settings bhejo dekhne ke liye.")
                return True
            await message.reply_text("Thumbnail ke liye photo bhejna zaroori hai. /cancel bhej kar cancel kar sakte ho.")
            return True

        if setting_key:
            value = text
            if setting_key in {"caption_index_padding", "caption_index_start", "filename_index_padding", "filename_index_start"}:
                if not value.isdigit():
                    await message.reply_text("Yahan sirf number bhejo.\n/cancel bhej kar cancel kar sakte ho.")
                    return True
                value = int(value)

            if setting_key == "topic_id" and value and not value.lstrip("-").isdigit():
                await message.reply_text("Topic ID sirf number hona chahiye.\n/cancel bhej kar cancel kar sakte ho.")
                return True

            if setting_key == "personal_bot_token":
                try:
                    me = await validate_personal_bot_token(user_id, value)
                    await cleanup_personal_bot_client(user_id)
                    update_user_settings(
                        user_id,
                        {
                            "personal_bot_token": value,
                            "personal_bot_username": getattr(me, "username", "") or "",
                            "bot_delivery_mode": "personal",
                        },
                    )
                    clear_user_state(user_id)
                    await message.reply_text(
                        f"Personal bot save ho gaya: @{getattr(me, 'username', 'unknown')}\n\n/settings bhejo dekhne ke liye."
                    )
                except Exception as e:
                    await message.reply_text(f"Personal bot invalid: {e}\n\n/cancel bhej kar cancel kar sakte ho.")
                return True

            if setting_key == "replace_words":
                update_replace_rule_settings(user_id, get_user_settings(user_id), file_rules=value, caption_rules=value)
            elif setting_key == "replace_words_file":
                update_replace_rule_settings(user_id, get_user_settings(user_id), file_rules=value)
            elif setting_key == "replace_words_caption":
                update_replace_rule_settings(user_id, get_user_settings(user_id), caption_rules=value)
            elif setting_key == "caption_text":
                current_settings = get_user_settings(user_id)
                caption_state = get_caption_settings_for_mode(current_settings)
                update_user_settings(
                    user_id,
                    {
                        caption_state["text_key"]: value,
                        caption_state["enabled_key"]: True,
                    },
                )
            else:
                update_user_settings(user_id, {setting_key: value})

            if setting_key in {"auto_rename", "rename_template", "filename_prefix", "filename_suffix"}:
                update_user_settings(user_id, {"auto_rename_enabled": True})
            if setting_key.startswith("metadata_"):
                update_user_settings(user_id, {"metadata_enabled": True})

            clear_user_state(user_id)
            await message.reply_text(
                f"`{setting_key.replace('_', ' ').title()}` update ho gaya.\n\n/settings bhejo dekhne ke liye."
            )
            return True

    return False
