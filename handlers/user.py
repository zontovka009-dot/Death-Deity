# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

import database as db
import keyboards as kb
import texts as t
from states import AnketaForm, SupportForm
from config import ADMIN_IDS, MODERATION_GROUP_ID

router = Router()


# ==================== ХЕЛПЕРЫ ====================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_ban(message: Message) -> str:
    """Возвращает 'none' / 'soft' / 'hard' статус бана юзера."""
    user = db.get_user(message.from_user.id)
    if not user:
        return "none"
    return user[3]  # ban_status


# ==================== /START ====================

@router.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    db.add_user(message.from_user.id, message.from_user.username, message.from_user.full_name)

    if is_admin(message.from_user.id):
        await message.answer(t.ADMIN_GREETING, reply_markup=kb.admin_main_menu())
        return

    ban_status = await check_ban(message)
    if ban_status == "hard":
        await message.answer(t.BANNED_HARD)
        return
    if ban_status == "soft":
        await message.answer(t.GREETING, reply_markup=kb.appeal_only_menu())
        return

    await message.answer(t.GREETING, reply_markup=kb.user_main_menu())


@router.message(F.text == "⬅️ Назад")
async def go_back_to_main(message: Message, state: FSMContext):
    await state.clear()
    if is_admin(message.from_user.id):
        await message.answer(t.ADMIN_GREETING, reply_markup=kb.admin_main_menu())
        return
    ban_status = await check_ban(message)
    if ban_status == "soft":
        await message.answer(t.GREETING, reply_markup=kb.appeal_only_menu())
    else:
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())


# ==================== АНКЕТА ====================

@router.message(F.text == "📝 Отправить анкету")
async def start_anketa(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status in ("soft", "hard"):
        await message.answer(t.BANNED_SOFT if ban_status == "soft" else t.BANNED_HARD)
        return

    if db.get_setting("recruitment_open") != "1":
        await message.answer(t.RECRUITMENT_CLOSED, reply_markup=kb.user_main_menu())
        return

    await state.set_state(AnketaForm.birth_date)
    await message.answer(t.ANKETA_INTRO, reply_markup=kb.back_menu())


@router.message(AnketaForm.birth_date)
async def anketa_birth_date(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())
        return
    await state.update_data(birth_date=message.text)
    await state.set_state(AnketaForm.role)
    await message.answer(t.ANKETA_ASK_ROLE, reply_markup=kb.roles_menu())


@router.message(AnketaForm.role)
async def anketa_role(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())
        return
    await state.update_data(role=message.text)
    await state.set_state(AnketaForm.about)
    await message.answer(t.ANKETA_ASK_ABOUT, reply_markup=kb.back_menu())


@router.message(AnketaForm.about)
async def anketa_about(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())
        return
    await state.update_data(about=message.text)
    await state.set_state(AnketaForm.confirm)
    await show_anketa_preview(message, state)


async def show_anketa_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    preview = (
        f"{t.ANKETA_READY}\n\n"
        f"📅 Дата рождения: {data.get('birth_date')}\n"
        f"🎭 Роль: {data.get('role')}\n"
        f"📝 О себе: {data.get('about')}"
    )
    await message.answer(preview, reply_markup=kb.confirm_menu())


@router.message(AnketaForm.confirm)
async def anketa_confirm(message: Message, state: FSMContext):
    if message.text == "✏️ Редактировать":
        await state.set_state(AnketaForm.birth_date)
        await message.answer(t.ANKETA_INTRO, reply_markup=kb.back_menu())
        return

    if message.text == "✅ Отправить":
        data = await state.get_data()
        app_id = db.create_application(
            message.from_user.id, data.get("birth_date"), data.get("role"), data.get("about")
        )
        text_for_group = (
            f"📥 Новая анкета #{app_id}\n\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username})\n"
            f"📅 Дата рождения: {data.get('birth_date')}\n"
            f"🎭 Роль: {data.get('role')}\n"
            f"📝 О себе: {data.get('about')}"
        )
        sent = await message.bot.send_message(
            MODERATION_GROUP_ID, text_for_group, reply_markup=kb.application_card_kb(app_id)
        )
        db.set_application_group_msg(app_id, sent.message_id)

        await state.clear()
        await message.answer(t.ANKETA_SENT_TO_USER, reply_markup=kb.user_main_menu())
        return

    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())


# ==================== ПОДДЕРЖКА ====================

@router.message(F.text == "🆘 Поддержка")
async def support_start(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status == "hard":
        await message.answer(t.BANNED_HARD)
        return
    await message.answer(t.SUPPORT_CHOOSE_TYPE, reply_markup=kb.support_menu())


@router.message(F.text == "⚖️ Аппеляция наказания")
async def appeal_start(message: Message, state: FSMContext):
    await state.update_data(ticket_type="appeal", intro=t.APPEAL_INTRO, confirm_text=t.APPEAL_CONFIRM, sent_text=t.APPEAL_SENT)
    await state.set_state(SupportForm.writing_text)
    await message.answer(t.APPEAL_INTRO, reply_markup=kb.back_menu())


@router.message(F.text == "📢 Пожаловаться")
async def complaint_start(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status in ("soft", "hard"):
        await message.answer(t.BANNED_SOFT if ban_status == "soft" else t.BANNED_HARD)
        return
    await state.update_data(ticket_type="complaint", intro=t.COMPLAINT_INTRO, confirm_text=t.COMPLAINT_CONFIRM, sent_text=t.COMPLAINT_SENT)
    await state.set_state(SupportForm.writing_text)
    await message.answer(t.COMPLAINT_INTRO, reply_markup=kb.back_menu())


@router.message(F.text == "❓ Другое")
async def other_start(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status in ("soft", "hard"):
        await message.answer(t.BANNED_SOFT if ban_status == "soft" else t.BANNED_HARD)
        return
    await state.update_data(ticket_type="other", intro=t.OTHER_INTRO, confirm_text=t.OTHER_CONFIRM, sent_text=t.OTHER_SENT)
    await state.set_state(SupportForm.writing_text)
    await message.answer(t.OTHER_INTRO, reply_markup=kb.back_menu())


@router.message(SupportForm.writing_text)
async def support_writing(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())
        return
    await state.update_data(ticket_text=message.text)
    await state.set_state(SupportForm.confirm)
    data = await state.get_data()
    await message.answer(data["confirm_text"], reply_markup=kb.confirm_menu())


@router.message(SupportForm.confirm)
async def support_confirm(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.text == "✏️ Редактировать":
        await state.set_state(SupportForm.writing_text)
        await message.answer(data["intro"], reply_markup=kb.back_menu())
        return

    if message.text == "✅ Отправить":
        ticket_id = db.create_ticket(message.from_user.id, data["ticket_type"], data["ticket_text"])
        type_labels = {"appeal": "⚖️ Аппеляция", "complaint": "📢 Жалоба", "other": "❓ Другое обращение"}
        text_for_group = (
            f"📨 {type_labels.get(data['ticket_type'])} #{ticket_id}\n\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username})\n\n"
            f"{data['ticket_text']}"
        )
        sent = await message.bot.send_message(
            MODERATION_GROUP_ID, text_for_group, reply_markup=kb.ticket_card_kb(ticket_id)
        )
        db.set_ticket_group_msg(ticket_id, sent.message_id)

        await state.clear()
        ban_status = await check_ban(message)
        markup = kb.appeal_only_menu() if ban_status == "soft" else kb.user_main_menu()
        await message.answer(data["sent_text"], reply_markup=markup)
        return

    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.GREETING, reply_markup=kb.user_main_menu())


# ==================== ОТВЕТ ЮЗЕРА АДМИНУ В ЛИЧНОМ ТРЕДЕ ====================
# Если у юзера есть последнее обращение со статусом "answered" и он пишет текстом
# вне какого-либо состояния — пересылаем это как продолжение переписки админам.

@router.message(F.text, ~F.text.startswith("/"))
async def fallback_user_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return  # уже обрабатывается другим хендлером
    if is_admin(message.from_user.id):
        return

    last_ticket = db.get_last_ticket_by_user(message.from_user.id)
    if last_ticket and last_ticket[4] == "answered":
        text_for_group = (
            f"↩️ Ответ пользователя по обращению #{last_ticket[0]}\n\n"
            f"От: {message.from_user.full_name} (@{message.from_user.username})\n\n"
            f"{message.text}"
        )
        await message.bot.send_message(MODERATION_GROUP_ID, text_for_group)
        await message.answer("Ваш ответ передан администрации, ожидайте!")
