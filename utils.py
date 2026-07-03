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
