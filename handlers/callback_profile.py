from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *

async def handle_profile_callbacks(client, callback_query, user_id: int, data: str, s: dict):
    if data == "show_user_limits":
        await callback_query.answer(
            f"Tasks: {get_user_task_limit(user_id)} | Batch: {get_user_batch_limit(user_id)}",
            show_alert=True,
        )
        return True
    if data in {"admin_broadcast_help", "admin_recent_users", "admin_logs_summary", "admin_task_debug_help", "admin_destination_help", "show_batch_info"}:
        if data.startswith("admin_") and not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
        help_map = {
            "admin_broadcast_help": "ðŸ“¢ Broadcast help\n\nUse: /broadcast your message\nYa kisi media/text par reply karke /broadcast bhejo.",
            "admin_recent_users": "ðŸ‘¥ Recent users\n\n/users command use karo ya admin panel ka users section kholo.",
            "admin_logs_summary": "ðŸ§¾ Logs summary\n\nLog channel aur runtime console logs se detailed status check karo.",
            "admin_task_debug_help": "ðŸ§ª Task debug help\n\nTask card ke refresh/cancel buttons use karo. Debug task button raw state dikhata hai.",
            "admin_destination_help": "ðŸ“Œ Destination help\n\nDestination me chat id ya @channelusername set karo. Topic ID optional hai.",
            "show_batch_info": "ðŸ“¦ Batch info\n\nSingle links, multiple links, aur range links dono supported hain.",
        }
        try:
            await callback_query.message.reply_text(help_map[data], disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return True
    if data == "show_premium_info":
        try:
            await callback_query.message.edit_text(
                premium_info_text(user_id),
                reply_markup=premium_info_buttons(is_admin(user_id)),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True
    if data == "show_settings_home":
        try:
            await callback_query.message.edit_text(
                settings_home_text(user_id),
                reply_markup=build_settings_home_markup(user_id),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True
    if data == "show_my_tasks":
        tasks = get_user_tasks(user_id, limit=10)
        try:
            await callback_query.message.edit_text(my_tasks_text(tasks), reply_markup=my_tasks_buttons(include_cleanup=True), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return True
    if data == "show_login_info":
        try:
            await callback_query.message.edit_text(login_intro_text(), reply_markup=login_buttons(has_user_session(user_id)), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return True
    if data == "show_login_status":
        try:
            await callback_query.message.edit_text(login_status_text(user_id), reply_markup=login_buttons(has_user_session(user_id)), disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer()
        return True
    if data == "start_login_flow":
        set_user_state(user_id, "login_phone")
        await callback_query.message.reply_text("ðŸ“± Ab apna phone number international format me bhejo.\nExample: +91xxxxxxxxxx\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    if data == "do_logout":
        if has_user_session(user_id):
            delete_user_session(user_id)
            clear_login_temp(user_id)
            await cleanup_login_client(user_id)
            await cleanup_authorized_user_client(user_id)
            try:
                await callback_query.message.edit_text(logout_success_text(), reply_markup=login_buttons(False), disable_web_page_preview=True)
            except Exception:
                pass
        else:
            try:
                await callback_query.message.edit_text(logout_missing_text(), reply_markup=login_buttons(False), disable_web_page_preview=True)
            except Exception:
                pass
        await callback_query.answer()
        return True

    return False
