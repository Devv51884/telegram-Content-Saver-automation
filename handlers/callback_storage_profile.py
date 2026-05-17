from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *

async def handle_storage_profile_callbacks(client, callback_query, user_id: int, data: str, s: dict):
    if await handle_storage_callbacks(client, callback_query, user_id, data, s):
        return True

    if await handle_profile_callbacks(client, callback_query, user_id, data, s):
        return True

    return False
