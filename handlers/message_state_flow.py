from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from features.payment_manager import submit_order_utr, get_order
from features.plan_manager import (
    save_plan,
    update_plan_price,
    update_plan_limits,
    save_payment_config,
    get_payment_config,
)
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

        if state == "ADM_ADD_PLAN":
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            parts = [p.strip() for p in text_raw.split("|")]
            if len(parts) < 3:
                await message.reply_text(
                    "❌ Sahi format me bhejein:\n`id | Name | Price | DurationDays | BatchLimit | TaskLimit | StorageModes | Features`\n\n"
                    "*Example:*\n`pro | Pro Elite ⚡ | 249 | 30 | 250 | 5 | telegram,gdrive,personal_bot | 250 Links, 5 Tasks, Cloud Drive`\n\n"
                    "*(Cancel karne ke liye /cancel bhejein)*"
                )
                return True
            plan_id = parts[0].lower().replace(" ", "_")
            name = parts[1]
            try:
                price = int(parts[2])
            except Exception:
                price = 99
            duration = int(parts[3]) if len(parts) > 3 and parts[3].isdigit() else 30
            batch = int(parts[4]) if len(parts) > 4 and parts[4].isdigit() else 50
            tasks = int(parts[5]) if len(parts) > 5 and parts[5].isdigit() else 3
            modes = parts[6] if len(parts) > 6 and parts[6] else "telegram,personal_bot"
            features = [f.strip() for f in parts[7].split(",") if f.strip()] if len(parts) > 7 else [
                f"{batch} Batch Limit",
                f"{tasks} Parallel Tasks",
                f"{duration} Days Validity",
            ]

            save_plan({
                "id": plan_id,
                "name": name,
                "price": price,
                "duration_days": duration,
                "batch_limit": batch,
                "task_limit": tasks,
                "storage_modes": modes,
                "features": features,
                "is_active": True,
            })
            clear_user_state(user_id)
            await message.reply_text(
                f"✅ **Plan '{name}' successfully create ho gaya!**\n\n"
                f"🆔 ID: `{plan_id}`\n"
                f"💰 Price: `₹{price}`\n"
                f"⏳ Validity: `{duration} Days`\n"
                f"📦 Batch: `{batch}` | Tasks: `{tasks}`\n\n"
                f"Aap `/admin` ya `/buy` me check kar sakte hain."
            )
            return True

        if state.startswith("ADM_EDIT_PLAN_PRICE:"):
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            plan_id = state.split(":", 1)[1].strip()
            raw_val = text.replace("₹", "").replace(",", "").strip()
            if not raw_val.isdigit() or int(raw_val) <= 0:
                await message.reply_text("❌ Kripya sirf sahi number (price) bhejein (e.g. `149`).\nYa /cancel karein.")
                return True
            new_price = int(raw_val)
            ok = update_plan_price(plan_id, new_price)
            clear_user_state(user_id)
            if ok:
                await message.reply_text(f"✅ Plan `{plan_id}` ka price update ho kar **₹{new_price}** ho gaya hai!\n\n/admin me dekh sakte hain.")
            else:
                await message.reply_text(f"❌ Plan `{plan_id}` nahi mila.")
            return True

        if state.startswith("ADM_EDIT_PLAN_LIMITS:"):
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            plan_id = state.split(":", 1)[1].strip()
            parts = [p.strip() for p in text.split("|")]
            if len(parts) < 3 or not parts[0].isdigit() or not parts[1].isdigit() or not parts[2].isdigit():
                await message.reply_text(
                    "❌ Sahi format me bhejein: `BatchLimit | TaskLimit | DurationDays`\n*Example:* `200 | 5 | 30`\n\nYa /cancel karein."
                )
                return True
            batch = int(parts[0])
            tasks = int(parts[1])
            days = int(parts[2])
            ok = update_plan_limits(plan_id, batch, tasks, days)
            clear_user_state(user_id)
            if ok:
                await message.reply_text(
                    f"✅ Plan `{plan_id}` ke limits update ho gaye!\n• Batch: `{batch}`\n• Tasks: `{tasks}`\n• Validity: `{days} Days`\n\n/admin me dekh sakte hain."
                )
            else:
                await message.reply_text(f"❌ Plan `{plan_id}` nahi mila.")
            return True

        if state == "ADM_SET_PAYTM":
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            parts = text.split()
            if len(parts) < 2:
                await message.reply_text(
                    "❌ Format: `<MID> <KEY>` (space se alag karein)\n*Example:* `CodeDe1234567890 ABCD1234EFGH5678`\n\nYa /cancel karein."
                )
                return True
            mid = parts[0].strip()
            key = parts[1].strip()
            save_payment_config(paytm_mid=mid, paytm_key=key)
            clear_user_state(user_id)
            await message.reply_text(
                f"✅ **Paytm Merchant Credentials Saved!**\n\n"
                f"🆔 **Merchant ID:** `{mid}`\n"
                f"🔑 **Merchant Key:** Set (`{key[:4]}****`)\n"
                f"⚡ **Auto-Verification Status:** 🟢 Active\n\n"
                f"Ab koi bhi user payment karega toh Paytm gateway automatically verify kar dega!\n/admin se test kar sakte hain."
            )
            return True

        if state == "ADM_SET_UPI":
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            parts = [p.strip() for p in text.split("|")]
            upi = parts[0]
            if "@" not in upi:
                await message.reply_text("❌ Sahi UPI ID bhejein (e.g. `someone@okhdfcbank` ya `merchant@paytm`).\nYa /cancel karein.")
                return True
            name = parts[1] if len(parts) > 1 and parts[1] else "Code Devil Premium"
            save_payment_config(upi_id=upi, payee_name=name)
            clear_user_state(user_id)
            await message.reply_text(
                f"✅ **UPI Details Saved!**\n\n"
                f"🏦 **UPI ID:** `{upi}`\n"
                f"👤 **Payee Name:** `{name}`\n\n"
                f"Ab QR code is UPI ID par generate hoga."
            )
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
