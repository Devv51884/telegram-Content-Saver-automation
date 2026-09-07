from __future__ import annotations

import os
from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from features.plan_manager import (
    get_all_plans,
    get_plan_by_id,
    get_plan_durations,
    get_plan_duration_info,
    save_plan,
    delete_plan,
    toggle_plan_status,
    reset_default_plans,
    get_payment_config,
    save_payment_config,
    remove_custom_qr,
    get_all_duration_options,
    add_duration_option,
    update_duration_option,
    delete_duration_option,
)
from features.payment_manager import get_pending_orders, get_order
from features.paytm_service import check_paytm_order_status
from keyboards import (
    admin_plan_durations_markup,
    admin_order_detail_markup,
    admin_payment_approval_markup,
    admin_payment_gateway_markup,
    admin_plans_list_markup,
    admin_plan_action_markup,
    admin_pending_orders_markup,
    admin_durations_crud_markup,
    admin_broadcast_confirm_markup,
)

from texts import (
    admin_plan_durations_text,
    admin_plan_detail_text,
    admin_manage_plans_text,
    admin_payment_gateway_text,
)
from storage import set_user_state


async def handle_admin_callbacks(client, callback_query, user_id: int, data: str) -> bool:
    if not is_admin(user_id):
        if any(data.startswith(prefix) for prefix in ("admin_", "show_admin_", "adm_")):
            await callback_query.answer("👑 Sirf Admin hi access kar sakta hai.", show_alert=True)
            return True
        return False

    # 1. Admin Dashboard Home
    if data == "show_admin_panel":
        try:
            await callback_query.message.edit_text(
                admin_panel_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            try:
                await callback_query.message.reply_text(
                    admin_panel_text(),
                    reply_markup=admin_panel_buttons(),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        await callback_query.answer("Admin Dashboard Refreshed")
        return True

    # 2. Live Stats
    if data == "admin_stats":
        try:
            await callback_query.message.edit_text(
                admin_stats_text(get_detailed_stats()),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer("Stats refreshed")
        return True

    # 3. All Users
    if data == "show_admin_users":
        users = get_all_users_page(limit=50, offset=0)
        text = all_users_text(users, title="All Users")
        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer("All users shown")
        return True

    # 4. Recent Users
    if data == "admin_recent_users":
        try:
            await callback_query.message.edit_text(
                all_users_text(get_recent_users(20), title="Recent Users"),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer("Recent users shown")
        return True

    # 5. Plan Management Catalog
    if data == "admin_manage_plans":
        plans = get_all_plans()
        try:
            await callback_query.message.edit_text(
                admin_manage_plans_text(plans),
                reply_markup=admin_plans_list_markup(plans),
                disable_web_page_preview=True,
            )
        except Exception:
            try:
                await callback_query.message.reply_text(
                    admin_manage_plans_text(plans),
                    reply_markup=admin_plans_list_markup(plans),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        await callback_query.answer()
        return True

    # 6. Plan Details View
    if data.startswith("adm_plan_detail:"):
        plan_id = data.split(":", 1)[1].strip()
        plan = get_plan_by_id(plan_id)
        if not plan:
            await callback_query.answer("Plan nahi mila.", show_alert=True)
            return True
        try:
            await callback_query.message.edit_text(
                admin_plan_detail_text(plan),
                reply_markup=admin_plan_action_markup(plan_id, plan.get("is_active", True)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 7. Toggle Plan Active/Disabled
    if data.startswith("adm_toggle_plan:"):
        plan_id = data.split(":", 1)[1].strip()
        new_status = toggle_plan_status(plan_id)
        if new_status is None:
            await callback_query.answer("Plan nahi mila.", show_alert=True)
            return True
        status_word = "🟢 Active" if new_status else "🔴 Disabled"
        await callback_query.answer(f"Plan '{plan_id}' ab {status_word} hai!", show_alert=True)
        plan = get_plan_by_id(plan_id)
        try:
            await callback_query.message.edit_text(
                admin_plan_detail_text(plan),
                reply_markup=admin_plan_action_markup(plan_id, new_status),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return True

    # 8. Delete Plan
    if data.startswith("adm_delete_plan:"):
        plan_id = data.split(":", 1)[1].strip()
        ok = delete_plan(plan_id)
        if ok:
            await callback_query.answer(f"🗑 Plan '{plan_id}' delete kar diya gaya.", show_alert=True)
        else:
            await callback_query.answer("Plan delete nahi ho saka.", show_alert=True)
        plans = get_all_plans()
        try:
            await callback_query.message.edit_text(
                admin_manage_plans_text(plans),
                reply_markup=admin_plans_list_markup(plans),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return True

    # 9. Reset Default Plans
    if data == "adm_reset_plans":
        plans = reset_default_plans()
        await callback_query.answer("✅ Standard default plans restore kar diye gaye!", show_alert=True)
        try:
            await callback_query.message.edit_text(
                admin_manage_plans_text(plans),
                reply_markup=admin_plans_list_markup(plans),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return True

    # 10. Start Add Plan Interactive Flow
    if data == "adm_add_plan_start":
        set_user_state(user_id, "ADM_ADD_PLAN")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                "➕ **Create New Plan Tier**\n\n"
                "Neeche diye format me plan ki details chat me bhejein:\n\n"
                "**Format:**\n"
                "`id | Name | Price | DurationDays | BatchLimit | TaskLimit | StorageModes | Feature 1, Feature 2...`\n\n"
                "**Example:**\n"
                "`vip_pro | VIP Pro 🚀 | 299 | 30 | 300 | 6 | telegram,gdrive,personal_bot | 300 Links Batch, 6 Concurrent Tasks, GDrive Upload`\n\n"
                "*(Kisi bhi waqt cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 11. Start Edit Price Interactive Flow
    if data.startswith("adm_edit_price_start:"):
        plan_id = data.split(":", 1)[1].strip()
        set_user_state(user_id, f"ADM_EDIT_PLAN_PRICE:{plan_id}")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                f"✏️ **Edit Price for Plan: `{plan_id}`**\n\n"
                f"Naya price (in ₹ Rupees) yahan chat me bhejein (sirf number):\n"
                f"*Example:* `149`\n\n"
                f"*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 12. Start Edit Limits Interactive Flow
    if data.startswith("adm_edit_limits_start:"):
        plan_id = data.split(":", 1)[1].strip()
        set_user_state(user_id, f"ADM_EDIT_PLAN_LIMITS:{plan_id}")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                f"⚙️ **Edit Limits for Plan: `{plan_id}`**\n\n"
                f"Format: `BatchLimit | TaskLimit | DurationDays`\n"
                f"*Example:* `250 | 5 | 30`\n\n"
                f"*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 12b. Plan Duration Pricing Dashboard
    if data.startswith("adm_plan_durations:"):
        plan_id = data.split(":", 1)[1].strip()
        plan = get_plan_by_id(plan_id)
        if not plan:
            await callback_query.answer("Plan nahi mila.", show_alert=True)
            return True
        durations = get_plan_durations(plan)
        try:
            await callback_query.message.edit_text(
                admin_plan_durations_text(plan, durations),
                reply_markup=admin_plan_durations_markup(plan_id, durations),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 12c. Edit Specific Duration Price
    if data.startswith("adm_edit_dur_price:"):
        parts = data.split(":")
        plan_id = parts[1].strip()
        dur_key = parts[2].strip()
        plan = get_plan_by_id(plan_id)
        if not plan:
            await callback_query.answer("Plan nahi mila.", show_alert=True)
            return True
        dur_info = get_plan_duration_info(plan, dur_key)
        set_user_state(user_id, f"ADM_EDIT_DUR_PRICE:{plan_id}:{dur_key}")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                f"✏️ **Edit Price for `{plan.get('name')}` — {dur_info['label']} ({dur_info['days']} Days)**\n\n"
                f"Current Price: `₹{dur_info['price']}`\n\n"
                f"Naya price (in ₹ Rupees) chat me bhejein (sirf number):\n"
                f"*Example:* `49`\n\n"
                f"*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 12d. Manage Durations (CRUD Dashboard)
    if data == "adm_manage_durations":
        durations = get_all_duration_options()
        text = (
            "⏱️ **Plan Duration Settings (CRUD)**\n\n"
            "Aap yahan se bot ke sabhi plan validity durations ko manage kar sakte hain:\n\n"
        )
        for d in durations:
            text += f"• {d.get('emoji', '⏱️')} **{d['label']}** (`{d['key']}`) — `{d['days']} Din`\n"
        text += "\n👇 *Neeche diye buttons se duration info edit karein, delete karein ya naya duration add karein:*"
        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=admin_durations_crud_markup(durations),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 12e. Add New Duration Start
    if data == "adm_add_dur_start":
        set_user_state(user_id, "ADM_ADD_DUR_START")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                "➕ **Add New Plan Duration**\n\n"
                "Naye duration ki details is format me chat me bhejein:\n"
                "`<key>, <label>, <days>, <emoji>`\n\n"
                "**Example 1:** `60d, 2 Months, 60, 🗓️`\n"
                "**Example 2:** `3d, 3 Days, 3, ⚡`\n"
                "**Example 3:** `90d, 3 Months, 90, 📅`\n\n"
                "*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 12f. Edit Duration Info
    if data.startswith("adm_edit_dur_info:"):
        dur_key = data.split(":", 1)[1].strip()
        set_user_state(user_id, f"ADM_EDIT_DUR_INFO:{dur_key}")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                f"✏️ **Edit Duration `{dur_key}` Info**\n\n"
                f"Naya Label, Days aur Emoji is format me chat me bhejein:\n"
                f"`<label>, <days>, <emoji>`\n\n"
                f"**Example:** `2 Months, 60, 🗓️`\n\n"
                f"*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 12g. Delete Duration
    if data.startswith("adm_del_dur:"):
        dur_key = data.split(":", 1)[1].strip()
        ok, msg = delete_duration_option(dur_key)
        await callback_query.answer(msg, show_alert=True)
        durations = get_all_duration_options()
        text = (
            "⏱️ **Plan Duration Settings (CRUD)**\n\n"
            "Aap yahan se bot ke sabhi plan validity durations ko manage kar sakte hain:\n\n"
        )
        for d in durations:
            text += f"• {d.get('emoji', '⏱️')} **{d['label']}** (`{d['key']}`) — `{d['days']} Din`\n"
        text += "\n👇 *Neeche diye buttons se duration info edit karein, delete karein ya naya duration add karein:*"
        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=admin_durations_crud_markup(durations),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        return True

    # 13. Payment Gateway Dashboard
    if data == "admin_payment_settings":
        try:
            await callback_query.answer()
        except Exception:
            pass
        try:
            text = admin_payment_gateway_text()
            markup = admin_payment_gateway_markup()
            await callback_query.message.edit_text(
                text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
            print(f"[callback_admin] admin_payment_settings rendered successfully for user={user_id}")
        except Exception as exc:
            print(f"[callback_admin] edit_text failed: {exc}, trying reply_text")
            try:
                await callback_query.message.reply_text(
                    text,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
                print(f"[callback_admin] reply_text succeeded for admin_payment_settings")
            except Exception as exc2:
                print(f"[callback_admin] reply_text failed: {exc2}")
                import traceback
                traceback.print_exc()
        return True

    # 14. Start Setup Paytm Credentials
    if data == "adm_set_paytm_start":
        set_user_state(user_id, "ADM_SET_PAYTM")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                "⚡ **Setup Paytm Merchant Credentials**\n\n"
                "Apna **Merchant ID (MID)** aur **Merchant Key** space se alag karke bhejein:\n\n"
                "**Format:**\n"
                "`<PAYTM_MID> <PAYTM_KEY>`\n\n"
                "**Example:**\n"
                "`CodeDe9876543210 ABCD1234EFGH5678`\n\n"
                "*(business.paytm.com ➔ Developer Settings ➔ API Keys se copy karein)*\n"
                "*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 15. Start Setup UPI ID
    if data == "adm_set_upi_start":
        set_user_state(user_id, "ADM_SET_UPI")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                "🏦 **Setup UPI ID for QR Generator**\n\n"
                "Apna **UPI ID** aur **Payee Name** format me bhejein:\n\n"
                "**Format:**\n"
                "`<UPI_ID> | <PAYEE_NAME>`\n\n"
                "**Example:**\n"
                "`yourname@okhdfcbank | Code Devil Premium`\n\n"
                "*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 15b. Upload Custom QR Photo
    if data == "adm_upload_qr_start":
        set_user_state(user_id, "ADM_UPLOAD_CUSTOM_QR")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                "🖼️ **Upload Custom UPI QR Code**\n\n"
                "Apne Paytm, PhonePe ya Google Pay ka QR Code photo (image) yahan chat me send karein.\n\n"
                "*(Yeh QR code users ko /buy me checkout karte waqt dikhaya jayega)*\n"
                "*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 15c. View Current Custom QR Photo
    if data == "adm_view_custom_qr":
        cfg = get_payment_config()
        file_id = cfg.get("custom_qr_file_id")
        file_path = cfg.get("custom_qr_path")
        target_photo = file_id or (file_path if file_path and os.path.exists(file_path) else None)
        if not target_photo:
            await callback_query.answer("Koi custom QR upload nahi hai.", show_alert=True)
            return True
        await callback_query.answer()
        try:
            await client.send_photo(
                chat_id=user_id,
                photo=target_photo,
                caption=f"🖼️ **Current Active Custom QR Code**\n\nUPI ID: `{cfg.get('upi_id')}`\nPayee: `{cfg.get('payee_name')}`\n\nYeh QR code users ko payment ke time dikhaya ja raha hai.",
            )
        except Exception as exc:
            await client.send_message(user_id, f"Error displaying QR: {exc}")
        return True

    # 15d. Remove Custom QR Photo
    if data == "adm_remove_custom_qr":
        remove_custom_qr()
        await callback_query.answer("Custom QR hata diya gaya! Ab Auto Dynamic QR use hoga.", show_alert=True)
        try:
            text = admin_payment_gateway_text()
            markup = admin_payment_gateway_markup()
            await callback_query.message.edit_text(text, reply_markup=markup, disable_web_page_preview=True)
        except Exception:
            pass
        return True

    # 16. Test Paytm Gateway Connection
    if data == "adm_test_paytm":
        cfg = get_payment_config()
        mid = cfg.get("paytm_mid")
        key = cfg.get("paytm_key")
        if not mid or not key:
            await callback_query.answer(
                "❌ Paytm Credentials Missing!\n\nPehle 'Setup Paytm MID & Key' dabayein.",
                show_alert=True,
            )
            return True

        is_paid, status_text, raw_data = check_paytm_order_status("TEST_PING_ORDER_001")
        result_info = raw_data.get("resultInfo", {}) if isinstance(raw_data, dict) else {}
        result_msg = result_info.get("resultMsg", status_text)

        await callback_query.answer(
            f"🟢 Paytm Gateway API Connected!\nMID: {mid}\nGateway: {result_msg}",
            show_alert=True,
        )
        return True

    # 17. Pending Orders List
    if data == "admin_pending_orders":
        orders = get_pending_orders()
        if not orders:
            await callback_query.answer("ℹ️ Koi pending order nahi hai.", show_alert=True)
            try:
                await callback_query.message.edit_text(
                    "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
                    "  ⏳  **PENDING PAYMENT ORDERS**  ⏳\n"
                    "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
                    "Abhi koi pending ya verification-waiting order nahi hai.",
                    reply_markup=admin_panel_buttons(),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
            return True

        lines = [
            "┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓",
            "  ⏳  **PENDING PAYMENT ORDERS**  ⏳",
            "┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛",
            "",
            f"Total Active Pending: **{len(orders)} Orders**",
            "",
        ]
        for o in orders[:8]:
            utr = o.get("utr_number") or "None"
            has_ss = "📸 " if o.get("screenshot_file_id") else ""
            lines.append(f"• {has_ss}`#{o.get('order_id')}` | ₹{o.get('amount')} | Plan: `{o.get('plan_name')}` | UTR: `{utr}`")

        lines.append("")
        lines.append("👉 *Neeche kisi bhi order button par tap karke verify ya approve karein:*")
        try:
            await callback_query.message.edit_text(
                "\n".join(lines),
                reply_markup=admin_pending_orders_markup(orders),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 18. View Order Details
    if data.startswith("adm_view_order:"):
        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if not order:
            await callback_query.answer("Order nahi mila.", show_alert=True)
            return True
        utr_str = f"`{order.get('utr_number')}`" if order.get("utr_number") else "⚠️ *Not submitted yet*"
        has_screenshot = bool(order.get("screenshot_file_id"))
        ss_str = "✅ Uploaded (View below)" if has_screenshot else "❌ Not attached"
        card = (
            f"┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓\n"
            f"  🧾 **ORDER DETAILS #{order_id}**\n"
            f"┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛\n\n"
            f"👤 **User ID:** `{order.get('user_id')}`\n"
            f"💎 **Plan:** `{order.get('plan_name')}`\n"
            f"💰 **Amount:** `₹{order.get('amount')}`\n"
            f"🧾 **UTR:** {utr_str}\n"
            f"📸 **Screenshot:** {ss_str}\n"
            f"🔘 **Status:** `{order.get('status')}`\n\n"
            f"Approve karne par user ka plan turant real-time me activate ho jayega."
        )
        try:
            await callback_query.message.edit_text(
                card,
                reply_markup=admin_order_detail_markup(order_id, has_screenshot=has_screenshot),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 18b. View Payment Screenshot
    if data.startswith("adm_view_screenshot:"):
        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if not order or not order.get("screenshot_file_id"):
            await callback_query.answer("Is order me koi screenshot attach nahi hai.", show_alert=True)
            return True
        await callback_query.answer()
        try:
            caption = (
                f"📸 **Payment Screenshot for Order #{order_id}**\n\n"
                f"👤 User: `{order.get('user_id')}`\n"
                f"📦 Plan: `{order.get('plan_name')}`\n"
                f"💰 Amount: `₹{order.get('amount')}`\n"
                f"🧾 UTR: `{order.get('utr_number') or 'Not provided'}`"
            )
            await client.send_photo(
                chat_id=user_id,
                photo=order["screenshot_file_id"],
                caption=caption,
                reply_markup=admin_payment_approval_markup(order_id, has_screenshot=False),
            )
        except Exception as exc:
            await client.send_message(user_id, f"Error viewing screenshot: {exc}")
        return True

    # 19. Premium Help Text
    if data == "admin_premium_help":
        try:
            await callback_query.message.edit_text(
                admin_premium_help_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 20. Plan Help Text
    if data == "admin_plan_help":
        try:
            await callback_query.message.edit_text(
                admin_plan_help_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 21b. Start Interactive Broadcast
    if data == "adm_start_broadcast":
        set_user_state(user_id, "ADM_AWAITING_BROADCAST_MSG")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                "📢 **Start Interactive Broadcast**\n\n"
                "Aap jo message sabhi registered users ko bhejna chahte hain, woh abhi is chat me send karein.\n\n"
                "• **Supported Media:** Photo, Video, Document/File, Audio, Voice Note, Sticker, Animation, Video Note ya Text!\n"
                "• Formatting (Markdown, HTML, Links, Spoilers) sab preserve rahega.\n\n"
                "*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    # 21c. Cancel Interactive Broadcast
    if data == "adm_cancel_broadcast":
        clear_user_state(user_id)
        await callback_query.answer("Broadcast cancel kar diya gaya.")
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        return True

    # 21d. Confirm Interactive Broadcast
    if data.startswith("adm_confirm_broadcast:"):
        msg_id = int(data.split(":", 1)[1].strip())
        await callback_query.answer("🚀 Broadcasting to all users...", show_alert=False)
        try:
            broadcast_msg = await client.get_messages(chat_id=user_id, message_ids=msg_id)
        except Exception as exc:
            await callback_query.message.reply_text(f"❌ Message load failed: {exc}")
            return True

        if not broadcast_msg:
            await callback_query.message.reply_text("❌ Broadcast message nahi mila.")
            return True

        status = await callback_query.message.reply_text("📢 **Broadcast shuru ho raha hai...**")
        users = get_recent_users(100000)
        sent = 0
        failed = 0
        total_users = len(users)

        for idx, u in enumerate(users, start=1):
            uid = u.get("id")
            if not uid or is_banned(uid):
                continue
            try:
                await send_broadcast_to_user(client, uid, broadcast_msg, "")
                sent += 1
            except FloodWait as e:
                await asyncio.sleep(e.value)
                try:
                    await send_broadcast_to_user(client, uid, broadcast_msg, "")
                    sent += 1
                except Exception:
                    failed += 1
            except Exception:
                failed += 1

            if idx % 25 == 0 or idx == total_users:
                try:
                    await status.edit_text(f"📢 **Broadcasting...**\nProgress: {idx}/{total_users}\n✅ Sent: {sent}\n❌ Failed: {failed}")
                except Exception:
                    pass
            await asyncio.sleep(0.04)

        await status.edit_text(f"📢 **Broadcast Complete!**\n\n✅ Sent: {sent}\n❌ Failed: {failed}\n👥 Total Users: {total_users}")
        try:
            add_broadcast_log({
                "sent": sent,
                "failed": failed,
                "total": total_users,
                "text": getattr(broadcast_msg, "caption", "") or getattr(broadcast_msg, "text", "") or "Media broadcast",
                "created_at": str(int(time.time())),
            })
        except Exception:
            pass
        return True

    # 21. Broadcast Help Text
    if data == "admin_broadcast_help":
        broadcast_text = (
            "📢 **Admin Broadcast Help**\n\n"
            "Aap bot ke sabhi registered users ko ek saath message broadcast kar sakte hain:\n\n"
            "**Command:**\n"
            "`/broadcast Aapka announcement message yahan...`\n\n"
            "Ya kisi message ko reply karke `/broadcast` bhejein."
        )
        try:
            await callback_query.message.edit_text(
                broadcast_text,
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    # 22. Task Debug Help
    if data == "admin_task_debug_help":
        debug_text = (
            "🧪 **Task Debug Tools**\n\n"
            "Admin task queue aur system processes monitor karne ke liye:\n\n"
            "• `/stats` — Live system & user stats\n"
            "• `/storage_status` — Storage directory usage\n"
            "• `/supabase_status` — Cloud DB connection\n"
            "• `/cancel_all` — Emergency stop all tasks"
        )
        try:
            await callback_query.message.edit_text(
                debug_text,
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    return False
