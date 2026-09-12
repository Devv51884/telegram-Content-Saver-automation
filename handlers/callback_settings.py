from __future__ import annotations

from runtime_context import *
from services.auth_admin_service import *
from services.storage_service import *
from services.task_service import *
from services.batch_transfer_service import *

async def handle_settings_callbacks(client, callback_query, user_id: int, data: str, s: dict):
    if data == "show_upload_mode":
        text = build_upload_mode_message(user_id)
        kb = upload_mode_buttons(get_user_telegram_upload_mode(user_id))

    elif data == "toggle_upload_mode":
        current = str(s.get("telegram_upload_mode", s.get("upload_mode", "media")) or "media").strip().lower()
        new_mode = "document" if current == "media" else "media"
        update_user_settings(user_id, {"upload_mode": new_mode, "telegram_upload_mode": new_mode})
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data.startswith("set_upload_mode:"):
        new_mode = data.split(":", 1)[1].strip().lower()
        if new_mode not in {"media", "document"}:
            new_mode = "media"
        update_user_settings(user_id, {"upload_mode": new_mode, "telegram_upload_mode": new_mode})
        text = build_upload_mode_message(user_id)
        kb = upload_mode_buttons(new_mode)

    elif data == "show_thumbnail":
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(s.get("thumbnail_enabled", False), has_file=bool(s.get("thumbnail_file_id")))

    elif data == "toggle_thumbnail_enabled":
        s["thumbnail_enabled"] = not s.get("thumbnail_enabled", False)
        update_user_settings(user_id, s)
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(s["thumbnail_enabled"], has_file=bool(s.get("thumbnail_file_id")))

    elif data == "view_thumbnail_photo":
        thumb_id = s.get("thumbnail_file_id")
        if thumb_id:
            try:
                await callback_query.message.reply_photo(
                    photo=thumb_id,
                    caption="🖼️ <b>Current Custom Thumbnail</b>",
                )
                await callback_query.answer("🖼️ Thumbnail bhej diya gaya!")
            except Exception as e:
                await callback_query.answer(f"❌ Thumbnail load nahi ho paya: {e}", show_alert=True)
        else:
            await callback_query.answer("⚠️ Koi custom thumbnail set nahi hai!", show_alert=True)
        return True

    elif data == "set_thumbnail_photo":
        set_user_state(user_id, "set_thumbnail_photo")
        await callback_query.message.reply_text("🖼️ Ab ek photo bhejo jise custom thumbnail save karna hai.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_thumbnail":
        update_user_settings(user_id, {"thumbnail_file_id": "", "thumbnail_enabled": False})
        text = thumbnail_text(user_id)
        kb = thumbnail_buttons(False, has_file=False)

    elif data == "show_caption":
        text = caption_text(user_id)
        cap_state = get_caption_settings_for_mode(s)
        kb = caption_buttons(cap_state.get("enabled", False), has_caption=bool(cap_state.get("text")))

    elif data == "toggle_caption_enabled":
        caption_state = get_caption_settings_for_mode(s)
        update_user_settings(user_id, {caption_state["enabled_key"]: not caption_state.get("enabled", False)})
        s = get_user_settings(user_id)
        text = caption_text(user_id)
        cap_state = get_caption_settings_for_mode(s)
        kb = caption_buttons(cap_state.get("enabled", False), has_caption=bool(cap_state.get("text")))

    elif data == "show_caption_index_settings":
        text = caption_text(user_id)
        kb = caption_index_buttons(s.get("caption_index_enabled", True))

    elif data == "toggle_caption_index_enabled":
        s["caption_index_enabled"] = not s.get("caption_index_enabled", True)
        update_user_settings(user_id, s)
        text = caption_text(user_id)
        kb = caption_index_buttons(s.get("caption_index_enabled", True))

    elif data == "set_caption_index_padding":
        set_user_state(user_id, "set_caption_index_padding")
        await callback_query.message.reply_text("🔢 Ab caption index padding bhejo.\nExample: 2\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_caption_index_start":
        set_user_state(user_id, "set_caption_index_start")
        await callback_query.message.reply_text("🚀 Ab caption index start value bhejo.\nExample: 1\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_caption_text":
        set_user_state(user_id, "set_caption_text")
        current_mode = normalize_storage_mode(s.get("storage_mode", "telegram"))
        await callback_query.message.reply_text(f"ðŸ“  Ab {current_mode} mode ke liye custom caption bhejo.\n{{index}} use kar sakte ho.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_caption":
        caption_state = get_caption_settings_for_mode(s)
        update_user_settings(user_id, {caption_state["text_key"]: "", caption_state["enabled_key"]: False})
        text = caption_text(user_id)
        kb = caption_buttons(False, has_caption=False)

    elif data == "show_prefix":
        text = prefix_text(user_id)
        kb = simple_set_buttons("set_prefix", "remove_prefix")

    elif data == "set_prefix":
        set_user_state(user_id, "set_prefix")
        await callback_query.message.reply_text("🏷️ Ab prefix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_prefix":
        update_user_settings(user_id, {"prefix": ""})
        text = prefix_text(user_id)
        kb = simple_set_buttons("set_prefix", "remove_prefix")

    elif data == "show_suffix":
        text = suffix_text(user_id)
        kb = simple_set_buttons("set_suffix", "remove_suffix")

    elif data == "set_suffix":
        set_user_state(user_id, "set_suffix")
        await callback_query.message.reply_text("🔖 Ab suffix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_suffix":
        update_user_settings(user_id, {"suffix": ""})
        text = suffix_text(user_id)
        kb = simple_set_buttons("set_suffix", "remove_suffix")

    elif data == "show_auto_rename":
        has_rename = bool(s.get("auto_rename") or s.get("rename_template") or s.get("filename_prefix") or s.get("filename_suffix"))
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(s.get("auto_rename_enabled", False), has_rename=has_rename)

    elif data == "toggle_auto_rename_enabled":
        s["auto_rename_enabled"] = not s.get("auto_rename_enabled", False)
        update_user_settings(user_id, s)
        has_rename = bool(s.get("auto_rename") or s.get("rename_template") or s.get("filename_prefix") or s.get("filename_suffix"))
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(s["auto_rename_enabled"], has_rename=has_rename)

    elif data == "set_auto_rename":
        set_user_state(user_id, "set_auto_rename")
        await callback_query.message.reply_text("✏️ Ab simple auto rename value bhejo.\n{index} aur {filename} use kar sakte ho.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_rename_template":
        set_user_state(user_id, "set_rename_template")
        await callback_query.message.reply_text("🧩 Ab rename template bhejo.\nExample: Movie_{index}\nYa: {index}_{filename}\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_filename_prefix":
        set_user_state(user_id, "set_filename_prefix")
        await callback_query.message.reply_text("🏷️ Ab filename prefix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_filename_suffix":
        set_user_state(user_id, "set_filename_suffix")
        await callback_query.message.reply_text("🔖 Ab filename suffix bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "show_filename_index_settings":
        text = auto_rename_text(user_id)
        kb = filename_index_buttons(s.get("filename_index_enabled", False))

    elif data == "toggle_filename_index_enabled":
        s["filename_index_enabled"] = not s.get("filename_index_enabled", False)
        update_user_settings(user_id, s)
        text = auto_rename_text(user_id)
        kb = filename_index_buttons(s.get("filename_index_enabled", False))

    elif data == "set_filename_index_padding":
        set_user_state(user_id, "set_filename_index_padding")
        await callback_query.message.reply_text("🔢 Ab filename index padding bhejo.\nExample: 2\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_filename_index_start":
        set_user_state(user_id, "set_filename_index_start")
        await callback_query.message.reply_text("🚀 Ab filename index start value bhejo.\nExample: 1\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_auto_rename":
        update_user_settings(user_id, {"auto_rename": "", "rename_template": "", "filename_prefix": "", "filename_suffix": "", "auto_rename_enabled": False, "filename_index_enabled": False})
        text = auto_rename_text(user_id)
        kb = auto_rename_buttons(False, has_rename=False)

    elif data == "show_destination":
        text = destination_text(user_id)
        kb = destination_buttons(bool(s.get("upload_destination")), bool(s.get("topic_id")))

    elif data == "set_destination":
        set_user_state(user_id, "set_destination")
        await callback_query.message.reply_text("📢 Ab upload destination bhejo.\nChat ID ya @channelusername format me.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data in {"clear_destination", "remove_destination"}:
        update_user_settings(user_id, {"upload_destination": ""})
        s = get_user_settings(user_id)
        text = destination_text(user_id)
        kb = destination_buttons(bool(s.get("upload_destination")), bool(s.get("topic_id")))

    elif data == "show_topic_id":
        text = topic_id_text(user_id)
        kb = destination_buttons(bool(s.get("upload_destination")), bool(s.get("topic_id")))

    elif data == "set_topic_id":
        set_user_state(user_id, "set_topic_id")
        await callback_query.message.reply_text("🧵 Ab topic id bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data in {"clear_topic_id", "remove_topic_id"}:
        update_user_settings(user_id, {"topic_id": ""})
        s = get_user_settings(user_id)
        text = topic_id_text(user_id)
        kb = destination_buttons(bool(s.get("upload_destination")), bool(s.get("topic_id")))

    elif data == "show_replace_words":
        text = replace_words_text(user_id)
        kb = replace_words_buttons(bool(get_file_replace_rules(s)), bool(get_caption_replace_rules(s)))

    elif data == "show_advanced_settings":
        text = advanced_settings_text(user_id)
        kb = advanced_settings_buttons(
            has_session=has_user_session(user_id),
            has_personal_bot=bool(s.get("personal_bot_token")),
            is_admin=is_admin(user_id),
            storage_mode=s.get("storage_mode", "telegram"),
        )

    elif data == "set_replace_words":
        set_user_state(user_id, "set_replace_words")
        await callback_query.message.reply_text("ðŸ” Ab combined remove/replace rules bhejo.\nYe file aur caption dono par apply hongi.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_replace_words_file":
        set_user_state(user_id, "set_replace_words_file")
        await callback_query.message.reply_text("ðŸ” Ab file remove/replace rules bhejo.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "set_replace_words_caption":
        set_user_state(user_id, "set_replace_words_caption")
        await callback_query.message.reply_text("ðŸ” Ab caption remove/replace rules bhejo.\nExample: old:new, test:\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_replace_words":
        update_replace_rule_settings(user_id, s, file_rules="", caption_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(False, False)

    elif data == "clear_replace_words_file":
        updated = update_replace_rule_settings(user_id, s, file_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(bool(get_file_replace_rules(updated)), bool(get_caption_replace_rules(updated)))

    elif data == "clear_replace_words_caption":
        updated = update_replace_rule_settings(user_id, s, caption_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(bool(get_file_replace_rules(updated)), bool(get_caption_replace_rules(updated)))

    elif data == "toggle_replace_words":
        await callback_query.answer("File aur caption rules alag set/clear karo")
        return True

    elif data == "clear_replace_words":
        update_replace_rule_settings(user_id, s, file_rules="", caption_rules="")
        text = replace_words_text(user_id)
        kb = replace_words_buttons(False, False)

    elif data == "show_metadata":
        text = metadata_home_text(user_id)
        kb = metadata_buttons(s["metadata_enabled"])

    elif data == "toggle_metadata_enabled":
        s["metadata_enabled"] = not s["metadata_enabled"]
        update_user_settings(user_id, s)
        text = metadata_home_text(user_id)
        kb = metadata_buttons(s["metadata_enabled"])

    elif data == "show_metadata_video_title":
        text = metadata_field_text(user_id, "Video Title", "metadata_video_title")
        kb = metadata_field_buttons("set_metadata_video_title", "remove_metadata_video_title")

    elif data == "set_metadata_video_title":
        set_user_state(user_id, "set_metadata_video_title")
        await callback_query.message.reply_text("ðŸŽ¬ Ab Video Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_metadata_video_title":
        update_user_settings(user_id, {"metadata_video_title": ""})
        text = metadata_field_text(user_id, "Video Title", "metadata_video_title")
        kb = metadata_field_buttons("set_metadata_video_title", "remove_metadata_video_title")

    elif data == "show_metadata_video_author":
        text = metadata_field_text(user_id, "Video Author", "metadata_video_author")
        kb = metadata_field_buttons("set_metadata_video_author", "remove_metadata_video_author")

    elif data == "set_metadata_video_author":
        set_user_state(user_id, "set_metadata_video_author")
        await callback_query.message.reply_text("ðŸ‘¤ Ab Video Author bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_metadata_video_author":
        update_user_settings(user_id, {"metadata_video_author": ""})
        text = metadata_field_text(user_id, "Video Author", "metadata_video_author")
        kb = metadata_field_buttons("set_metadata_video_author", "remove_metadata_video_author")

    elif data == "show_metadata_audio_title":
        text = metadata_field_text(user_id, "Audio Title", "metadata_audio_title")
        kb = metadata_field_buttons("set_metadata_audio_title", "remove_metadata_audio_title")

    elif data == "set_metadata_audio_title":
        set_user_state(user_id, "set_metadata_audio_title")
        await callback_query.message.reply_text("ðŸŽµ Ab Audio Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_metadata_audio_title":
        update_user_settings(user_id, {"metadata_audio_title": ""})
        text = metadata_field_text(user_id, "Audio Title", "metadata_audio_title")
        kb = metadata_field_buttons("set_metadata_audio_title", "remove_metadata_audio_title")

    elif data == "show_metadata_subtitle_title":
        text = metadata_field_text(user_id, "Subtitle Title", "metadata_subtitle_title")
        kb = metadata_field_buttons("set_metadata_subtitle_title", "remove_metadata_subtitle_title")

    elif data == "set_metadata_subtitle_title":
        set_user_state(user_id, "set_metadata_subtitle_title")
        await callback_query.message.reply_text("ðŸ’¬ Ab Subtitle Title bhejo.\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "remove_metadata_subtitle_title":
        update_user_settings(user_id, {"metadata_subtitle_title": ""})
        text = metadata_field_text(user_id, "Subtitle Title", "metadata_subtitle_title")
        kb = metadata_field_buttons("set_metadata_subtitle_title", "remove_metadata_subtitle_title")

    elif data == "show_index_settings":
        text = index_info_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == "toggle_upload_mode_legacy":
        current_mode = str(s.get("telegram_upload_mode", s.get("upload_mode", "media")) or "media").strip().lower()
        new_mode = "media" if current_mode == "document" else "document"
        update_user_settings(user_id, {"upload_mode": new_mode, "telegram_upload_mode": new_mode})
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "toggle_index_mode":
        current = is_index_mode(user_id)
        set_index_mode(user_id, not current)
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "show_index_stats":
        text = index_stats_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == "show_index_info":
        text = index_info_text(user_id)
        kb = index_buttons(is_index_mode(user_id))

    elif data == "show_batch_settings":
        text = batch_text(user_id)
        kb = batch_buttons(is_batch_mode(user_id), is_premium_user(user_id))

    elif data == "toggle_batch_mode":
        set_batch_mode(user_id, not is_batch_mode(user_id))
        text = batch_text(user_id)
        kb = batch_buttons(is_batch_mode(user_id), is_premium_user(user_id))

    elif data == "set_batch_links":
        set_user_state(user_id, "set_batch_links")
        await callback_query.message.reply_text("ðŸ“¥ Ab multiple Telegram links bhejo.\nRange format bhi de sakte ho like:\nhttps://t.me/channel/39-69\n\n/cancel bhej kar cancel kar sakte ho.")
        await callback_query.answer()
        return True
    elif data == "clear_batch_links":
        save_batch_input(user_id, "")
        text = batch_text(user_id)
        kb = batch_buttons(is_batch_mode(user_id), is_premium_user(user_id))

    elif data == "start_batch_now":
        batch_input = get_batch_input(user_id)
        await callback_query.answer("Batch start ho raha hai...")
        await process_batch_links(client, user_id, callback_query.message, batch_input)
        return True
    elif data == "reset_all_settings":
        reset_user_settings(user_id)
        clear_user_state(user_id)
        text = settings_home_text(user_id)
        kb = build_settings_home_markup(user_id)

    elif data == "close_settings":
        try:
            await callback_query.message.delete()
        except Exception:
            pass
        await callback_query.answer("Closed")
        return True
    else:
        return False

    try:
        await callback_query.message.edit_text(text, reply_markup=kb, disable_web_page_preview=True)
    except Exception:
        pass

    await callback_query.answer("\u2705 Updated")
    return True
