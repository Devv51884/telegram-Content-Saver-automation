from __future__ import annotations

import os
from runtime_context import is_admin, OWNER_ID, LOG_CHANNEL
from features.plan_manager import (
    get_active_plans,
    get_plan_by_id,
    get_plan_durations,
    get_payment_config,
)
from features.payment_manager import (
    create_order,
    get_order,
    is_order_expired,
    cancel_order,
    mark_order_paid,
)
from services.qr_service import create_order_qr
from services.plan_activation_service import activate_user_plan
from features.paytm_service import check_paytm_order_status
from keyboards import (
    buy_plans_markup,
    plan_durations_markup,
    order_payment_markup,
    admin_payment_approval_markup,
)
from texts import (
    buy_plans_text,
    plan_duration_selection_text,
    order_payment_text,
)
from storage import get_user_state, set_user_state, clear_user_state


async def handle_payment_callbacks(client, callback_query, user_id: int, data: str) -> bool:
    if data == "buy_plans_menu":
        active_plans = get_active_plans()
        try:
            await callback_query.message.edit_text(
                buy_plans_text(),
                reply_markup=buy_plans_markup(active_plans),
                disable_web_page_preview=True,
            )
        except Exception:
            try:
                await callback_query.message.reply_text(
                    buy_plans_text(),
                    reply_markup=buy_plans_markup(active_plans),
                    disable_web_page_preview=True,
                )
            except Exception:
                pass
        await callback_query.answer()
        return True

    if data.startswith("buy_plan:") or data.startswith("buy_select:"):
        plan_id = data.split(":", 1)[1].strip()
        plan = get_plan_by_id(plan_id)
        if not plan:
            await callback_query.answer("❌ Plan nahi mila.", show_alert=True)
            return True

        durations = get_plan_durations(plan)
        text = plan_duration_selection_text(plan, durations)
        markup = plan_durations_markup(plan_id, durations)

        try:
            await callback_query.message.edit_text(
                text,
                reply_markup=markup,
                disable_web_page_preview=True,
            )
        except Exception:
            try:
                await callback_query.message.reply_text(
                    text,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
            except Exception:
                pass

        await callback_query.answer()
        return True

    if data.startswith("buy_dur:"):
        parts = data.split(":")
        if len(parts) < 3:
            await callback_query.answer("Invalid selection.", show_alert=True)
            return True
        plan_id = parts[1].strip()
        dur_key = parts[2].strip()

        plan = get_plan_by_id(plan_id)
        if not plan:
            await callback_query.answer("❌ Plan nahi mila.", show_alert=True)
            return True

        order = create_order(user_id, plan_id, duration_key=dur_key)
        qr_file_path, upi_uri, _ = create_order_qr(order)
        cfg = get_payment_config()
        upi_id = cfg.get("upi_id") or "nope728@ptyes"

        caption = order_payment_text(order, upi_id)
        markup = order_payment_markup(order["order_id"])

        try:
            await callback_query.message.delete()
        except Exception:
            pass

        set_user_state(user_id, f"AWAITING_PAYMENT_UTR:{order['order_id']}")

        try:
            if qr_file_path and os.path.exists(qr_file_path):
                await client.send_photo(
                    chat_id=user_id,
                    photo=qr_file_path,
                    caption=caption,
                    reply_markup=markup,
                )
            else:
                await client.send_message(
                    chat_id=user_id,
                    text=caption,
                    reply_markup=markup,
                    disable_web_page_preview=True,
                )
        except Exception as exc:
            await client.send_message(user_id, f"Error generating payment: {exc}")

        await callback_query.answer()
        return True


    if data.startswith("pay_check:"):
        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if not order:
            await callback_query.answer("❌ Order nahi mila.", show_alert=True)
            return True

        if order.get("status") == "paid":
            await callback_query.answer("✅ Plan already activated hai!", show_alert=True)
            return True

        if is_order_expired(order):
            await callback_query.answer("⏱️ Yeh order 5 minute me expire ho chuka hai. Naya plan select karein.", show_alert=True)
            return True

        is_paid, status_text, _ = check_paytm_order_status(order_id)
        if is_paid:
            ok, msg = await activate_user_plan(client, order_id, verified_via="paytm_auto")
            if ok:
                await callback_query.answer("🎉 Payment Received! Aapka plan activate ho gaya hai!", show_alert=True)
                try:
                    await callback_query.message.edit_caption(
                        caption=f"✅ **Payment Verified!**\n\nPlan: `{order.get('plan_name')}`\nAapka premium plan turant activate kar diya gaya hai. Check karne ke liye /plan use karein.",
                        reply_markup=None,
                    )
                except Exception:
                    pass
                return True

        await callback_query.answer(
            "⏳ Bank se payment abhi confirm nahi hui hai.\n\nAgar aapne pay kar diya hai toh 10-15s baad dobara check karein ya 'Submit 12-Digit UTR' par click karein.",
            show_alert=True,
        )
        return True

    if data.startswith("pay_screenshot:"):
        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if not order:
            await callback_query.answer("❌ Order nahi mila.", show_alert=True)
            return True

        if is_order_expired(order):
            await callback_query.answer("⏱️ Yeh order expire ho chuka hai.", show_alert=True)
            return True

        set_user_state(user_id, f"AWAITING_PAYMENT_UTR:{order_id}")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                f"📸 **Order #{order_id} (₹{order.get('amount')}) — Screenshot Upload**\n\n"
                f"Kripya payment receipt ya confirmation ka photo yahan send karein!\n\n"
                f"💡 *Aap photo ke caption me 12-digit UTR bhi likh sakte hain.*\n"
                f"*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    if data.startswith("pay_utr:"):
        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if not order:
            await callback_query.answer("❌ Order nahi mila.", show_alert=True)
            return True

        if is_order_expired(order):
            await callback_query.answer("⏱️ Yeh order expire ho chuka hai.", show_alert=True)
            return True

        set_user_state(user_id, f"AWAITING_PAYMENT_UTR:{order_id}")
        await callback_query.answer()
        await client.send_message(
            chat_id=user_id,
            text=(
                f"🧾 **Order #{order_id} (₹{order.get('amount')})**\n\n"
                f"Kripya apna **12-digit UPI Reference / UTR Number** chat me type karke send karein, YA payment ki receipt/screenshot photo yahan send karein!\n\n"
                f"💡 *Aap photo ke caption me bhi 12-digit UTR number likh sakte hain.*\n"
                f"*(Cancel karne ke liye /cancel bhejein)*"
            ),
        )
        return True

    if data.startswith("pay_cancel:"):
        order_id = data.split(":", 1)[1].strip()
        cancel_order(order_id)
        clear_user_state(user_id)
        await callback_query.answer("Order cancel kar diya gaya.")
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        return True

    if data.startswith("adm_approve_pay:"):
        if not is_admin(user_id):
            await callback_query.answer("Only admin can approve.", show_alert=True)
            return True

        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if not order:
            await callback_query.answer("Order nahi mila.", show_alert=True)
            return True

        ok, msg = await activate_user_plan(client, order_id, verified_via=f"admin_{user_id}", utr=order.get("utr_number", ""))
        if ok:
            await callback_query.answer("✅ Approved! Plan activated.", show_alert=True)
            appr_text = (
                f"✅ **Order #{order_id} Approved!**\n\n"
                f"User: `{order.get('user_id')}`\n"
                f"Plan: `{order.get('plan_name')}`\n"
                f"Amount: `₹{order.get('amount')}`\n"
                f"UTR: `{order.get('utr_number') or 'None'}`\n"
                f"Approved by: `{user_id}`"
            )
            try:
                await callback_query.message.edit_caption(
                    caption=appr_text,
                    reply_markup=None,
                )
            except Exception:
                try:
                    await callback_query.message.edit_text(
                        appr_text,
                        reply_markup=None,
                    )
                except Exception:
                    pass
        else:
            await callback_query.answer(f"Error: {msg}", show_alert=True)
        return True

    if data.startswith("adm_reject_pay:"):
        if not is_admin(user_id):
            await callback_query.answer("Only admin can reject.", show_alert=True)
            return True

        order_id = data.split(":", 1)[1].strip()
        order = get_order(order_id)
        if order:
            target_user = order.get("user_id")
            try:
                await client.send_message(
                    target_user,
                    f"❌ **Payment Rejected**\n\nAapka order #{order_id} (₹{order.get('amount')}) admin dwara reject kar diya gaya hai. Agar aapne payment kar di hai toh support se contact karein.",
                )
            except Exception:
                pass
            rej_text = f"❌ **Order #{order_id} Rejected.**\nUser: `{target_user}`\nRejected by: `{user_id}`"
            try:
                await callback_query.message.edit_caption(
                    caption=rej_text,
                    reply_markup=None,
                )
            except Exception:
                try:
                    await callback_query.message.edit_text(
                        rej_text,
                        reply_markup=None,
                    )
                except Exception:
                    pass
        await callback_query.answer("Order rejected.")
        return True

    return False
