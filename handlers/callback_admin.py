from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *


async def handle_admin_callbacks(client, callback_query, user_id: int, data: str) -> bool:
    if data == "admin_stats":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
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

    if data == "show_admin_users":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
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

    if data == "admin_recent_users":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
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

    if data == "show_admin_panel":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
        try:
            await callback_query.message.edit_text(
                admin_panel_text(),
                reply_markup=admin_panel_buttons(),
                disable_web_page_preview=True,
            )
        except Exception:
            pass
        await callback_query.answer()
        return True

    if data == "admin_premium_help":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
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

    if data == "admin_plan_help":
        if not is_admin(user_id):
            await callback_query.answer("Only admin", show_alert=True)
            return True
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

    return False
