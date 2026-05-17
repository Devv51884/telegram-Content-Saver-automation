from __future__ import annotations

from pathlib import Path

from runtime_context import *  # noqa: F403
from runtime_context import app


def _load_split_module(relative_path: str) -> None:
    module_path = Path(__file__).resolve().parent / relative_path
    source = module_path.read_text(encoding="utf-8")
    filtered_lines = []
    for line in source.splitlines():
        stripped = line.strip()
        if stripped == "from __future__ import annotations":
            continue
        if stripped.startswith("from runtime_context import *"):
            continue
        if stripped.startswith("from services.") and stripped.endswith("import *"):
            continue
        filtered_lines.append(line)
    source = "\n".join(filtered_lines) + "\n"
    exec(compile(source, str(module_path), "exec"), globals())


for _relative_path in (
    "services/storage_service.py",
    "services/task_service.py",
    "services/worker_service.py",
    "services/link_service.py",
    "services/delivery_service.py",
    "services/clone_delivery_service.py",
    "services/upload_target_service.py",
    "services/source_transfer_service.py",
    "services/queue_task_service.py",
    "services/batch_transfer_service.py",
    "services/transfer_service.py",
    "services/auth_admin_service.py",
    "handlers/callback_admin.py",
    "handlers/callback_batch.py",
    "handlers/callback_settings.py",
    "handlers/callback_storage.py",
    "handlers/callback_profile.py",
    "handlers/callback_storage_profile.py",
    "handlers/callback_router.py",
    "handlers/message_state_flow.py",
    "handlers/message_commands.py",
    "handlers/message_router.py",
    "handlers/callbacks.py",
    "handlers/messages.py",
):
    _load_split_module(_relative_path)


_HANDLERS_REGISTERED = False


def register_handlers():
    global _HANDLERS_REGISTERED
    if _HANDLERS_REGISTERED:
        return
    register_callback_handlers(app)
    register_message_handlers(app)
    _HANDLERS_REGISTERED = True


register_handlers()
