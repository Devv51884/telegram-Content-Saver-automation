from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from services.task_service import (
    _get_batch_board,
    _cancel_batch_tasks,
    _cancel_active_tasks_for_user,
    _refresh_batch_board_message,
    update_task_status_message,
)
from features.plan_manager import get_active_plans
from keyboards import buy_plans_markup
from texts import buy_plans_text


async def handle_message_commands(client, message, user_id: int, text_raw: str, lowered: str, state: str):
    if await handle_admin_commands(client, message, lowered):
        return True

    if lowered.startswith("/cancelall") or lowered.startswith("/cancel_all"):
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        cancelled_ids = []
        board = _get_batch_board(user_id)
        if board and str(board.get("batch_key") or "").strip():
            cancelled_ids.extend(_cancel_batch_tasks(user_id, board.get("batch_key"), only_current=False, return_task_ids=True))
        cancelled_ids.extend(_cancel_active_tasks_for_user(user_id, limit=2000, return_task_ids=True))
        cancelled_ids = list(dict.fromkeys([task_id for task_id in cancelled_ids if str(task_id).strip()]))

        for task_id in cancelled_ids:
            await update_task_status_message(client, task_id, done=True)
        if _get_batch_board(user_id):
            try:
                await _refresh_batch_board_message(client, user_id)
            except Exception:
                pass
        if cancelled_ids:
            await message.reply_text(f"{len(cancelled_ids)} active task(s) cancel kar diye gaye.")
        else:
            await message.reply_text("Koi active task nahi mila.")
        return True

    if lowered.startswith("/cancel"):
        had_input_state = bool(state)
        clear_login_temp(user_id)
        clear_user_state(user_id)
        await cleanup_login_client(user_id)
        cancelled_ids = []
        board = _get_batch_board(user_id)
        if board and str(board.get("current_task_id") or "").strip():
            cancelled_ids.extend(_cancel_batch_tasks(user_id, board.get("batch_key"), only_current=True, return_task_ids=True))
        cancelled_ids.extend(_cancel_active_tasks_for_user(user_id, limit=1, return_task_ids=True))
        cancelled_ids = list(dict.fromkeys([task_id for task_id in cancelled_ids if str(task_id).strip()]))

        for task_id in cancelled_ids:
            await update_task_status_message(client, task_id, done=True)
        if cancelled_ids and _get_batch_board(user_id):
            try:
                await _refresh_batch_board_message(client, user_id)
            except Exception:
                pass
        if had_input_state and cancelled_ids:
            await message.reply_text("Current input mode aur current running task cancel kar diya gaya.")
        elif had_input_state:
            await message.reply_text("Current input mode cancel kar diya gaya.")
        elif cancelled_ids:
            await message.reply_text("Current running task cancel kar diya gaya.")
        else:
            await message.reply_text("Koi active input mode ya running task nahi mila.")
        return True

    if lowered.startswith("/ping"):
        await message.reply_text("Bot online hai aur sahi se reply kar raha hai.")
        return True

    if lowered.startswith("/start"):
        reset_user_index_counter(user_id)
        await message.reply_text(
            start_text() + "\n\nTumhara current user index reset ho gaya hai. Ab next item `01` se start hoga.",
            reply_markup=build_start_markup(user_id),
            disable_web_page_preview=True,
        )
        return True

    if lowered.startswith("/help"):
        await message.reply_text(help_text(is_admin(user_id)))
        return True

    if lowered.startswith("/buy") or lowered == "/plans":
        active_plans = get_active_plans()
        await message.reply_text(
            buy_plans_text(),
            reply_markup=buy_plans_markup(active_plans),
            disable_web_page_preview=True,
        )
        return True

    if lowered.startswith("/plan"):
        await message.reply_text(plan_text(user_id))
        return True

    if lowered.startswith("/terms"):
        await message.reply_text(terms_text())
        return True

    if lowered.startswith("/settings"):
        await message.reply_text(
            settings_home_text(user_id),
            reply_markup=build_settings_home_markup(user_id),
            disable_web_page_preview=True,
        )
        return True

    if lowered.startswith("/login_status"):
        await message.reply_text(login_status_text(user_id), reply_markup=login_buttons(has_user_session(user_id)))
        return True

    if lowered.startswith("/logout"):
        if has_user_session(user_id):
            delete_user_session(user_id)
            clear_login_temp(user_id)
            await cleanup_login_client(user_id)
            await cleanup_authorized_user_client(user_id)
            await message.reply_text(logout_success_text(), reply_markup=login_buttons(False))
        else:
            await message.reply_text(logout_missing_text(), reply_markup=login_buttons(False))
        return True

    if lowered.startswith("/my_tasks"):
        tasks = get_user_tasks(user_id, limit=10)
        await message.reply_text(
            my_tasks_text(tasks),
            reply_markup=my_tasks_buttons(include_cleanup=True),
            disable_web_page_preview=True,
        )
        return True

    if should_send_unknown_reply(message, text_raw):
        await message.reply_text(unknown_text())

    return False
