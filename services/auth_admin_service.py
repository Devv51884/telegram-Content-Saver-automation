from __future__ import annotations

from runtime_context import *
from services.storage_service import *
from features.plan_manager import (
    get_payment_config,
    save_payment_config,
    get_all_plans,
    get_plan_by_id,
    save_plan,
    delete_plan,
    toggle_plan_status,
    update_plan_price,
    update_plan_limits,
    reset_default_plans,
)
from features.payment_manager import get_pending_orders
import asyncio

async def start_login_client(user_id: int):
    existing = TEMP_LOGIN_CLIENTS.get(user_id)

    if existing:
        try:
            await asyncio.sleep(0)
            await existing.get_me()
            return existing
        except Exception:
            try:
                await existing.disconnect()
            except Exception:
                pass

    login_client = Client(
        name=f"login_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        in_memory=True,
        workers=1,
    )

    await asyncio.sleep(0)

    try:
        await asyncio.wait_for(
            login_client.connect(),
            timeout=12
        )
    except asyncio.TimeoutError:
        raise RuntimeError("Telegram connection timeout. Dobara try karo.")

    TEMP_LOGIN_CLIENTS[user_id] = login_client
    return login_client


async def get_or_create_login_client(user_id: int):
    existing = TEMP_LOGIN_CLIENTS.get(user_id)
    if existing:
        return existing
    return await start_login_client(user_id)


async def cleanup_login_client(user_id: int):
    client_obj = TEMP_LOGIN_CLIENTS.pop(user_id, None)
    if client_obj:
        try:
            await client_obj.disconnect()
        except Exception:
            pass


async def begin_login_flow(user_id: int, phone: str):
    login_client = await get_or_create_login_client(user_id)

    try:
        sent = await asyncio.wait_for(
            login_client.send_code(phone),
            timeout=15
        )

    except asyncio.TimeoutError:
        await cleanup_login_client(user_id)
        raise RuntimeError("OTP request timeout. Dobara try karo.")

    except Exception as e:
        await cleanup_login_client(user_id)
        raise RuntimeError(f"OTP send failed: {e}")

    set_login_temp(user_id, "phone", phone)
    set_login_temp(user_id, "phone_code_hash", sent.phone_code_hash)
    set_user_state(user_id, "login_code")


async def finish_login_with_code(user_id: int, code: str):
    phone = get_login_temp(user_id, "phone", "")
    phone_code_hash = get_login_temp(user_id, "phone_code_hash", "")

    if not phone or not phone_code_hash:
        raise RuntimeError("Login session data missing. Dobara /login try karo.")

    login_client = await get_or_create_login_client(user_id)

    try:
        await login_client.sign_in(
            phone_number=phone,
            phone_code_hash=phone_code_hash,
            phone_code=code,
        )
    except SessionPasswordNeeded:
        set_user_state(user_id, "login_password")
        raise

    me = await login_client.get_me()
    session_string = await login_client.export_session_string()
    await asyncio.sleep(0)
    save_user_session(user_id, session_string, tg_user_id=me.id, phone=phone)
    clear_login_temp(user_id)
    clear_user_state(user_id)
    await cleanup_login_client(user_id)
    return me, phone


async def finish_login_with_password(user_id: int, password: str):
    phone = get_login_temp(user_id, "phone", "")
    login_client = await get_or_create_login_client(user_id)
    await login_client.check_password(password=password)

    me = await login_client.get_me()
    session_string = await login_client.export_session_string()
    await asyncio.sleep(0)
    save_user_session(user_id, session_string, tg_user_id=me.id, phone=phone)
    clear_login_temp(user_id)
    clear_user_state(user_id)
    await cleanup_login_client(user_id)
    return me, phone


async def send_broadcast_to_user(client, uid: int, reply_msg, broadcast_text: str):
    if reply_msg:
        if reply_msg.photo:
            return await client.send_photo(uid, photo=reply_msg.photo.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.video:
            return await client.send_video(uid, video=reply_msg.video.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.document:
            return await client.send_document(uid, document=reply_msg.document.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.audio:
            return await client.send_audio(uid, audio=reply_msg.audio.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.voice:
            return await client.send_voice(uid, voice=reply_msg.voice.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.animation:
            return await client.send_animation(uid, animation=reply_msg.animation.file_id, caption=broadcast_text or reply_msg.caption or "")
        if reply_msg.text:
            return await client.send_message(uid, broadcast_text or reply_msg.text, disable_web_page_preview=True)
        raise RuntimeError("Unsupported broadcast reply message type.")

    if not broadcast_text:
        raise RuntimeError("Empty broadcast text.")

    return await client.send_message(uid, f"ðŸ“¢ **Code Devil Broadcast**\n\n{broadcast_text}", disable_web_page_preview=True)


async def handle_admin_commands(client, message, lowered: str):
    user_id = message.from_user.id
    if not is_admin(user_id):
        return False

    if lowered.startswith("/admin") or lowered.startswith("/panel"):
        from texts import admin_panel_text
        from keyboards import admin_panel_buttons
        await message.reply_text(
            admin_panel_text(),
            reply_markup=admin_panel_buttons(),
            disable_web_page_preview=True,
        )
        return True

    if lowered.startswith("/stats"):
        await message.reply_text(admin_stats_text(get_detailed_stats()), disable_web_page_preview=True)
        return True

    if lowered.startswith("/supabase_status"):
        status = get_supabase_status()
        schema_state = status.get("schema_state", {}) or {}
        await message.reply_text(
            "\n".join([
                "🔄 **Supabase Status**",
                "",
                f"Enabled: **{'Yes' if status.get('enabled') else 'No'}**",
                f"Project URL: **{'Present' if status.get('has_url') else 'Missing'}**",
                f"API Key: **{'Present' if status.get('has_key') else 'Missing'}**",
                f"Key Role: **{status.get('key_role', 'unknown')}**",
                f"DB URL: **{'Present' if status.get('has_db_url') else 'Missing'}**",
                f"Schema Ready: **{'Yes' if schema_state.get('ready') else 'No'}**",
                f"Message: `{schema_state.get('message', '')}`",
            ]),
            disable_web_page_preview=True,
        )
        return True

    if lowered.startswith("/storage_status"):
        status = get_storage_runtime_status()
        data_dir = status.get("data_dir", {}) or {}
        temp_dir = status.get("temp_dir", {}) or {}
        backup_dir = status.get("backup_dir", {}) or {}
        cache_dir = status.get("cache_dir", {}) or {}
        persistent_data_dir = str(status.get("persistent_data_dir", "") or "").strip()
        persistence_label = "Configured" if status.get("data_on_persistent_dir") else "Ephemeral local path"
        if persistent_data_dir and status.get("temp_on_persistent_dir"):
            persistence_label += " | Temp also on persistent disk"
        await message.reply_text(
            "\n".join([
                "ðŸ’½ **Storage Status**",
                "",
                f"Persistence: **{persistence_label}**",
                f"Persistent Data Dir: `{persistent_data_dir or 'Not Set'}`",
                f"Data Dir: `{data_dir.get('path', '')}` | `{data_dir.get('files', 0)}` files | `{human_bytes(data_dir.get('bytes', 0))}`",
                f"Temp Dir: `{temp_dir.get('path', '')}` | `{temp_dir.get('files', 0)}` files | `{human_bytes(temp_dir.get('bytes', 0))}`",
                f"Cache Dir: `{cache_dir.get('path', '')}` | `{cache_dir.get('files', 0)}` files | `{human_bytes(cache_dir.get('bytes', 0))}`",
                f"Backup Dir: `{backup_dir.get('path', '')}` | `{backup_dir.get('files', 0)}` files | `{human_bytes(backup_dir.get('bytes', 0))}`",
            ]),
            disable_web_page_preview=True,
        )
        return True

    if lowered.startswith("/backup"):
        backup = create_backup_snapshot(label="manual")
        caption = "\n".join([
            "ðŸ—ƒ **Local Backup Created**",
            f"Created: `{backup.get('created_at', '')}`",
            f"Files: `{len(backup.get('summary', {}))}`",
            f"Stored In: `{os.path.basename(backup.get('path', ''))}`",
            "Cloud DB sync is not used for this backup.",
        ])
        await client.send_document(
            chat_id=message.chat.id,
            document=backup.get("path"),
            caption=caption,
        )
        return True

    if lowered.startswith("/restore"):
        parts = (message.text or "").split(maxsplit=1)
        restore_target = None
        reply_document = getattr(getattr(message, "reply_to_message", None), "document", None)
        if reply_document:
            restore_target = reply_document
        elif len(parts) > 1 and parts[1].strip().lower() == "latest":
            backup_dir = str(getattr(cfg, "BACKUP_DIR", "") or "")
            if backup_dir and os.path.isdir(backup_dir):
                candidates = sorted(
                    [os.path.join(backup_dir, item) for item in os.listdir(backup_dir) if item.lower().endswith(".json")],
                    reverse=True,
                )
                if candidates:
                    result = restore_backup_snapshot(candidates[0], sync_remote=True)
                    await message.reply_text(
                        "\n".join([
                            "♻️ **Restore Complete**",
                            f"Source: `{os.path.basename(candidates[0])}`",
                            f"Restored: `{', '.join(result.get('restored', []))}`",
                            f"Supabase Sync: `{', '.join((result.get('sync', {}) or {}).get('synced', [])) or 'none'}`",
                        ]),
                        disable_web_page_preview=True,
                    )
                    return True
        if not restore_target:
            await message.reply_text("Use: `/restore latest` ya kisi backup JSON file par reply karke `/restore` bhejo.", disable_web_page_preview=True)
            return True

        download_path = os.path.join(TEMP_DIR, f"restore_{uuid.uuid4().hex[:8]}.json")
        cleanup_path = download_path
        try:
            saved_path = await client.download_media(restore_target, file_name=download_path)
            cleanup_path = saved_path or download_path
            result = restore_backup_snapshot(cleanup_path, sync_remote=True)
            await message.reply_text(
                "\n".join([
                    "♻️ **Restore Complete**",
                    f"Restored: `{', '.join(result.get('restored', []))}`",
                    f"Supabase Sync: `{', '.join((result.get('sync', {}) or {}).get('synced', [])) or 'none'}`",
                ]),
                disable_web_page_preview=True,
            )
        finally:
            if cleanup_path and os.path.exists(cleanup_path):
                try:
                    os.remove(cleanup_path)
                except Exception:
                    pass
        return True

    if lowered.startswith("/users"):
        users = get_all_users_page(limit=50, offset=0)
        await message.reply_text(all_users_text(users, title="All Users"), disable_web_page_preview=True)
        return True

    if lowered.startswith("/recent_users"):
        await message.reply_text(all_users_text(get_recent_users(20), title="Recent Users"), disable_web_page_preview=True)
        return True

    if lowered.startswith("/set_batch_limit"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            await message.reply_text("Use: /set_batch_limit user_id 500")
            return True
        record = save_user_limit_record(int(parts[1]), {"batch_limit": int(parts[2])})
        await message.reply_text(f"✅ Batch limit updated\nUser: `{parts[1]}`\nBatch Limit: `{record.get('batch_limit', 0)}`")
        return True

    if lowered.startswith("/set_task_limit"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[1].isdigit() or not parts[2].isdigit():
            await message.reply_text("Use: /set_task_limit user_id 10")
            return True
        record = save_user_limit_record(int(parts[1]), {"task_limit": int(parts[2])})
        await message.reply_text(f"✅ Task limit updated\nUser: `{parts[1]}`\nTask Limit: `{record.get('task_limit', 0)}`")
        return True

    if lowered.startswith("/set_storage_access"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /set_storage_access user_id telegram,gdrive,rclone,personal_bot")
            return True
        record = save_user_limit_record(int(parts[1]), {"allowed_storage_modes": parts[2].strip()})
        await message.reply_text(f"✅ Storage access updated\nUser: `{parts[1]}`\nModes: `{record.get('allowed_storage_modes', '')}`")
        return True

    if lowered.startswith("/set_paytm"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3:
            await message.reply_text("Use: /set_paytm <merchant_mid> <merchant_key>")
            return True
        mid = parts[1].strip()
        key = parts[2].strip()
        save_payment_config(paytm_mid=mid, paytm_key=key)
        await message.reply_text(f"✅ Paytm Business credentials saved!\nMID: `{mid}`\nStatus: 🟢 Auto-Verification Active")
        return True

    if lowered.startswith("/set_upi"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 2:
            await message.reply_text("Use: /set_upi <upi_id> [payee_name]")
            return True
        upi = parts[1].strip()
        name = parts[2].strip() if len(parts) > 2 else "Code Devil Premium"
        save_payment_config(upi_id=upi, payee_name=name)
        await message.reply_text(f"✅ Payment UPI ID saved!\nUPI ID: `{upi}`\nPayee Name: `{name}`")
        return True

    if lowered.startswith("/payment_settings"):
        cfg = get_payment_config()
        paytm_status = "🟢 Connected (Auto-Check Active)" if cfg.get("paytm_mid") and cfg.get("paytm_key") else "⚪ Not set (Using UPI UTR mode)"
        await message.reply_text(
            f"⚙️ **Payment Gateway Settings**\n\n"
            f"🏦 **UPI ID:** `{cfg.get('upi_id') or 'Not set'}`\n"
            f"👤 **Payee Name:** `{cfg.get('payee_name') or 'Code Devil'}`\n"
            f"⚡ **Paytm Auto-Check:** {paytm_status}\n"
            f"🆔 **Paytm MID:** `{cfg.get('paytm_mid') or 'None'}`\n\n"
            f"Commands:\n"
            f"• `/set_upi someone@upi Code Devil`\n"
            f"• `/set_paytm <MID> <KEY>`"
        )
        return True

    if lowered.startswith("/pending_orders"):
        orders = get_pending_orders()
        if not orders:
            await message.reply_text("ℹ️ Koi pending order nahi hai.")
            return True
        lines = ["📋 **Pending Payment Orders:**\n"]
        for o in orders[:10]:
            lines.append(f"• `#{o.get('order_id')}` | User: `{o.get('user_id')}` | ₹{o.get('amount')} ({o.get('plan_name')}) | UTR: `{o.get('utr_number') or 'None'}`")
        await message.reply_text("\n".join(lines))
        return True

    if lowered.startswith("/add_plan"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or "|" not in parts[1]:
            await message.reply_text(
                "Use: `/add_plan id | Name | Price | DurationDays | BatchLimit | TaskLimit | StorageModes | Features`\n\n"
                "*Example:*\n`/add_plan pro | Pro 🚀 | 249 | 30 | 250 | 5 | telegram,gdrive | 250 Links, 5 Tasks`"
            )
            return True
        raw_parts = [p.strip() for p in parts[1].split("|")]
        if len(raw_parts) < 3:
            await message.reply_text("❌ Kam se kam id, Name, aur Price dena zaroori hai.")
            return True
        plan_id = raw_parts[0].lower().replace(" ", "_")
        name = raw_parts[1]
        try:
            price = int(raw_parts[2])
        except Exception:
            price = 99
        duration = int(raw_parts[3]) if len(raw_parts) > 3 and raw_parts[3].isdigit() else 30
        batch = int(raw_parts[4]) if len(raw_parts) > 4 and raw_parts[4].isdigit() else 50
        tasks = int(raw_parts[5]) if len(raw_parts) > 5 and raw_parts[5].isdigit() else 3
        modes = raw_parts[6] if len(raw_parts) > 6 and raw_parts[6] else "telegram,personal_bot"
        features = [f.strip() for f in raw_parts[7].split(",") if f.strip()] if len(raw_parts) > 7 else [
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
        await message.reply_text(f"✅ Plan '{name}' (`{plan_id}`) ₹{price} successfully save ho gaya!")
        return True

    if lowered.startswith("/toggle_plan"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("Use: /toggle_plan <plan_id>")
            return True
        plan_id = parts[1].strip().lower()
        new_status = toggle_plan_status(plan_id)
        if new_status is None:
            await message.reply_text(f"❌ Plan `{plan_id}` nahi mila.")
        else:
            status_word = "🟢 Active" if new_status else "🔴 Disabled"
            await message.reply_text(f"Plan `{plan_id}` ab {status_word} hai!")
        return True

    if lowered.startswith("/delete_plan"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2:
            await message.reply_text("Use: /delete_plan <plan_id>")
            return True
        plan_id = parts[1].strip().lower()
        ok = delete_plan(plan_id)
        if ok:
            await message.reply_text(f"🗑 Plan `{plan_id}` delete ho gaya.")
        else:
            await message.reply_text(f"❌ Plan `{plan_id}` nahi mila.")
        return True

    if lowered.startswith("/edit_plan_price"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[2].isdigit():
            await message.reply_text("Use: /edit_plan_price <plan_id> <new_price>")
            return True
        plan_id = parts[1].strip().lower()
        price = int(parts[2].strip())
        ok = update_plan_price(plan_id, price)
        if ok:
            await message.reply_text(f"✅ Plan `{plan_id}` ka price update ho kar **₹{price}** ho gaya.")
        else:
            await message.reply_text(f"❌ Plan `{plan_id}` nahi mila.")
        return True

    if lowered.startswith("/premium_status"):
        parts = (message.text or "").split(maxsplit=1)
        target = user_id
        if len(parts) > 1 and parts[1].strip().isdigit():
            target = int(parts[1].strip())
        expiry = get_premium_expiry_text(target) or "No expiry"
        status = "Premium ðŸ’Ž" if is_premium_user(target) else "Free ðŸ†“"
        plan_name = get_user_plan_name(target)
        features = get_user_plan_features(target)
        feature_text = "\n".join([f"- {item}" for item in features]) if features else "Admin ne custom plan features set nahi kiye."
        await message.reply_text(
            f"User `{target}`\nStatus: **{status}**\nPlan: **{plan_name}**\nExpiry: `{expiry}`\n\n**Plan Features**\n{feature_text}"
        )
        return True

    if lowered.startswith("/plan_status"):
        parts = (message.text or "").split(maxsplit=1)
        target = user_id
        if len(parts) > 1 and parts[1].strip().isdigit():
            target = int(parts[1].strip())
        expiry = get_premium_expiry_text(target) or "No expiry"
        status = "Premium ðŸ’Ž" if is_premium_user(target) else "Free ðŸ†“"
        plan_name = get_user_plan_name(target)
        features = get_user_plan_features(target)
        feature_text = "\n".join([f"- {item}" for item in features]) if features else "Admin ne custom plan features set nahi kiye."
        await message.reply_text(
            f"ðŸªª Plan Status\n\nUser: `{target}`\nStatus: **{status}**\nPlan: **{plan_name}**\nExpiry: `{expiry}`\n\n**Plan Features**\n{feature_text}"
        )
        return True

    if lowered.startswith("/set_plan_features"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /set_plan_features user_id feature 1 | feature 2 | feature 3")
            return True
        target = int(parts[1])
        record = set_user_plan_features(target, parts[2], updated_by=user_id)
        features = get_user_plan_features(target)
        await message.reply_text(
            f"✅ Plan features updated\nUser: `{target}`\nPlan: **{get_user_plan_name(target)}**\nItems: `{len(features)}`"
        )
        return True

    if lowered.startswith("/clear_plan_features"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text("Use: /clear_plan_features user_id")
            return True
        target = int(parts[1].strip())
        set_user_plan_features(target, "", updated_by=user_id)
        await message.reply_text(f"ðŸ§¹ Plan features cleared for `{target}`")
        return True

    if lowered.startswith("/set_plan"):
        parts = (message.text or "").split(maxsplit=2)
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /set_plan user_id Gold")
            return True
        target = int(parts[1])
        plan_name = parts[2].strip()
        if not plan_name:
            await message.reply_text("Plan name empty nahi ho sakta.")
            return True
        set_user_plan_name(target, plan_name, updated_by=user_id)
        await message.reply_text(
            f"✅ Plan name updated\nUser: `{target}`\nPlan: **{get_user_plan_name(target)}**"
        )
        return True

    if lowered.startswith("/add_premium"):
        parts = (message.text or "").split()
        if len(parts) < 3 or not parts[1].isdigit():
            await message.reply_text("Use: /add_premium user_id 30d")
            return True
        target = int(parts[1])
        duration = parts[2]
        record = add_premium(target, duration, granted_by=user_id)
        await message.reply_text(
            f"✅ Premium added\nUser: `{target}`\nExpiry: `{record.get('premium_expires_at') or 'No expiry'}`"
        )
        return True

    if lowered.startswith("/remove_premium"):
        parts = (message.text or "").split()
        if len(parts) < 2 or not parts[1].isdigit():
            await message.reply_text("Use: /remove_premium user_id")
            return True
        target = int(parts[1])
        remove_premium(target)
        await message.reply_text(f"✅ Premium removed for `{target}`")
        return True

    if lowered.startswith("/ban"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text("Use: /ban user_id")
            return True
        target = int(parts[1].strip())
        if target == OWNER_ID:
            await message.reply_text("Owner ko ban nahi kar sakte.")
            return True
        ban_user(target)
        await message.reply_text(f"ðŸš« User `{target}` ko ban kar diya gaya.")
        return True

    if lowered.startswith("/unban"):
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) < 2 or not parts[1].strip().isdigit():
            await message.reply_text("Use: /unban user_id")
            return True
        target = int(parts[1].strip())
        unban_user(target)
        await message.reply_text(f"✅ User `{target}` ko unban kar diya gaya.")
        return True

    if lowered.startswith("/broadcast"):
        users = get_recent_users(100000)
        sent = 0
        failed = 0
        status = await message.reply_text("ðŸ“¢ Broadcast start ho raha hai...")

        broadcast_text = ""
        parts = (message.text or "").split(maxsplit=1)
        if len(parts) > 1:
            broadcast_text = parts[1].strip()

        reply_msg = message.reply_to_message

        for u in users:
            await asyncio.sleep(0)
            uid = u.get("id")
            if not uid or is_banned(uid):
                continue

            try:
                await send_broadcast_to_user(client, uid, reply_msg, broadcast_text)
                sent += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await send_broadcast_to_user(client, uid, reply_msg, broadcast_text)
                    sent += 1
                except Exception:
                    failed += 1
            except Exception:
                failed += 1

        await status.edit_text(f"ðŸ“¢ **Broadcast Complete**\n\n✅ Sent: {sent}\n❌ Failed: {failed}")
        return True

    if lowered.startswith("/index_id"):
        set_index_mode(user_id, True)
        await message.reply_text(index_started_text(user_id))
        return True

    if lowered.startswith("/stop_index"):
        set_index_mode(user_id, False)
        await message.reply_text(index_stopped_text(user_id))
        return True

    if lowered.startswith("/index_stats"):
        await message.reply_text(index_stats_text(user_id))
        return True

    return False
