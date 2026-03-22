import json
import os
from datetime import datetime
from config import SETTINGS_FILE, STATE_FILE, USERS_FILE, BANNED_FILE, INDEX_FILE, INDEX_STATE_FILE

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
    current = all_settings.get(uid, {})

    # Backfill newly added keys for old users/settings files.
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
    return get_all_states().get(str(user_id), '')


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


def get_all_index_entries():
    return load_json(INDEX_FILE, [])


def save_all_index_entries(data):
    save_json(INDEX_FILE, data)


def add_index_entry(entry: dict):
    entries = get_all_index_entries()
    entry = dict(entry)
    entry['index_no'] = len(entries) + 1
    entry['indexed_at'] = datetime.utcnow().isoformat()
    entries.append(entry)
    save_all_index_entries(entries)
    return entry['index_no']


def index_count() -> int:
    return len(get_all_index_entries())


def get_index_state():
    return load_json(INDEX_STATE_FILE, {})


def save_index_state(data):
    save_json(INDEX_STATE_FILE, data)


def set_index_mode(user_id: int, enabled: bool):
    state = get_index_state()
    key = str(user_id)
    current = state.get(key, {'enabled': False, 'count': 0})
    current['enabled'] = enabled
    state[key] = current
    save_index_state(state)


def is_index_mode(user_id: int) -> bool:
    return bool(get_index_state().get(str(user_id), {}).get('enabled', False))


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
