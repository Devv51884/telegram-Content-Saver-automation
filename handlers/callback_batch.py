from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *


async def handle_batch_task_callbacks(client, callback_query, user_id: int, data: str) -> bool:
    if data.startswith("batch_refresh:"):
        await _refresh_batch_board_message(client, user_id)
        await callback_query.answer("Refreshed")
        return True

    if data.startswith("batch_close:"):
        await _close_batch_board(client, user_id)
        await callback_query.answer("Closed")
        return True

    if data.startswith("batch_cancel_current:"):
        batch_key = data.split(":", 1)[1]
        cancelled_ids = _cancel_batch_tasks(user_id, batch_key, only_current=True, return_task_ids=True)
        if cancelled_ids:
            for task_id in cancelled_ids:
                await update_task_status_message(client, task_id, done=True)
            await _refresh_batch_board_message(client, user_id)
            await callback_query.answer(f"Cancelled {len(cancelled_ids)} task")
        else:
            await callback_query.answer("No running task", show_alert=True)
        return True

    if data.startswith("batch_cancel_all:"):
        batch_key = data.split(":", 1)[1]
        cancelled_ids = _cancel_batch_tasks(user_id, batch_key, only_current=False, return_task_ids=True)
        if cancelled_ids:
            for task_id in cancelled_ids:
                await update_task_status_message(client, task_id, done=True)
            await _refresh_batch_board_message(client, user_id)
            await callback_query.answer(f"Cancelled {len(cancelled_ids)} task(s)")
        else:
            await callback_query.answer("No active batch task", show_alert=True)
        return True

    if data == "clear_finished_tasks":
        removed = 0
        for task in get_user_tasks(user_id, limit=1000):
            if task.get("status") in {"completed", "failed", "cancelled"}:
                delete_task(task.get("id"))
                removed += 1
        await callback_query.answer(f"Cleared: {removed}")
        return True

    if data.startswith("task_debug:"):
        task_id = data.split(":", 1)[1]
        task = get_task(task_id) or {}
        debug_text = (
            "Task Debug\n\n"
            f"ID: `{task.get('id', task_id)}`\n"
            f"Status: `{task.get('status', 'unknown')}`\n"
            f"Source: `{task.get('source', '')}`\n"
            f"Destination: `{task.get('destination_display') or task.get('destination') or 'Not Set'}`\n"
            f"Topic: `{task.get('topic_id') or 'None'}`\n"
            f"Mode: `{task.get('upload_mode') or task.get('mode') or 'unknown'}`\n"
            f"Retries: `{task.get('retry_count', task.get('retries', 0))}`\n"
            f"Error: `{task.get('error', '') or 'None'}`"
        )
        try:
            await callback_query.message.reply_text(debug_text, disable_web_page_preview=True)
        except Exception:
            pass
        await callback_query.answer("Debug shown")
        return True

    if data.startswith("task_refresh:"):
        task_id = data.split(":", 1)[1]
        task = get_task(task_id) or {}
        await update_task_status_message(client, task_id, done=task.get("status") in {"completed", "failed", "cancelled"})
        await callback_query.answer("Refreshed")
        return True

    if data.startswith("task_cancel:"):
        task_id = data.split(":", 1)[1]
        task = get_task(task_id)
        if task and _cancel_task_record(task_id):
            await update_task_status_message(client, task_id, done=True)
            if str(task.get("mode") or "").strip().lower() == "batch" and str(task.get("batch_key") or "").strip():
                await _refresh_batch_board_message(client, user_id)
        await callback_query.answer("Cancelled")
        return True

    return False
