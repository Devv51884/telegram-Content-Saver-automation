import os
import re
from config import DATA_DIR
from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from features.payment_manager import (
    submit_order_utr,
    get_order,
    attach_order_screenshot,
    get_user_latest_pending_order,
)
from features.plan_manager import (
    save_plan,
    update_plan_price,
    update_plan_limits,
    update_plan_duration_price,
    save_payment_config,
    get_payment_config,
    set_custom_qr,
    get_plan_by_id,
    get_plan_duration_info,
    add_duration_option,
    update_duration_option,
    delete_duration_option,
)
from keyboards import admin_payment_approval_markup



def _extract_media_image_file_id(message) -> str:
    photo = getattr(message, "photo", None)
    if photo:
        if hasattr(photo, "file_id"):
            return str(photo.file_id)
        if isinstance(photo, (list, tuple)) and len(photo) > 0:
            return str(getattr(photo[-1], "file_id", ""))
    doc = getattr(message, "document", None)
    if doc:
        mime = str(getattr(doc, "mime_type", "") or "").lower()
        fname = str(getattr(doc, "file_name", "") or "").lower()
        if mime.startswith("image/") or fname.endswith((".jpg", ".jpeg", ".png", ".webp")):
            return str(getattr(doc, "file_id", ""))
    return ""



async def _send_admin_payment_notification(client, order_id: str, utr: str, user_id: int, order: dict, screenshot_file_id: str = ""):
    admin_card = (
        f"🔔 **New Payment Verification Request!**\n\n"
        f"🆔 **Order:** `#{order_id}`\n"
        f"👤 **User:** `{user_id}`\n"
        f"📦 **Plan:** `{order.get('plan_name')}`\n"
        f"💰 **Amount:** `₹{order.get('amount')}`\n"
        f"🧾 **UTR:** `{utr}`\n"
        f"📸 **Screenshot:** {'Attached ✅' if screenshot_file_id else 'None ❌'}\n"
        f"⏱️ **Time:** Just now\n\n"
        f"Verify karke neeche button dabayein:"
    )
    admin_markup = admin_payment_approval_markup(order_id, has_screenshot=bool(screenshot_file_id))

    targets = [t for t in [OWNER_ID, LOG_CHANNEL] if t]
    seen = set()
    for target in targets:
        if target in seen:
            continue
        seen.add(target)
        try:
            if screenshot_file_id:
                await client.send_photo(
                    chat_id=target,
                    photo=screenshot_file_id,
                    caption=admin_card,
                    reply_markup=admin_markup,
                )
            else:
                await client.send_message(
                    chat_id=target,
                    text=admin_card,
                    reply_markup=admin_markup,
                )
        except Exception:
            try:
                await client.send_message(
                    chat_id=target,
                    text=admin_card,
                    reply_markup=admin_markup,
                )
            except Exception:
                pass


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

    if not state and not lowered.startswith("/"):
        pending_order = get_user_latest_pending_order(user_id)
        if pending_order:
            order_id = pending_order.get("order_id")
            file_id = _extract_media_image_file_id(message)
            match = re.search(r"\b(\d{12})\b", text_raw or text)
            if file_id and match:
                utr = match.group(1)
                ok, response_msg = submit_order_utr(order_id, utr, screenshot_file_id=file_id)
                if ok:
                    clear_user_state(user_id)
                    order = get_order(order_id) or pending_order
                    await message.reply_text(
                        f"✅ **Payment Screenshot & UTR (#{utr}) Received!**\n\n"
                        f"Aapka payment proof submit ho gaya hai. Admin dwara verify hote hi **{order.get('plan_name', 'Plan')}** activate ho jayega."
                    )
                    await _send_admin_payment_notification(client, order_id, utr, user_id, order, screenshot_file_id=file_id)
                    return True
            elif file_id:
                attach_order_screenshot(order_id, file_id)
                set_user_state(user_id, f"AWAITING_UTR_FOR_PHOTO:{order_id}:{file_id}")
                await message.reply_text(
                    f"📸 **Payment Screenshot Received for Order #{order_id}!**\n\n"
                    f"Ab kripya is payment ka **12-digit UPI Reference / UTR Number** chat me type karke send karein taaki hum verify kar sakein.\n\n"
                    f"*(GPay, PhonePe ya Paytm receipt par 'UPI Ref No.' ya 'UTR' 12 digits ka hota hai)*"
                )
                return True
            elif match:
                utr = match.group(1)
                ok, response_msg = submit_order_utr(order_id, utr)
                if ok:
                    set_user_state(user_id, f"OPTIONAL_SCREENSHOT:{order_id}")
                    order = get_order(order_id) or pending_order
                    await message.reply_text(
                        f"✅ **UTR Received (#{utr}) for Order #{order_id}!**\n\n"
                        f"Aapka UTR submit ho gaya hai.\n\n"
                        f"📸 *Tip: Verification fast karne ke liye aap abhi payment receipt ka photo/screenshot bhi bhej sakte hain (Optional).*\n\n"
                        f"Ya seedha verification ka intezar karein."
                    )
                    await _send_admin_payment_notification(client, order_id, utr, user_id, order)
                    return True

    if state and not lowered.startswith("/cancel"):
        if state.startswith("AWAITING_PAYMENT_UTR:"):
            order_id = state.split(":", 1)[1]
            file_id = _extract_media_image_file_id(message)

            # Case 1: User sent photo WITH or WITHOUT caption
            if file_id:
                match = re.search(r"\b(\d{12})\b", text_raw)
                if match:
                    utr = match.group(1)
                    ok, response_msg = submit_order_utr(order_id, utr, screenshot_file_id=file_id)
                    if not ok:
                        await message.reply_text(f"{response_msg}\n\nDobara bhejien ya /cancel karein.")
                        return True

                    clear_user_state(user_id)
                    order = get_order(order_id) or {}
                    await message.reply_text(
                        f"✅ **Payment Screenshot & UTR (#{utr}) Received!**\n\n"
                        f"Aapka payment proof submit ho gaya hai. Admin dwara verify hote hi **{order.get('plan_name', 'Plan')}** activate ho jayega."
                    )
                    await _send_admin_payment_notification(client, order_id, utr, user_id, order, screenshot_file_id=file_id)
                    return True
                else:
                    attach_order_screenshot(order_id, file_id)
                    set_user_state(user_id, f"AWAITING_UTR_FOR_PHOTO:{order_id}:{file_id}")
                    await message.reply_text(
                        "📸 **Payment Screenshot Received!**\n\n"
                        "Ab kripya is payment ka **12-digit UPI Reference / UTR Number** chat me type karke send karein taaki hum verify kar sakein.\n\n"
                        "*(GPay, PhonePe ya Paytm receipt par 'UPI Ref No.' ya 'UTR' 12 digits ka hota hai)*"
                    )
                    return True

            # Case 2: User sent text only
            match = re.search(r"\b(\d{12})\b", text)
            if not match:
                await message.reply_text("❌ Sahi 12-digit UTR number bhejein (e.g. 424212345678), ya payment ka screenshot (photo) send karein.")
                return True

            utr = match.group(1)
            ok, response_msg = submit_order_utr(order_id, utr)
            if not ok:
                await message.reply_text(f"{response_msg}\n\nDobara sahi 12-digit UTR bhejo ya /cancel karo.")
                return True

            set_user_state(user_id, f"OPTIONAL_SCREENSHOT:{order_id}")
            order = get_order(order_id) or {}
            await message.reply_text(
                f"✅ **UTR Received (#{utr})!**\n\n"
                f"Aapka UTR submit ho gaya hai.\n\n"
                f"📸 *Tip: Verification fast karne ke liye aap abhi payment receipt ka photo/screenshot bhi bhej sakte hain (Optional).*\n\n"
                f"Ya seedha verification ka intezar karein."
            )
            await _send_admin_payment_notification(client, order_id, utr, user_id, order)
            return True

        if state.startswith("AWAITING_UTR_FOR_PHOTO:"):
            parts = state.split(":", 2)
            order_id = parts[1]
            file_id = parts[2] if len(parts) > 2 else ""

            match = re.search(r"\b(\d{12})\b", text)
            if not match:
                await message.reply_text("❌ Sahi 12-digit UTR number bhejein (e.g. 424212345678).")
                return True

            utr = match.group(1)
            ok, response_msg = submit_order_utr(order_id, utr, screenshot_file_id=file_id)
            if not ok:
                await message.reply_text(f"{response_msg}\n\nDobara sahi 12-digit UTR bhejo ya /cancel karo.")
                return True

            clear_user_state(user_id)
            order = get_order(order_id) or {}
            await message.reply_text(
                f"✅ **UTR Received (#{utr}) & Screenshot Attached!**\n\n"
                f"Aapka verification proof admin ko bhej diya gaya hai. Verification hote hi aapka **{order.get('plan_name', 'Plan')}** activate ho jayega."
            )
            await _send_admin_payment_notification(client, order_id, utr, user_id, order, screenshot_file_id=file_id)
            return True

        if state.startswith("OPTIONAL_SCREENSHOT:"):
            order_id = state.split(":", 1)[1]
            file_id = _extract_media_image_file_id(message)

            if file_id:
                attach_order_screenshot(order_id, file_id)
                clear_user_state(user_id)
                order = get_order(order_id) or {}
                await message.reply_text(
                    "📸 **Payment Screenshot Attach Ho Gaya Hai!**\n\n"
                    "Admin ko screenshot bhej diya gaya hai. Jald hi aapka plan activate ho jayega."
                )
                admin_markup = admin_payment_approval_markup(order_id, has_screenshot=False)
                caption = (
                    f"📸 **Attached Screenshot for Order #{order_id}**\n\n"
                    f"👤 User: `{user_id}`\n"
                    f"📦 Plan: `{order.get('plan_name')}`\n"
                    f"💰 Amount: `₹{order.get('amount')}`\n"
                    f"🧾 UTR: `{order.get('utr_number')}`\n\n"
                    f"Verify karke approve karein:"
                )
                if OWNER_ID:
                    try:
                        await client.send_photo(OWNER_ID, photo=file_id, caption=caption, reply_markup=admin_markup)
                    except Exception:
                        pass
                if LOG_CHANNEL and str(LOG_CHANNEL) != str(OWNER_ID):
                    try:
                        await client.send_photo(LOG_CHANNEL, photo=file_id, caption=caption, reply_markup=admin_markup)
                    except Exception:
                        pass
                return True
            else:
                clear_user_state(user_id)


        if state.startswith("ADM_EDIT_DUR_PRICE:"):
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            parts = state.split(":")
            plan_id = parts[1]
            dur_key = parts[2]
            try:
                price = int(text.strip())
                if price <= 0:
                    raise ValueError()
            except Exception:
                await message.reply_text("❌ Kripya valid price number bhejein (e.g. 49).")
                return True

            ok = update_plan_duration_price(plan_id, dur_key, price)
            clear_user_state(user_id)
            if ok:
                plan = get_plan_by_id(plan_id)
                dur_info = get_plan_duration_info(plan, dur_key)
                await message.reply_text(
                    f"✅ **Price Updated!**\n\nPlan: `{plan.get('name')}`\nDuration: `{dur_info['label']}`\nNew Price: `₹{price}`\n\nAb users ko yeh naya price dikhega."
                )
            else:
                await message.reply_text("❌ Price update fail hua. Plan nahi mila.")
            return True

        if state == "ADM_ADD_DUR_START":
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            parts = [p.strip() for p in text_raw.split(",")]
            if len(parts) < 3:
                await message.reply_text(
                    "❌ Sahi format me bhejein:\n`<key>, <label>, <days>, <emoji>`\n\n"
                    "**Example:** `60d, 2 Months, 60, 🗓️`\n\n"
                    "*(Cancel karne ke liye /cancel bhejein)*"
                )
                return True
            dur_key = parts[0].lower()
            label = parts[1]
            try:
                days = int(parts[2])
            except Exception:
                await message.reply_text("❌ Days valid number hona chahiye (e.g. 60).")
                return True
            emoji = parts[3] if len(parts) > 3 else "⏱️"
            ok, msg = add_duration_option(dur_key, label, days, emoji)
            clear_user_state(user_id)
            await message.reply_text(msg)
            return True

        if state.startswith("ADM_EDIT_DUR_INFO:"):
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            dur_key = state.split(":", 1)[1]
            parts = [p.strip() for p in text_raw.split(",")]
            if len(parts) < 2:
                await message.reply_text(
                    "❌ Sahi format me bhejein:\n`<label>, <days>, <emoji>`\n\n"
                    "**Example:** `2 Months, 60, 🗓️`\n\n"
                    "*(Cancel karne ke liye /cancel bhejein)*"
                )
                return True
            label = parts[0]
            try:
                days = int(parts[1])
            except Exception:
                await message.reply_text("❌ Days valid number hona chahiye (e.g. 60).")
                return True
            emoji = parts[2] if len(parts) > 2 else "⏱️"
            ok, msg = update_duration_option(dur_key, label=label, days=days, emoji=emoji)
            clear_user_state(user_id)
            await message.reply_text(msg)
            return True

        if state == "ADM_AWAITING_BROADCAST_MSG":
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True
            clear_user_state(user_id)
            from keyboards import admin_broadcast_confirm_markup
            await message.reply_text(
                "📢 **Broadcast Message Staged!**\n\n"
                "Upar diya gaya message sabhi registered users ko bhejne ke liye ready hai.\n\n"
                "Confirm karne ke liye neeche **'🚀 Confirm & Send to All Users'** button dabayein:",
                reply_markup=admin_broadcast_confirm_markup(message_id=message.id),
            )
            return True

        if state == "ADM_UPLOAD_CUSTOM_QR":
            if not is_admin(user_id):
                clear_user_state(user_id)
                return True

            file_id = _extract_media_image_file_id(message)

            if not file_id:
                await message.reply_text("❌ Kripya ek QR code image/photo send karein, ya /cancel karein.")
                return True

            save_dir = os.path.join(DATA_DIR, "qr")
            os.makedirs(save_dir, exist_ok=True)
            local_path = os.path.join(save_dir, "custom_qr.png")

            try:
                await message.download(file_name=local_path)
            except Exception:
                pass

            set_custom_qr(file_id=file_id, file_path=local_path if os.path.exists(local_path) else "")
            clear_user_state(user_id)
            await message.reply_text(
                "✅ **Custom QR Code Successfully Saved!**\n\n"
                "Ab users jab bhi kisi plan/duration ko select karenge, unhe payment ke liye yeh uploaded QR code dikhega.\n\n"
                "Aap `/admin` -> **Payment Gateway** me jaakar isko dekh ya remove kar sakte hain."
            )
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
