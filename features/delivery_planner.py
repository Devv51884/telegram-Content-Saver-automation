from __future__ import annotations

from features.media_transforms import is_media_message


def normalize_link_type(info: dict | None) -> str:
    value = str((info or {}).get("link_type") or "").strip().lower()
    if value in {"public", "private", "public_topic", "private_topic", "direct_message"}:
        return value
    return "unknown"


def normalize_chat_type(value) -> str:
    value = str(value or "").strip().lower()
    if "." in value:
        value = value.rsplit(".", 1)[-1]
    return value


def normalize_member_status(value) -> str:
    value = str(value or "").strip().lower()
    if "." in value:
        value = value.rsplit(".", 1)[-1]
    return value


def source_has_protected_content(source_msg) -> bool:
    if not source_msg:
        return False
    if bool(getattr(source_msg, "has_protected_content", False)):
        return True
    chat = getattr(source_msg, "chat", None)
    if chat and bool(getattr(chat, "has_protected_content", False)):
        return True
    return False


def build_source_access_map(link_type: str, fetch_mode: str, has_user_session_client: bool) -> dict:
    link_type = str(link_type or "unknown").strip().lower()
    fetch_mode = str(fetch_mode or "bot").strip().lower()
    access = {"main_bot": False, "user_session": False, "personal_bot": False}

    if link_type == "direct_message":
        access["main_bot"] = True
        return access

    if link_type in {"private", "private_topic"}:
        access["user_session"] = bool(has_user_session_client)
        return access

    if link_type in {"public", "public_topic"}:
        access["main_bot"] = fetch_mode == "bot"
        access["user_session"] = bool(has_user_session_client)
        return access

    access["main_bot"] = fetch_mode == "bot"
    access["user_session"] = bool(has_user_session_client and fetch_mode == "user")
    return access


def is_positive_writable_target(chat_type: str, member_status: str) -> bool:
    chat_type = normalize_chat_type(chat_type)
    member_status = normalize_member_status(member_status)

    if chat_type in {"private", "bot"}:
        return True
    if chat_type in {"group", "supergroup"}:
        return member_status in {"member", "administrator", "creator", "owner"}
    if chat_type == "channel":
        return member_status in {"administrator", "creator", "owner"}
    return False


def choose_upload_client_kind(target_access: dict, prefer_personal_upload: bool = False) -> str | None:
    target_access = target_access or {}
    priority = ["personal_bot", "main_bot", "user_session"] if prefer_personal_upload else ["main_bot", "user_session", "personal_bot"]
    for kind in priority:
        if (target_access.get(kind) or {}).get("writable"):
            return kind
    return None


def choose_cached_client_kind(source_access: dict | None, target_access: dict | None) -> str | None:
    source_access = source_access or {}
    target_access = target_access or {}
    for kind in ("main_bot", "user_session"):
        if source_access.get(kind) and (target_access.get(kind) or {}).get("writable"):
            return kind
    return None


def choose_fast_cached_delivery_client_kind(
    source_access: dict | None,
    target_access: dict | None,
    *,
    prefer_personal_upload: bool = False,
) -> str | None:
    source_access = source_access or {}
    target_access = target_access or {}
    for kind in ("main_bot", "user_session", "personal_bot"):
        if source_access.get(kind) and (target_access.get(kind) or {}).get("writable"):
            return kind
    return None


def choose_relay_route_kinds(
    source_access: dict | None,
    target_access: dict | None,
    relay_access: dict | None,
    *,
    prefer_personal_upload: bool = False,
) -> tuple[str | None, str | None]:
    source_access = source_access or {}
    target_access = target_access or {}
    relay_access = relay_access or {}

    relay_client_kind = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
    if not relay_client_kind or relay_client_kind == "user_session":
        return None, None
    if not (relay_access.get(relay_client_kind) or {}).get("writable"):
        return None, None

    for source_kind in ("user_session", "main_bot"):
        if source_kind == relay_client_kind:
            continue
        if source_access.get(source_kind) and (relay_access.get(source_kind) or {}).get("writable"):
            return source_kind, relay_client_kind
    return None, None


def choose_relay_delivery_plan(
    source_access: dict | None,
    target_access: dict | None,
    relay_access: dict | None,
    *,
    relay_target_available: bool = False,
    prefer_personal_upload: bool = False,
    bot_pm_relay_available: bool = False,
) -> dict | None:
    if relay_target_available:
        relay_source_kind, relay_client_kind = choose_relay_route_kinds(
            source_access,
            target_access,
            relay_access,
            prefer_personal_upload=prefer_personal_upload,
        )
        if relay_source_kind and relay_client_kind:
            return {
                "relay_source_client_kind": relay_source_kind,
                "relay_client_kind": relay_client_kind,
                "relay_via": "log_channel",
            }

    if bot_pm_relay_available:
        return {
            "relay_source_client_kind": "user_session",
            "relay_client_kind": "main_bot",
            "relay_via": "bot_pm",
        }

    return None


def choose_log_copy_client_kind(destination_access: dict | None, log_access: dict | None, preferred_client_kind: str | None = None) -> str | None:
    destination_access = destination_access or {}
    log_access = log_access or {}
    priority = []
    preferred = str(preferred_client_kind or "").strip().lower()
    if preferred:
        priority.append(preferred)
    for kind in ("main_bot", "user_session", "personal_bot"):
        if kind not in priority:
            priority.append(kind)

    for kind in priority:
        dest_info = destination_access.get(kind) or {}
        log_info = log_access.get(kind) or {}
        if not dest_info.get("client"):
            continue
        if not log_info.get("writable"):
            continue
        if dest_info.get("writable") or dest_info.get("resolved"):
            return kind
    return None


def build_target_delivery_plan(
    *,
    is_media: bool,
    has_cached_file_id: bool,
    has_transforming: bool,
    is_protected: bool,
    source_access: dict | None,
    target_access: dict | None,
    allow_main_bot_direct: bool,
    allow_user_session_direct: bool,
    prefer_personal_upload: bool,
    direct_copy_blocked: bool = False,
    cached_send_allowed: bool = False,
    relay_access: dict | None = None,
    relay_target_available: bool = False,
    bot_pm_relay_available: bool = False,
) -> dict:
    source_access = source_access or {}
    target_access = target_access or {}
    relay_access = relay_access or {}

    plan = {
        "mode": "upload",
        "direct_client_kind": None,
        "cached_client_kind": None,
        "relay_source_client_kind": None,
        "relay_client_kind": None,
        "relay_via": "",
        "upload_client_kind": None,
        "fallback_reason": "",
        "error": "",
    }

    direct_transfer_allowed = not direct_copy_blocked and not has_transforming and not is_protected
    cached_transfer_allowed = bool(cached_send_allowed and not has_transforming and not is_protected)
    if direct_transfer_allowed:
        main_direct_ready = bool(source_access.get("main_bot")) and bool((target_access.get("main_bot") or {}).get("writable"))
        user_direct_ready = bool(source_access.get("user_session")) and bool((target_access.get("user_session") or {}).get("writable"))

        if allow_main_bot_direct and main_direct_ready:
            plan["mode"] = "direct"
            plan["direct_client_kind"] = "main_bot"
            return plan
        if allow_user_session_direct and user_direct_ready:
            plan["mode"] = "direct"
            plan["direct_client_kind"] = "user_session"
            return plan

    if cached_transfer_allowed:
        cached_client_kind = choose_fast_cached_delivery_client_kind(
            source_access,
            target_access,
            prefer_personal_upload=prefer_personal_upload,
        )
        if has_cached_file_id and cached_client_kind:
            plan["mode"] = "cached"
            plan["cached_client_kind"] = cached_client_kind
            return plan

    if direct_transfer_allowed:
        relay_plan = choose_relay_delivery_plan(
            source_access,
            target_access,
            relay_access,
            relay_target_available=relay_target_available,
            prefer_personal_upload=prefer_personal_upload,
            bot_pm_relay_available=bot_pm_relay_available,
        )
        if relay_plan:
            plan["mode"] = "relay"
            plan.update(relay_plan)
            return plan

    if has_transforming:
        plan["fallback_reason"] = "transforming_settings_enabled"
    elif direct_copy_blocked:
        plan["fallback_reason"] = "telegram_output_transform"
    elif is_protected:
        plan["fallback_reason"] = "protected_content"
    elif source_access.get("main_bot") or source_access.get("user_session"):
        plan["fallback_reason"] = "target_not_writable_by_source_client"
    else:
        plan["fallback_reason"] = "source_not_readable"

    if not is_media:
        plan["mode"] = "text"
        plan["upload_client_kind"] = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
        if not plan["upload_client_kind"]:
            plan["error"] = "No writable target client available"
        return plan

    if not direct_transfer_allowed:
        plan["upload_client_kind"] = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
        if not plan["upload_client_kind"]:
            plan["error"] = "No writable target client available"
        return plan

    if source_access.get("main_bot") or source_access.get("user_session"):
        plan["fallback_reason"] = "target_not_writable_by_source_client"
    else:
        plan["fallback_reason"] = "source_not_readable"

    plan["upload_client_kind"] = choose_upload_client_kind(target_access, prefer_personal_upload=prefer_personal_upload)
    if not plan["upload_client_kind"]:
        plan["error"] = "No writable target client available"
    return plan


def build_followup_delivery_plan_after_direct_failure(
    *,
    failed_client_kind: str,
    is_media: bool,
    has_cached_file_id: bool,
    has_transforming: bool,
    is_protected: bool,
    source_access: dict | None,
    target_access: dict | None,
    allow_main_bot_direct: bool,
    allow_user_session_direct: bool,
    prefer_personal_upload: bool,
    direct_copy_blocked: bool = False,
    cached_send_allowed: bool = False,
    relay_access: dict | None = None,
    relay_target_available: bool = False,
    bot_pm_relay_available: bool = False,
) -> dict:
    failed_client_kind = str(failed_client_kind or "").strip().lower()
    return build_target_delivery_plan(
        is_media=is_media,
        has_cached_file_id=has_cached_file_id,
        has_transforming=has_transforming,
        is_protected=is_protected,
        source_access=source_access,
        target_access=target_access,
        allow_main_bot_direct=bool(allow_main_bot_direct and failed_client_kind != "main_bot"),
        allow_user_session_direct=bool(allow_user_session_direct and failed_client_kind != "user_session"),
        prefer_personal_upload=prefer_personal_upload,
        direct_copy_blocked=direct_copy_blocked,
        cached_send_allowed=cached_send_allowed,
        relay_access=relay_access,
        relay_target_available=relay_target_available,
        bot_pm_relay_available=bot_pm_relay_available,
    )


def build_target_access_error(target, access_map: dict) -> str:
    access_map = access_map or {}
    details = []
    for kind in ("personal_bot", "main_bot", "user_session"):
        info = access_map.get(kind) or {}
        if not info.get("client"):
            continue
        if info.get("writable"):
            continue
        error_text = str(info.get("error") or "").strip()
        if error_text:
            details.append(f"{kind}: {error_text}")
        elif info.get("resolved"):
            details.append(f"{kind}: write access not confirmed")
        else:
            details.append(f"{kind}: target access unavailable")
    detail_text = " | ".join(details[:3])
    if detail_text:
        return f"No writable target client available for {target} | {detail_text}"
    return f"No writable target client available for {target}"


def describe_delivery_path(mode: str, client_kind: str | None) -> str:
    mode = str(mode or "").strip().lower()
    client_kind = str(client_kind or "").strip().lower()
    if mode == "direct":
        if client_kind == "main_bot":
            return "direct_copy"
        if client_kind == "user_session":
            return "direct_forward"
    if mode == "cached":
        return "cached_send"
    if mode == "relay":
        return "relay_copy"
    if mode == "text":
        return "text_send"
    if mode == "upload":
        return "download_upload"
    return mode or "unknown"


def describe_target_route(target, path: str, client_kind: str | None) -> str:
    target_text = str(target)
    client_text = str(client_kind or "unknown")
    if path == "direct_copy":
        return f"{target_text}: direct via {client_text}"
    if path == "direct_forward":
        return f"{target_text}: forward via {client_text}"
    if path == "cached_send":
        return f"{target_text}: cached via {client_text}"
    if path == "relay_copy":
        return f"{target_text}: relay via {client_text}"
    if path == "text_send":
        return f"{target_text}: text via {client_text}"
    if path == "download_upload":
        return f"{target_text}: upload via {client_text}"
    return f"{target_text}: {path} via {client_text}"


def select_download_client_kind(source_access: dict, client_map: dict) -> str | None:
    source_access = source_access or {}
    client_map = client_map or {}
    for kind in ("main_bot", "user_session"):
        if source_access.get(kind) and client_map.get(kind):
            return kind
    return None


def has_transferable_content(source_msg) -> bool:
    if not source_msg:
        return False
    if is_media_message(source_msg):
        return True
    if str(getattr(source_msg, "text", "") or "").strip():
        return True
    if str(getattr(source_msg, "caption", "") or "").strip():
        return True
    media_name = str(getattr(source_msg, "media", "") or "").strip().lower()
    if media_name and media_name not in {"none", "0", "messagemediatype.empty", "empty"}:
        return True
    return False


def get_transfer_validation_error(source_msg) -> str | None:
    if not source_msg:
        return "Source post fetch nahi hua. Link invalid ho sakti hai ya access missing hai."
    if getattr(source_msg, "empty", False):
        return "Source post empty/not found mili. Shayad link par post exist nahi karti."
    if getattr(source_msg, "service", None):
        return "Ye service/system message hai, isliye save nahi ki ja sakti."
    if not has_transferable_content(source_msg):
        return "Is link par transferable post content nahi mila. Post deleted, invalid, ya unsupported ho sakti hai."
    return None
