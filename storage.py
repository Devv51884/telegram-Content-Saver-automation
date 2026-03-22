import json
import os
from config import SETTINGS_FILE, STATE_FILE

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
