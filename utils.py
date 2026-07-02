# -*- coding: utf-8 -*-
import aiohttp
from config import CAT_API_URL


async def get_random_cat_url() -> str:
    """
    Возвращает прямую ссылку на случайную картинку котика с cataas.com.
    Ключи/авторизация не нужны — обычный публичный GET.
    """
    # cataas.com/cat отдаёт бинарник картинки напрямую по этому же URL,
    # поэтому просто добавляем случайный параметр, чтобы не словить кэш
    import random
    return f"{CAT_API_URL}?rand={random.randint(1, 999999)}"
