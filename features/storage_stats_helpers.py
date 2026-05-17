from __future__ import annotations


__all__ = ["get_detailed_stats_impl"]


def get_detailed_stats_impl(
    *,
    get_stats_fn,
    get_all_users_sorted_fn,
    get_all_settings_fn,
    get_all_tasks_fn,
    now_utc_fn,
    parse_iso_fn,
    normalize_settings_fn,
    active_statuses,
    get_recent_users_fn,
    has_user_session_fn,
    sync_premium_stats_fn,
    timedelta_cls,
):
    stats = get_stats_fn()
    users = get_all_users_sorted_fn()
    settings_map = get_all_settings_fn()
    tasks = get_all_tasks_fn()
    now = now_utc_fn()

    active_users = 0
    for row in users:
        parsed = parse_iso_fn(row.get("last_seen", ""))
        if parsed and (now - parsed) <= timedelta_cls(days=7):
            active_users += 1

    storage_counts = {"telegram": 0, "gdrive": 0, "rclone": 0}
    for uid in settings_map:
        mode = str(normalize_settings_fn(settings_map.get(uid, {})).get("storage_mode", "telegram")).lower()
        storage_counts[mode] = storage_counts.get(mode, 0) + 1

    task_counts = {"total": 0, "completed": 0, "failed": 0, "running": 0, "cancelled": 0, "queued": 0, "batch": 0}
    for task in tasks.values():
        task_counts["total"] += 1
        status = str(task.get("status", "") or "").strip().lower()
        if status in active_statuses:
            task_counts["running"] += 1
        elif status in task_counts:
            task_counts[status] += 1
        if str(task.get("mode", "") or "").strip().lower() == "batch":
            task_counts["batch"] += 1

    return {
        "stats": stats,
        "total_users": len(users),
        "recent_users": get_recent_users_fn(10),
        "active_users": active_users,
        "logged_in_users": len([uid for uid in settings_map if has_user_session_fn(int(uid))]),
        "premium_users": sync_premium_stats_fn(),
        "storage_counts": storage_counts,
        "task_counts": task_counts,
    }
