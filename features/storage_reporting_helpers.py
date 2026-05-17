from __future__ import annotations

import re

__all__ = [
    "analyze_batch_input_impl",
    "get_admin_overview_impl",
]


def analyze_batch_input_impl(raw_text: str, *, expand_range_fn, parse_links_fn):
    raw_text = str(raw_text or "")
    tokens = []
    invalid_tokens = []
    for line in raw_text.splitlines():
        for part in line.split():
            token = str(part or "").strip()
            if not token:
                continue
            expanded = expand_range_fn(token)
            if expanded:
                tokens.extend(expanded)
            elif token.startswith("http://") or token.startswith("https://"):
                invalid_tokens.append(token)

    links = parse_links_fn(raw_text)
    summary = {
        "valid_links": len(links),
        "invalid_links": len(invalid_tokens),
        "public_links": 0,
        "private_links": 0,
        "topic_links": 0,
    }
    for link in links:
        value = str(link)
        if "/c/" in value:
            summary["private_links"] += 1
        else:
            summary["public_links"] += 1
        if re.search(r"https?://(?:t|telegram)\.me/(?:c/\d+/\d+/\d+|[A-Za-z0-9_]+/\d+/\d+)", value):
            summary["topic_links"] += 1
    summary["invalid_tokens"] = invalid_tokens[:20]
    return summary


def get_admin_overview_impl(limit_recent_users: int, *, user_count_fn, banned_count_fn, sync_premium_stats_fn, recent_users_fn, all_tasks_fn, is_running_task_fn, failed_tasks_fn, stats_fn):
    return {
        "total_users": user_count_fn(),
        "banned_users": banned_count_fn(),
        "premium_users": sync_premium_stats_fn(),
        "recent_users": recent_users_fn(limit_recent_users),
        "running_tasks": len([task for task in all_tasks_fn().values() if is_running_task_fn(task)]),
        "failed_tasks": len(failed_tasks_fn()),
        "stats": stats_fn(),
    }
