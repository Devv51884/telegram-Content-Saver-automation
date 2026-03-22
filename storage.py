import json
import os
from datetime import datetime
from config import SETTINGS_FILE, STATE_FILE, USERS_FILE, BANNED_FILE

DEFAULT_SETTINGS = {
    'upload_mode': 'Telegram',
    'thumbnail': False,
    'caption': False,
    'prefix': '',
    'suffix': '',
    'auto_rename': '',
    'metadata': False,
    'upload_destination': '',
    'topic_id': '',
    'replace_words': '',
}

WAITING_KEYS = {
    'set_prefix': 'prefix',
    'set_suffix': 'suffix',
    'set_auto_rename': 'auto_rename',
    'set_destination': 'upload_destination',
    'set_topic_id': 'topic_id',
    'set_replace_words': 'replace_words',
}


def load_json(path, default):
    if not os.path.exists(path):
        return default
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def get_all_settings():
    return load_json(SETTINGS_FILE, {})


def save_all_settings(data):
    save_json(SETTINGS_FILE, data)


def get_user_settings(user_id: int):
    all_settings = get_all_settings()
    uid = str(user_id)
    if uid not in all_settings:
        all_settings[uid] = DEFAULT_SETTINGS.copy()
        save_all_settings(all_settings)
    return all_settings[uid]


def update_user_settings(user_id: int, new_data: dict):
    all_settings = get_all_settings()
    uid = str(user_id)
    current = all_settings.get(uid, DEFAULT_SETTINGS.copy())
    current.update(new_data)
    all_settings[uid] = current
    save_all_settings(all_settings)


def reset_user_settings(user_id: int):
    all_settings = get_all_settings()
    all_settings[str(user_id)] = DEFAULT_SETTINGS.copy()
    save_all_settings(all_settings)


def get_all_states():
    return load_json(STATE_FILE, {})


def save_all_states(data):
    save_json(STATE_FILE, data)


def set_user_state(user_id: int, state: str):
    states = get_all_states()
    states[str(user_id)] = state
    save_all_states(states)


def get_user_state(user_id: int):
    states = get_all_states()
    return states.get(str(user_id), '')


def clear_user_state(user_id: int):
    states = get_all_states()
    states.pop(str(user_id), None)
    save_all_states(states)


def get_all_users():
    return load_json(USERS_FILE, {})


def save_all_users(data):
    save_json(USERS_FILE, data)


def register_user(user):
    if not user:
        return
    users = get_all_users()
    uid = str(user.id)
    users[uid] = {
        'id': user.id,
        'first_name': getattr(user, 'first_name', '') or '',
        'username': getattr(user, 'username', '') or '',
        'last_seen': datetime.utcnow().isoformat(),
    }
    save_all_users(users)


def user_count() -> int:
    return len(get_all_users())


def get_recent_users(limit: int = 10):
    users = list(get_all_users().values())
    users.sort(key=lambda x: x.get('last_seen', ''), reverse=True)
    return users[:limit]


def get_banned_users():
    data = load_json(BANNED_FILE, [])
    return set(int(x) for x in data if str(x).isdigit())


def save_banned_users(data):
    save_json(BANNED_FILE, sorted(list(data)))


def is_banned(user_id: int) -> bool:
    return user_id in get_banned_users()


def ban_user(user_id: int):
    banned = get_banned_users()
    banned.add(int(user_id))
    save_banned_users(banned)


def unban_user(user_id: int):
    banned = get_banned_users()
    banned.discard(int(user_id))
    save_banned_users(banned)


def banned_count() -> int:
    return len(get_banned_users())
