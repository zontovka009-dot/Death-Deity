# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

import database as db
import keyboards as kb
import texts as t
import utils
from states import AnketaForm, SupportForm, ProfileForm
from config import ADMIN_IDS, MODERATION_GROUP_ID

router = Router()


# ==================== ХЕЛПЕРЫ ====================

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


async def check_ban(message: Message) -> str:
    user = db.get_user(message.from_user.id)
    if not user:
        return "none"
    return user[3]  # ban_status


async def notify_admins(bot, entity_type: str, entity_id: int, header: str, body: str, kb_builder):
    """
    Шлёт персональное уведомление каждому админу в личку бота, с теми же
    кнопками действия, что и в карточке. Регистрирует каждое сообщение
    как 'dm'-карточку — когда кто-то из админов решит вопрос, все эти
    уведомления удалятся у всех разом.
    """
    for admin_id in ADMIN_IDS:
        try:
            sent = await bot.send_message(admin_id, f"{header}\n\n{body}", reply_markup=kb_builder(entity_id))
            db.register_card(entity_type, entity_id, admin_id, sent.message_id, "dm")
        except Exception:
            pass  # админ мог не запускать бота лично — молча пропускаем


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
        await utils.replace_message(message, state, t.ADMIN_GREETING, kb.admin_main_menu())
        return
    ban_status = await check_ban(message)
    if ban_status == "soft":
        await utils.replace_message(message, state, t.GREETING, kb.appeal_only_menu())
    else:
        await utils.replace_message(message, state, t.GREETING, kb.user_main_menu())


# ==================== АНКЕТА (шаблон админа + текст + фото) ====================

@router.message(F.text == "📝 Отправить анкету")
async def start_anketa(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status in ("soft", "hard"):
        await message.answer(t.BANNED_SOFT if ban_status == "soft" else t.BANNED_HARD)
        return

    if db.get_setting("recruitment_open") != "1":
        await message.answer(t.RECRUITMENT_CLOSED, reply_markup=kb.user_main_menu())
        return

    template = db.get_setting("anketa_template") or ""
    photo_id = db.get_setting("anketa_photo")

    await state.set_state(AnketaForm.filling)
    if photo_id:
        sent = await message.answer_photo(photo_id, caption=template, reply_markup=kb.back_menu())
    else:
        sent = await message.answer(template, reply_markup=kb.back_menu())
    await state.update_data(_last_bot_msg=sent.message_id)


@router.message(AnketaForm.filling)
async def anketa_filling(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.GREETING, kb.user_main_menu())
        return
    await state.update_data(answer_text=message.text, app_photo=None)
    await state.set_state(AnketaForm.photo)
    await utils.replace_message(message, state, t.ASK_PHOTO_FOR_ANKETA, kb.skip_menu())


@router.message(AnketaForm.photo, F.photo)
async def anketa_photo_given(message: Message, state: FSMContext):
    await state.update_data(app_photo=message.photo[-1].file_id)
    await show_anketa_preview(message, state)


@router.message(AnketaForm.photo, F.text == "⏭ Пропустить")
async def anketa_photo_skip(message: Message, state: FSMContext):
    await show_anketa_preview(message, state)


@router.message(AnketaForm.photo, F.text == "⬅️ Назад")
async def anketa_photo_back(message: Message, state: FSMContext):
    await state.set_state(AnketaForm.filling)
    template = db.get_setting("anketa_template") or ""
    await utils.replace_message(message, state, template, kb.back_menu())


async def show_anketa_preview(message: Message, state: FSMContext):
    data = await state.get_data()
    await state.set_state(AnketaForm.confirm)
    preview = f"{t.ANKETA_READY}\n\n{utils.esc(data.get('answer_text'))}"
    photo = data.get("app_photo")
    if photo:
        await utils.replace_message_photo(message, state, photo, preview, kb.confirm_menu())
    else:
        await utils.replace_message(message, state, preview, kb.confirm_menu())


@router.message(AnketaForm.confirm)
async def anketa_confirm(message: Message, state: FSMContext):
    if message.text == "✏️ Редактировать":
        await state.set_state(AnketaForm.filling)
        template = db.get_setting("anketa_template") or ""
        await utils.replace_message(message, state, template, kb.back_menu())
        return

    if message.text == "✅ Отправить":
        data = await state.get_data()
        answer_text = data.get("answer_text", "")
        photo_id = data.get("app_photo")
        app_id = db.create_application(message.from_user.id, answer_text, photo_id)

        header = f"📥 Новая анкета #{app_id}"
        body = (
            f"От: {utils.esc(message.from_user.full_name)} (@{message.from_user.username})\n\n"
            f"{utils.esc(answer_text)}"
        )
        card_kb = kb.application_card_kb

        # карточка в группу модерации
        try:
            if photo_id:
                sent = await message.bot.send_photo(
                    MODERATION_GROUP_ID, photo_id, caption=f"{header}\n\n{body}", reply_markup=card_kb(app_id)
                )
            else:
                sent = await message.bot.send_message(
                    MODERATION_GROUP_ID, f"{header}\n\n{body}", reply_markup=card_kb(app_id)
                )
            db.register_card("application", app_id, MODERATION_GROUP_ID, sent.message_id, "group")
        except Exception:
            pass

        # персональные уведомления каждому админу в личку
        await notify_admins(
            message.bot, "application", app_id, t.NOTIF_NEW_APPLICATION, body, card_kb
        )

        await state.clear()
        await message.answer(t.ANKETA_SENT_TO_USER, reply_markup=kb.user_main_menu())
        return

    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.GREETING, kb.user_main_menu())


# ==================== ПОДДЕРЖКА ====================

@router.message(F.text == "🆘 Поддержка")
async def support_start(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status == "hard":
        await message.answer(t.BANNED_HARD)
        return
    await utils.replace_message(message, state, t.SUPPORT_CHOOSE_TYPE, kb.support_menu())


@router.message(F.text == "⚖️ Аппеляция наказания")
async def appeal_start(message: Message, state: FSMContext):
    await state.update_data(ticket_type="appeal", intro=t.APPEAL_INTRO, confirm_text=t.APPEAL_CONFIRM, sent_text=t.APPEAL_SENT)
    await state.set_state(SupportForm.writing_text)
    await utils.replace_message(message, state, t.APPEAL_INTRO, kb.back_menu())


@router.message(F.text == "📢 Пожаловаться")
async def complaint_start(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status in ("soft", "hard"):
        await message.answer(t.BANNED_SOFT if ban_status == "soft" else t.BANNED_HARD)
        return
    await state.update_data(ticket_type="complaint", intro=t.COMPLAINT_INTRO, confirm_text=t.COMPLAINT_CONFIRM, sent_text=t.COMPLAINT_SENT)
    await state.set_state(SupportForm.writing_text)
    await utils.replace_message(message, state, t.COMPLAINT_INTRO, kb.back_menu())


@router.message(F.text == "❓ Другое")
async def other_start(message: Message, state: FSMContext):
    ban_status = await check_ban(message)
    if ban_status in ("soft", "hard"):
        await message.answer(t.BANNED_SOFT if ban_status == "soft" else t.BANNED_HARD)
        return
    await state.update_data(ticket_type="other", intro=t.OTHER_INTRO, confirm_text=t.OTHER_CONFIRM, sent_text=t.OTHER_SENT)
    await state.set_state(SupportForm.writing_text)
    await utils.replace_message(message, state, t.OTHER_INTRO, kb.back_menu())


@router.message(SupportForm.writing_text)
async def support_writing(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.GREETING, kb.user_main_menu())
        return
    await state.update_data(ticket_text=message.text)
    await state.set_state(SupportForm.confirm)
    data = await state.get_data()
    await utils.replace_message(message, state, data["confirm_text"], kb.confirm_menu())


@router.message(SupportForm.confirm)
async def support_confirm(message: Message, state: FSMContext):
    data = await state.get_data()

    if message.text == "✏️ Редактировать":
        await state.set_state(SupportForm.writing_text)
        await utils.replace_message(message, state, data["intro"], kb.back_menu())
        return

    if message.text == "✅ Отправить":
        ticket_id = db.create_ticket(message.from_user.id, data["ticket_type"], data["ticket_text"])
        type_labels = {"appeal": "⚖️ Аппеляция", "complaint": "📢 Жалоба", "other": "❓ Другое обращение"}
        notif_labels = {
            "appeal": t.NOTIF_NEW_APPEAL,
            "complaint": t.NOTIF_NEW_COMPLAINT,
            "other": t.NOTIF_NEW_OTHER,
        }
        body = (
            f"{type_labels.get(data['ticket_type'])} #{ticket_id}\n\n"
            f"От: {utils.esc(message.from_user.full_name)} (@{message.from_user.username})\n\n"
            f"{utils.esc(data['ticket_text'])}"
        )

        try:
            sent = await message.bot.send_message(
                MODERATION_GROUP_ID, body, reply_markup=kb.ticket_card_kb(ticket_id)
            )
            db.register_card("ticket", ticket_id, MODERATION_GROUP_ID, sent.message_id, "group")
        except Exception:
            pass

        await notify_admins(
            message.bot, "ticket", ticket_id, notif_labels.get(data["ticket_type"], "❓ Обращение"),
            body, kb.ticket_card_kb
        )

        await state.clear()
        ban_status = await check_ban(message)
        markup = kb.appeal_only_menu() if ban_status == "soft" else kb.user_main_menu()
        await message.answer(data["sent_text"], reply_markup=markup)
        return

    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.GREETING, kb.user_main_menu())


# ==================== ПРОФИЛЬ ====================

async def show_own_profile(message: Message, state: FSMContext):
    user_row = db.get_user(message.from_user.id)
    profile_row = db.get_profile(message.from_user.id)
    text, photo = utils.format_profile_text(user_row, profile_row)
    if photo:
        await utils.replace_message_photo(message, state, photo, text, kb.profile_menu())
    else:
        await utils.replace_message(message, state, text, kb.profile_menu())


@router.message(F.text == "📇 Профиль")
async def profile_open(message: Message, state: FSMContext):
    await state.clear()
    await show_own_profile(message, state)


@router.message(F.text == "✏️ Редактировать")
async def profile_edit_start(message: Message, state: FSMContext):
    await state.set_state(ProfileForm.waiting_bio)
    await utils.replace_message(message, state, "Расскажи немного о себе:", kb.back_menu())


@router.message(ProfileForm.waiting_bio)
async def profile_edit_bio(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await show_own_profile(message, state)
        return
    db.set_profile_bio(message.from_user.id, message.text)
    await state.set_state(ProfileForm.waiting_photo)
    await utils.replace_message(message, state, t.ASK_PHOTO_FOR_ANKETA, kb.skip_menu())


@router.message(ProfileForm.waiting_photo, F.photo)
async def profile_edit_photo(message: Message, state: FSMContext):
    db.set_profile_photo(message.from_user.id, message.photo[-1].file_id)
    await state.clear()
    await show_own_profile(message, state)


@router.message(ProfileForm.waiting_photo, F.text.in_(["⏭ Пропустить", "⬅️ Назад"]))
async def profile_edit_photo_skip(message: Message, state: FSMContext):
    await state.clear()
    await show_own_profile(message, state)


# ==================== ОТВЕТ ЮЗЕРА АДМИНУ В ЛИЧНОМ ТРЕДЕ ====================

@router.message(F.text, ~F.text.startswith("/"))
async def fallback_user_message(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is not None:
        return
    if is_admin(message.from_user.id):
        return

    last_ticket = db.get_last_ticket_by_user(message.from_user.id)
    if last_ticket and last_ticket[4] == "answered":
        text_for_group = (
            f"↩️ Ответ пользователя по обращению #{last_ticket[0]}\n\n"
            f"От: {utils.esc(message.from_user.full_name)} (@{message.from_user.username})\n\n"
            f"{utils.esc(message.text)}"
        )
        await message.bot.send_message(MODERATION_GROUP_ID, text_for_group)
        await message.answer("Передал администрации, жди ответа! 🕊")
