# -*- coding: utf-8 -*-
import random
import html
import aiohttp
from config import CAT_API_URL


async def get_random_cat_url() -> str:
    """
    Возвращает прямую ссылку на случайную картинку котика с cataas.com.
    Ключи/авторизация не нужны — обычный публичный GET.
    """
    return f"{CAT_API_URL}?rand={random.randint(1, 999999)}"


def esc(text) -> str:
    """
    Экранирует пользовательский текст перед вставкой в HTML-сообщение.
    Без этого текст с символами <, >, & от юзера ломает разметку,
    и bot.send_message тихо падает с исключением — сообщение просто не долетает.
    """
    if text is None:
        return ""
    return html.escape(str(text))


async def replace_message(source_message, state, text, reply_markup=None):
    """
    Удаляет предыдущее сообщение бота (если оно было сохранено в состоянии)
    и отправляет новое — чтобы сообщения не копились друг под другом при навигации.
    """
    data = await state.get_data()
    last_id = data.get("_last_bot_msg")
    if last_id:
        try:
            await source_message.bot.delete_message(source_message.chat.id, last_id)
        except Exception:
            pass
    sent = await source_message.answer(text, reply_markup=reply_markup)
    await state.update_data(_last_bot_msg=sent.message_id)
    return sent


async def replace_message_photo(source_message, state, photo, caption, reply_markup=None):
    """То же самое, но когда нужно показать фото с подписью."""
    data = await state.get_data()
    last_id = data.get("_last_bot_msg")
    if last_id:
        try:
            await source_message.bot.delete_message(source_message.chat.id, last_id)
        except Exception:
            pass
    sent = await source_message.answer_photo(photo, caption=caption, reply_markup=reply_markup)
    await state.update_data(_last_bot_msg=sent.message_id)
    return sent


def format_profile_text(user_row, profile_row):
    """
    user_row: (user_id, username, full_name, ban_status, created_at)
    profile_row: (user_id, bio, photo_file_id)
    """
    import texts as t
    username = f"@{user_row[1]}" if user_row[1] else "—"
    bio = esc(profile_row[1]) if profile_row and profile_row[1] else t.PROFILE_EMPTY_BIO
    text = (
        f"{t.PROFILE_HEADER}\n\n"
        f"Имя: {esc(user_row[2])}\n"
        f"Юзернейм: {username}\n"
        f"ID: {user_row[0]}\n\n"
        f"{bio}"
    )
    photo = profile_row[2] if profile_row else None
    return text, photo
