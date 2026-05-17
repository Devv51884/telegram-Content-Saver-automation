from __future__ import annotations

from runtime_context import *

def derive_gdrive_token_dest(user_id: int, filename: str = "token.pickle") -> str:
    folder = getattr(cfg, "GDRIVE_TOKENS_DIR", TEMP_DIR)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}_{filename}")


def derive_rclone_config_dest(user_id: int, filename: str = "rclone.conf") -> str:
    folder = getattr(cfg, "RCLONE_CONFIGS_DIR", TEMP_DIR)
    os.makedirs(folder, exist_ok=True)
    return os.path.join(folder, f"{user_id}_{filename}")


PERSONAL_BOT_CLIENTS = {}
AUTHORIZED_USER_CLIENTS = {}


def is_client_connection_ready(client_obj) -> bool:
    if not client_obj:
        return False
    connected = getattr(client_obj, "is_connected", None)
    if connected is None:
        return True
    return bool(connected)


def is_cached_authorized_user_client(user_id: int, client_obj) -> bool:
    user_id = int(user_id or 0)
    if not user_id or not client_obj:
        return False
    return AUTHORIZED_USER_CLIENTS.get(user_id) is client_obj


async def get_or_create_personal_bot_client(user_id: int, settings: dict):
    mode = str((settings or {}).get("bot_delivery_mode", "main") or "main").strip().lower()
    token = str((settings or {}).get("personal_bot_token", "") or "").strip()
    if mode != "personal" or not token:
        return None
    cache = PERSONAL_BOT_CLIENTS.get(user_id)
    if cache and cache.get("token") == token:
        return cache.get("client")
    client_obj = Client(
        name=f"personal_bot_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=token,
        in_memory=True,
    )
    await client_obj.start()
    me = await client_obj.get_me()
    update_user_settings(user_id, {"personal_bot_username": getattr(me, "username", "") or ""})
    PERSONAL_BOT_CLIENTS[user_id] = {"token": token, "client": client_obj}
    return client_obj


async def cleanup_personal_bot_client(user_id: int):
    cache = PERSONAL_BOT_CLIENTS.pop(user_id, None)
    if cache and cache.get("client"):
        try:
            await cache["client"].stop()
        except Exception:
            pass


async def cleanup_authorized_user_client(user_id: int):
    client = AUTHORIZED_USER_CLIENTS.pop(int(user_id or 0), None)
    if not client:
        return
    try:
        await client.stop()
    except Exception:
        try:
            await client.disconnect()
        except Exception:
            pass


async def validate_personal_bot_token(user_id: int, token: str):
    temp_client = Client(
        name=f"validate_personal_bot_{user_id}",
        api_id=API_ID,
        api_hash=API_HASH,
        bot_token=token,
        in_memory=True,
    )
    await temp_client.start()
    try:
        me = await temp_client.get_me()
        return me
    finally:
        try:
            await temp_client.stop()
        except Exception:
            pass


def create_temp_text_file(source_msg, settings: dict, index_no: int = 0, storage_mode: str | None = None):
    os.makedirs(TEMP_DIR, exist_ok=True)
    path = os.path.join(TEMP_DIR, f"text_{uuid.uuid4().hex[:8]}.txt")
    value = build_final_text(source_msg.text or source_msg.caption or "", source_msg, settings, index_no=index_no, storage_mode=storage_mode)
    Path(path).write_text(ensure_non_empty_text(value), encoding="utf-8")
    return path


def _build_gdrive_service(token_path: str):
    import pickle
    from googleapiclient.discovery import build
    with open(token_path, "rb") as fh:
        creds = pickle.load(fh)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _upload_file_to_gdrive_sync(token_path: str, file_path: str, folder_id: str, description: str = ""):
    from googleapiclient.http import MediaFileUpload
    service = _build_gdrive_service(token_path)
    metadata = {"name": os.path.basename(file_path)}
    if folder_id:
        metadata["parents"] = [folder_id]
    if str(description or "").strip():
        metadata["description"] = str(description).strip()
    media = MediaFileUpload(file_path, resumable=False)
    return service.files().create(body=metadata, media_body=media, fields="id,name,description,webViewLink").execute()


async def upload_file_to_gdrive(user_id: int, settings: dict, file_path: str, source_msg=None, index_no: int = 0):
    token_path = str(settings.get("gdrive_token_path", "") or "").strip()
    folder_id = str(settings.get("gdrive_folder_id", "") or "").strip()
    if not token_path or not os.path.exists(token_path):
        raise RuntimeError("Google Drive token.pickle missing hai.")
    if not folder_id:
        raise RuntimeError("Google Drive folder ID set nahi hai.")
    description = build_storage_annotation(source_msg, settings, index_no=index_no, storage_mode="gdrive") if source_msg else ""
    result = await asyncio.to_thread(_upload_file_to_gdrive_sync, token_path, file_path, folder_id, description)
    update_user_settings(user_id, {"gdrive_last_file_link": str(result.get("webViewLink", "") or result.get("id", ""))})
    return result


async def validate_gdrive_settings_for_user(settings: dict):
    token_path = str(settings.get("gdrive_token_path", "") or "").strip()
    folder_id = str(settings.get("gdrive_folder_id", "") or "").strip()
    if not token_path or not os.path.exists(token_path):
        raise RuntimeError("token.pickle missing")
    if not folder_id:
        raise RuntimeError("folder id missing")
    def _validate():
        service = _build_gdrive_service(token_path)
        return service.files().get(fileId=folder_id, fields="id,name,mimeType").execute()
    return await asyncio.to_thread(_validate)


async def upload_file_to_rclone(user_id: int, settings: dict, file_path: str, source_msg=None, index_no: int = 0):
    config_path = str(settings.get("rclone_config_path", "") or "").strip()
    remote_path = str(settings.get("rclone_remote_path", "") or "").strip()
    if not config_path or not os.path.exists(config_path):
        raise RuntimeError("rclone config missing hai.")
    if not remote_path:
        raise RuntimeError("rclone remote path set nahi hai.")
    target = remote_path.rstrip("/") + "/" + os.path.basename(file_path)
    proc = await asyncio.create_subprocess_exec(
        getattr(cfg, "RCLONE_BIN", "rclone"), "copyto", file_path, target, "--config", config_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((stderr or stdout or b"rclone failed").decode("utf-8", "ignore")[:500])

    sidecar_target = ""
    annotation = build_storage_annotation(source_msg, settings, index_no=index_no, storage_mode="rclone") if source_msg else ""
    if annotation and source_msg and is_media_message(source_msg):
        sidecar_path = os.path.join(TEMP_DIR, f"{os.path.basename(file_path)}.caption.txt")
        sidecar_target = f"{target}.caption.txt"
        try:
            Path(sidecar_path).write_text(annotation, encoding="utf-8")
            sidecar_proc = await asyncio.create_subprocess_exec(
                getattr(cfg, "RCLONE_BIN", "rclone"), "copyto", sidecar_path, sidecar_target, "--config", config_path,
                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
            )
            side_stdout, side_stderr = await sidecar_proc.communicate()
            if sidecar_proc.returncode != 0:
                raise RuntimeError((side_stderr or side_stdout or b"rclone caption sidecar failed").decode("utf-8", "ignore")[:500])
        finally:
            if os.path.exists(sidecar_path):
                try:
                    os.remove(sidecar_path)
                except Exception:
                    pass

    update_user_settings(user_id, {"rclone_last_file_path": target})
    if sidecar_target:
        return {"path": target, "caption_sidecar": sidecar_target}
    return {"path": target}


async def validate_rclone_settings_for_user(settings: dict):
    config_path = str(settings.get("rclone_config_path", "") or "").strip()
    remote_path = str(settings.get("rclone_remote_path", "") or "").strip()
    if not config_path or not os.path.exists(config_path):
        raise RuntimeError("rclone.conf missing")
    if not remote_path:
        raise RuntimeError("remote path missing")
    proc = await asyncio.create_subprocess_exec(
        getattr(cfg, "RCLONE_BIN", "rclone"), "lsf", remote_path, "--max-depth", "1", "--config", config_path,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError((stderr or stdout or b"rclone validation failed").decode("utf-8", "ignore")[:500])
    return {"path": remote_path}


async def validate_telegram_destination(client, settings: dict):
    destination = normalize_target(settings.get("upload_destination", "")) or DEFAULT_DESTINATION or None
    if not destination:
        raise RuntimeError("Telegram destination set nahi hai")
    chat = await client.get_chat(destination)
    me = await client.get_me()
    try:
        member = await client.get_chat_member(chat.id, me.id)
        member_status = str(getattr(member, "status", "unknown"))
    except Exception:
        member_status = "unknown"
    return {"chat_id": chat.id, "title": getattr(chat, "title", None) or getattr(chat, "first_name", None) or "Unknown", "type": str(getattr(chat, "type", "unknown")), "member_status": member_status}


async def validate_current_destination_settings(client, settings: dict):
    storage_mode = normalize_storage_mode(settings.get("storage_mode", "telegram"))
    if storage_mode == "gdrive":
        return await validate_gdrive_settings_for_user(settings)
    if storage_mode == "rclone":
        return await validate_rclone_settings_for_user(settings)
    return await validate_telegram_destination(client, settings)
