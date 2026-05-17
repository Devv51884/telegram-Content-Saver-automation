from __future__ import annotations

from runtime_context import *
from services.clone_delivery_service import *
from services.source_transfer_service import *
from services.queue_task_service import *
from services.batch_transfer_service import *


async def clone_known_message_to_target(
    client,
    from_chat_id,
    message_id,
    target,
    settings: dict | None = None,
    *,
    strict: bool = False,
):
    return await clone_known_message_to_target_impl(
        client,
        from_chat_id,
        message_id,
        target,
        settings,
        strict=strict,
    )


def derive_batch_name(raw_text: str, links: list[str] | None = None) -> str:
    return derive_batch_name_impl(raw_text, links)


def build_index_entry(user_id: int, source_msg, link_text: str, info):
    return build_index_entry_impl(user_id, source_msg, link_text, info)


async def process_source_message_transfer(client, user_id: int, message, source_msg, task_id: str, settings: dict, destination, source_label: str, info: dict | None = None, user_client=None, fetch_mode: str = "bot", disconnect_user_client: bool = False):
    return await process_source_message_transfer_impl(
        client,
        user_id,
        message,
        source_msg,
        task_id,
        settings,
        destination,
        source_label,
        info=info,
        user_client=user_client,
        fetch_mode=fetch_mode,
        disconnect_user_client=disconnect_user_client,
    )


async def _perform_transfer(client, user_id: int, message, link_text: str, task_id: str, settings: dict, destination):
    return await _perform_transfer_impl(client, user_id, message, link_text, task_id, settings, destination)


async def process_link_task(client, user_id: int, message, link_text: str, batch_mode: bool = False, batch_key: str = "", batch_index: int = 0, batch_total: int = 0):
    return await process_link_task_impl(
        client,
        user_id,
        message,
        link_text,
        batch_mode=batch_mode,
        batch_key=batch_key,
        batch_index=batch_index,
        batch_total=batch_total,
    )


async def enqueue_direct_message_task(client, user_id: int, message):
    return await enqueue_direct_message_task_impl(client, user_id, message)


async def process_batch_links(client, user_id: int, message, raw_text: str, links: list[str] | None = None):
    return await process_batch_links_impl(client, user_id, message, raw_text, links=links)
