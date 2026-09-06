from __future__ import annotations

from runtime_context import *
from services.storage_service import *
from services.task_service import *
from services.task_service import (
    _get_batch_board,
    _save_batch_board,
    _open_batch_board,
    _refresh_batch_board_message,
)
from services.worker_service import *
from services.worker_service import (
    _run_task_attempts,
)
from services.link_service import *
from services.queue_task_service import *

__all__ = [
    "derive_batch_name_impl",
    "derive_batch_name",
    "process_batch_links_impl",
    "process_batch_links",
]


def derive_batch_name_impl(raw_text: str, links: list[str] | None = None) -> str:
    raw_text = str(raw_text or "").strip()
    links = links or []
    for line in raw_text.splitlines():
        value = str(line or "").strip()
        if not value:
            continue
        if not value.startswith("http://") and not value.startswith("https://"):
            return value[:80]
    if links:
        first = str(links[0]).strip()
        if "/c/" in first:
            return "Private Channel Batch"
        return "Telegram Batch Job"
    return "Batch Job"


def derive_batch_name(raw_text: str, links: list[str] | None = None) -> str:
    return derive_batch_name_impl(raw_text, links)


async def process_batch_links_impl(client, user_id: int, message, raw_text: str, links: list[str] | None = None):
    links = list(links or parse_batch_links(raw_text))
    if not links:
        await message.reply_text("❌ Batch me koi valid Telegram links nahi mile.")
        return

    save_batch_input(user_id, raw_text)
    batch_settings = get_user_settings(user_id)
    try:
        ensure_storage_runtime_ready(batch_settings, ensure_shared_user_site_packages)
    except Exception as exc:
        await message.reply_text(f"❌ Batch start nahi hua: {exc}")
        return

    user_batch_limit = get_user_batch_limit(user_id)
    if len(links) > user_batch_limit:
        links = links[:user_batch_limit]

    board = await _open_batch_board(client, message, user_id, len(links), note="", batch_name=derive_batch_name_impl(raw_text, links))
    batch_key = board.get("batch_key", "")

    success = 0
    failed = 0

    await asyncio.sleep(0)

    for idx, link in enumerate(links, start=1):
        board = _get_batch_board(user_id)
        if not board or board.get("batch_key") != batch_key:
            break
        if bool(board.get("cancel_all_requested")):
            board["status"] = "Cancelled"
            board["current_stage"] = "Cancelled"
            board["current_task_id"] = ""
            board["note"] = "Batch cancelled by user"
            _save_batch_board(user_id, board)
            await _refresh_batch_board_message(client, user_id, force_done=True)
            break

        task_id = await process_link_task_impl(
            client,
            user_id,
            message,
            link,
            batch_mode=True,
            batch_key=batch_key,
            batch_index=idx,
            batch_total=len(links),
        )

        if not task_id:
            failed += 1
            await _refresh_batch_board_message(client, user_id, force_done=(idx == len(links) and success == 0))
            continue

        current_settings = get_user_settings(user_id)
        item = {
            "task_id": task_id,
            "user_id": user_id,
            "message": message,
            "link_text": link,
            "settings": current_settings,
            "destination": get_configured_storage_destination(current_settings),
            "batch_mode": True,
        }

        touch_task(task_id, {
            "status": "processing",
            "current_stage": "processing",
            "progress_text": "",
            "queue_position": 0,
            "worker_id": 0,
            "is_visible": False,
        })
        await asyncio.sleep(0)
        await update_task_status_message(client, task_id, done=False)

        ok = await _run_task_attempts(client, item)
        if ok:
            success += 1
        else:
            failed += 1

        board = _get_batch_board(user_id)
        if board:
            cancel_all_requested = bool(board.get("cancel_all_requested"))
            board["current_index"] = idx
            board["current_task_id"] = ""
            if cancel_all_requested:
                board["status"] = "Cancelled"
                board["current_stage"] = "Cancelled"
                board["note"] = "Batch cancelled by user"
            _save_batch_board(user_id, board)
            await _refresh_batch_board_message(client, user_id, force_done=(idx == len(links) or cancel_all_requested))
            if cancel_all_requested:
                break

        if BATCH_DELAY > 0 and idx < len(links):
            board = _get_batch_board(user_id)
            if board and bool(board.get("cancel_all_requested")):
                break
            await asyncio.sleep(max(BATCH_DELAY, 0.2))

    board = _get_batch_board(user_id)
    if board:
        if bool(board.get("cancel_all_requested")):
            board["status"] = "Cancelled"
            board["current_stage"] = "Cancelled"
            board["note"] = "Batch cancelled by user"
        else:
            board["status"] = "Completed"
        board["current_task_id"] = ""
        _save_batch_board(user_id, board)
        await _refresh_batch_board_message(client, user_id, force_done=True)


async def process_batch_links(client, user_id: int, message, raw_text: str, links: list[str] | None = None):
    return await process_batch_links_impl(client, user_id, message, raw_text, links=links)
