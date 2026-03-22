import json
import os
from datetime import datetime
from config import (
    SETTINGS_FILE,
    STATE_FILE,
    USERS_FILE,
    BANNED_FILE,
    INDEX_FILE,
    INDEX_STATE_FILE,
    SESSION_STORE_FILE,
    TASKS_FILE,
)

DEFAULT_SETTINGS = {
    'upload_mode': 'Telegram',
    'thumbnail_enabled': False,
    'thumbnail_file_id': '',
    'caption_enabled': False,
    'caption_text': '',
    'prefix': '',
    'suffix': '',
    'auto_rename': '',
    'metadata_enabled': False,
    'metadata_video_title': '',
    'metadata_video_author': '',
    'metadata_audio_title': '',
    'metadata_subtitle_title': '',
    'upload_destination': '',
    'topic_id': '',
    'replace_words': '',
    'index_mode': False,
    # V6 login/session helpers
    'authorized_mode': False,
    'last_login_user_id': 0,
}

WAITING_KEYS = {
    'set_prefix': 'prefix',
    'set_suffix': 'suffix',
    'set_auto_rename': 'auto_rename',
    'set_destination': 'upload_destination',
    'set_topic_id': 'topic_id',
    'set_replace_words': 'replace_words',
    'set_caption_text': 'caption_text',
    'set_metadata_video_title': 'metadata_video_title',
    'set_metadata_video_author': 'metadata_video_author',
    'set_metadata_audio_title': 'metadata_audio_title',
    'set_metadata_subtitle_title': 'metadata_subtitle_title',
    'set_thumbnail_photo': 'thumbnail_file_id',

    # V6 login flow states
    'login_phone': 'login_phone',
    'login_code': 'login_code',
    'login_password': 'login_password',
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
    folder = os.path.dirname(path)
    if folder:
        os.makedirs(folder, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# ================= SETTINGS =================

def get_all_settings():
    return load_json(SETTINGS_FILE, {})


def save_all_settings(data):
    save_json(SETTINGS_FILE, data)


def get_user_settings(user_id: int):
    all_settings = get_all_settings()
    uid = str(user_id)
    current = all_settings.get(uid, {})

    merged = DEFAULT_SETTINGS.copy()
    if isinstance(current, dict):
        merged.update(current)

    if uid not in all_settings or merged != current:
        all_settings[uid] = merged
        save_all_settings(all_settings)

    return merged


def update_user_settings(user_id: int, new_data: dict):
    all_settings = get_all_settings()
    uid = str(user_id)

    current = DEFAULT_SETTINGS.copy()
    existing = all_settings.get(uid, {})
    if isinstance(existing, dict):
        current.update(existing)

    if isinstance(new_data, dict):
        current.update(new_data)

    all_settings[uid] = current
    save_all_settings(all_settings)


def reset_user_settings(user_id: int):
    all_settings = get_all_settings()
    all_settings[str(user_id)] = DEFAULT_SETTINGS.copy()
    save_all_settings(all_settings)


# ================= USER INPUT STATE =================

def get_all_states():
    return load_json(STATE_FILE, {})


def save_all_states(data):
    save_json(STATE_FILE, data)


def set_user_state(user_id: int, state: str):
    states = get_all_states()
    states[str(user_id)] = state
    save_all_states(states)


def get_user_state(user_id: int):
    return get_all_states().get(str(user_id), '')


def clear_user_state(user_id: int):
    states = get_all_states()
    states.pop(str(user_id), None)
    save_all_states(states)


# ================= USERS =================

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


# ================= BANNED USERS =================

def get_banned_users():
    data = load_json(BANNED_FILE, [])
    return set(int(x) for x in data if str(x).lstrip('-').isdigit())


def save_banned_users(data):
    save_json(BANNED_FILE, sorted(list(data)))


def is_banned(user_id: int) -> bool:
    return int(user_id) in get_banned_users()


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


# ================= INDEX ENTRIES =================

def get_all_index_entries():
    return load_json(INDEX_FILE, [])


def save_all_index_entries(data):
    save_json(INDEX_FILE, data)


def add_index_entry(entry: dict):
    entries = get_all_index_entries()

    clean_entry = dict(entry) if isinstance(entry, dict) else {}
    clean_entry['index_no'] = len(entries) + 1
    clean_entry['indexed_at'] = datetime.utcnow().isoformat()

    entries.append(clean_entry)
    save_all_index_entries(entries)
    return clean_entry['index_no']


def index_count() -> int:
    return len(get_all_index_entries())


# ================= INDEX MODE / INDEX STATE =================

def get_index_state():
    return load_json(INDEX_STATE_FILE, {})


def save_index_state(data):
    save_json(INDEX_STATE_FILE, data)


def set_index_mode(user_id: int, enabled: bool):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, {'enabled': False, 'count': 0})
    current['enabled'] = bool(enabled)
    state[key] = current
    save_index_state(state)

    update_user_settings(user_id, {'index_mode': bool(enabled)})


def is_index_mode(user_id: int) -> bool:
    state_enabled = bool(get_index_state().get(str(user_id), {}).get('enabled', False))
    settings_enabled = bool(get_user_settings(user_id).get('index_mode', False))
    return state_enabled or settings_enabled


def increase_index_user_count(user_id: int):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, {'enabled': False, 'count': 0})
    current['count'] = int(current.get('count', 0)) + 1
    state[key] = current
    save_index_state(state)
    return current['count']


def get_index_user_count(user_id: int) -> int:
    return int(get_index_state().get(str(user_id), {}).get('count', 0))


# ================= SESSION STORE (V6) =================

def get_all_user_sessions():
    data = load_json(SESSION_STORE_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_user_sessions(data):
    save_json(SESSION_STORE_FILE, data)


def save_user_session(user_id: int, session_string: str, tg_user_id: int = 0, phone: str = ''):
    sessions = get_all_user_sessions()
    sessions[str(user_id)] = {
        'session_string': session_string,
        'tg_user_id': tg_user_id,
        'phone': phone,
        'saved_at': datetime.utcnow().isoformat(),
    }
    save_all_user_sessions(sessions)

    update_user_settings(user_id, {
        'authorized_mode': True,
        'last_login_user_id': int(tg_user_id or 0),
    })


def get_user_session(user_id: int):
    return get_all_user_sessions().get(str(user_id), {})


def get_user_session_string(user_id: int) -> str:
    return str(get_user_session(user_id).get('session_string', '') or '')


def has_user_session(user_id: int) -> bool:
    return bool(get_user_session_string(user_id))


def delete_user_session(user_id: int):
    sessions = get_all_user_sessions()
    sessions.pop(str(user_id), None)
    save_all_user_sessions(sessions)

    update_user_settings(user_id, {
        'authorized_mode': False,
        'last_login_user_id': 0,
    })


# ================= LOGIN FLOW TEMP DATA (V6) =================

def set_login_temp(user_id: int, key: str, value):
    states = get_all_states()
    uid = str(user_id)
    current = states.get(uid, {})
    if not isinstance(current, dict):
        current = {'state': current} if current else {}
    current[key] = value
    states[uid] = current
    save_all_states(states)


def get_login_temp(user_id: int, key: str, default=None):
    states = get_all_states()
    current = states.get(str(user_id), {})
    if isinstance(current, dict):
        return current.get(key, default)
    return default


def get_user_state(user_id: int):
    raw = get_all_states().get(str(user_id), '')
    if isinstance(raw, dict):
        return raw.get('state', '')
    return raw


def set_user_state(user_id: int, state: str):
    states = get_all_states()
    uid = str(user_id)
    current = states.get(uid, {})
    if isinstance(current, dict):
        current['state'] = state
        states[uid] = current
    else:
        states[uid] = {'state': state}
    save_all_states(states)


def clear_user_state(user_id: int):
    states = get_all_states()
    states.pop(str(user_id), None)
    save_all_states(states)


# ================= TASK STORE (V6) =================

def get_all_tasks():
    data = load_json(TASKS_FILE, {})
    return data if isinstance(data, dict) else {}


def save_all_tasks(data):
    save_json(TASKS_FILE, data)


def set_task(task_id: str, data: dict):
    tasks = get_all_tasks()
    current = tasks.get(task_id, {})
    if isinstance(current, dict):
        current.update(data or {})
    else:
        current = data or {}

    if 'updated_at' not in current:
        current['updated_at'] = datetime.utcnow().isoformat()
    else:
        current['updated_at'] = datetime.utcnow().isoformat()

    tasks[task_id] = current
    save_all_tasks(tasks)


def get_task(task_id: str):
    return get_all_tasks().get(task_id, {})


def delete_task(task_id: str):
    tasks = get_all_tasks()
    tasks.pop(task_id, None)
    save_all_tasks(tasks)


def get_user_tasks(user_id: int, limit: int = 20):
    tasks = list(get_all_tasks().values())
    tasks = [t for t in tasks if str(t.get('user_id')) == str(user_id)]
    tasks.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
    return tasks[:limit]


def count_running_tasks(user_id: int) -> int:
    tasks = get_user_tasks(user_id, limit=1000)
    count = 0
    for t in tasks:
        if t.get('status') in {'queued', 'fetching', 'downloading', 'uploading', 'processing'}:
            count += 1
    return count