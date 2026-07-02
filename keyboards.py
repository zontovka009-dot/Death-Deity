# -*- coding: utf-8 -*-
from aiogram.types import (
    ReplyKeyboardMarkup,
    KeyboardButton,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
import database as db


# ==================== USER REPLY-КЛАВИАТУРЫ ====================

def user_main_menu():
    kb = [
        [KeyboardButton(text="📝 Отправить анкету"), KeyboardButton(text="🆘 Поддержка")],
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


def roles_menu():
    roles = db.get_free_roles()
    kb = []
    for r in roles:
        kb.append([KeyboardButton(text=r[1])])
    kb.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def back_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="⬅️ Назад")]], resize_keyboard=True)


def appeal_only_menu():
    # Меню для мягко забаненных — доступна только аппеляция
    kb = [[KeyboardButton(text="⚖️ Аппеляция наказания")]]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ==================== ADMIN REPLY-КЛАВИАТУРЫ ====================

def admin_main_menu():
    kb = [
        [KeyboardButton(text="📥 Посмотреть заявки"), KeyboardButton(text="🚫 Чёрный список")],
        [KeyboardButton(text="📨 Посмотреть обращения"), KeyboardButton(text="👑 Список админов")],
        [KeyboardButton(text="🗂 Анкета заявок"), KeyboardButton(text="🙀 Если рвёт крышу")],
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
        [KeyboardButton(text="🎭 Управление ролями")],
        [KeyboardButton(text=toggle_text)],
        [KeyboardButton(text="⬅️ Назад")],
    ]
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


def admin_roles_menu():
    roles = db.get_all_roles()
    kb = []
    for r in roles:
        status = "🟢" if r[2] == 1 else "🔴"
        kb.append([KeyboardButton(text=f"{status} {r[1]}")])
    kb.append([KeyboardButton(text="➕ Добавить роль")])
    kb.append([KeyboardButton(text="⬅️ Назад")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)


# ==================== INLINE-КЛАВИАТУРЫ (карточки заявок/обращений) ====================

def application_card_kb(app_id: int, pending=True):
    if pending:
        kb = [
            [
                InlineKeyboardButton(text="✅ Принять", callback_data=f"app_accept_{app_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"app_reject_{app_id}"),
            ],
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"app_block_{app_id}")],
        ]
    else:
        kb = [[InlineKeyboardButton(text="👤 Профиль", callback_data=f"app_profile_{app_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def ticket_card_kb(ticket_id: int, pending=True):
    if pending:
        kb = [
            [
                InlineKeyboardButton(text="💬 Ответить", callback_data=f"tk_reply_{ticket_id}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"tk_reject_{ticket_id}"),
            ],
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"tk_block_{ticket_id}")],
        ]
    else:
        kb = [[InlineKeyboardButton(text="👤 Профиль", callback_data=f"tk_profile_{ticket_id}")]]
    return InlineKeyboardMarkup(inline_keyboard=kb)


def profile_kb(user_id: int, banned: bool):
    ban_btn = (
        InlineKeyboardButton(text="✅ Разбанить", callback_data=f"unban_{user_id}")
        if banned
        else InlineKeyboardButton(text="🚫 Забанить", callback_data=f"ban_{user_id}")
    )
    kb = [
        [InlineKeyboardButton(text="✍️ Написать", callback_data=f"write_{user_id}")],
        [ban_btn],
    ]
    return InlineKeyboardMarkup(inline_keyboard=kb)
