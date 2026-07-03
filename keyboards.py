# -*- coding: utf-8 -*-
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)


# ==================== USER REPLY-КЛАВИАТУРЫ ====================

def user_main_menu():
    kb = [
        [KeyboardButton(text="📝 Отправить анкету"), KeyboardButton(text="🆘 Поддержка")],
        [KeyboardButton(text="📇 Профиль")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def support_menu():
    kb = [
        [KeyboardButton(text="⚖️ Аппеляция наказания")],
        [KeyboardButton(text="📢 Пожаловаться")],
        [KeyboardButton(text="❓ Другое")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def confirm_menu():
    kb = [
        [KeyboardButton(text="✅ Отправить"), KeyboardButton(text="✏️ Редактировать")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def skip_menu():
    kb = [[KeyboardButton(text="⏭ Пропустить")], [KeyboardButton(text="⬅️ Назад")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def back_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)


def appeal_only_menu():
    kb = [[KeyboardButton(text="⚖️ Аппеляция наказания")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def profile_menu():
    kb = [[KeyboardButton(text="✏️ Редактировать")], [KeyboardButton(text="⬅️ Назад")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ==================== ADMIN REPLY-КЛАВИАТУРЫ ====================

def admin_main_menu():
    kb = [
        [KeyboardButton(text="📥 Посмотреть заявки"), KeyboardButton(text="🚫 Чёрный список")],
        [KeyboardButton(text="📨 Посмотреть обращения"), KeyboardButton(text="👑 Список админов")],
        [KeyboardButton(text="🗂 Анкета заявок"), KeyboardButton(text="🙀 Если рвёт крышу")],
        [KeyboardButton(text="🔍 Поиск"), KeyboardButton(text="📇 Профиль")],
        [KeyboardButton(text="🔗 Ссылка чата")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_applications_menu():
    kb = [
        [KeyboardButton(text="🟢 Активные заявки"), KeyboardButton(text="✔️ Проверенные")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_tickets_menu():
    kb = [
        [KeyboardButton(text="🟢 Активные обращения"), KeyboardButton(text="✔️ Обработанные")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_anketa_settings_menu(is_open: bool):
    toggle_text = "🔴 Закрыть набор" if is_open else "🟢 Открыть набор"
    kb = [
        [KeyboardButton(text="✏️ Изменить текст анкеты")],
        [KeyboardButton(text="🖼 Прикрепить/сменить фото")],
        [KeyboardButton(text=toggle_text)],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_profile_result_menu(banned: bool):
    ban_text = "✅ Разбанить" if banned else "🚫 Заблокировать"
    kb = [
        [KeyboardButton(text=ban_text)],
        [KeyboardButton(text="✍️ Написать")],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ==================== INLINE: списки заявок/обращений (компактно) ====================

def entity_list_kb(items, prefix: str):
    """
    items: список (id, короткая_метка)
    prefix: 'appview' / 'tkview'
    Собирает кнопки по 3 в ряд, чтобы длинный список не растягивал экран.
    """
    buttons = [
        InlineKeyboardButton(text=label, callback_data=f"{prefix}_{item_id}")
        for item_id, label in items
    ]
    rows = [buttons[i:i + 3] for i in range(0, len(buttons), 3)]
    return InlineKeyboardMarkup(inline_keyboard=rows)


def application_detail_kb(app_id: int, status: str):
    rows = []
    if status == "pending":
        rows.append([
            InlineKeyboardButton(text="✅ Принять", callback_data=f"app_accept_{app_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"app_reject_{app_id}"),
        ])
        rows.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"app_block_{app_id}")])
    rows.append([InlineKeyboardButton(text="◀️ К списку", callback_data=f"applist_{status}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def ticket_detail_kb(ticket_id: int, status: str):
    rows = []
    if status == "pending":
        rows.append([
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"tk_reply_{ticket_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"tk_reject_{ticket_id}"),
        ])
        rows.append([InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"tk_block_{ticket_id}")])
    rows.append([InlineKeyboardButton(text="◀️ К списку", callback_data=f"tklist_{status}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


# карточка, которая летит в группу модерации / в личку каждому админу при подаче
def application_card_kb(app_id: int):
    kb = [
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"app_accept_{app_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"app_reject_{app_id}"),
        ],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"app_block_{app_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def ticket_card_kb(ticket_id: int):
    kb = [
        [
            InlineKeyboardButton(text="💬 Ответить", callback_data=f"tk_reply_{ticket_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"tk_reject_{ticket_id}"),
        ],
        [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"tk_block_{ticket_id}")],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)


# кнопка "Написать" на посте с одобренной анкетой в чате новичков
def write_button_kb(user_id: int):
    kb = [[InlineKeyboardButton(text="✍️ Написать", callback_data=f"write_{user_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def invite_kb(user_id: int):
    kb = [[
        InlineKeyboardButton(text="✅ Да", callback_data=f"invite_yes_{user_id}"),
        InlineKeyboardButton(text="❌ Нет", callback_data="invite_no"),
    ]]
    return InlineKeyboardMarkup(inline_keyboard=kb)
