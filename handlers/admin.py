# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile, BufferedInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters import Command

import database as db
import keyboards as kb
import texts as t
import utils
from states import AdminWriteToUser, AdminEditTemplate, AdminManageRoles
from config import ADMIN_IDS, NEWCOMERS_GROUP_ID

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


# фильтр: все хендлеры этого роутера только для админов
@router.message.middleware()
async def admin_only_middleware(handler, event: Message, data):
    if not is_admin(event.from_user.id):
        return
    return await handler(event, data)


@router.callback_query.middleware()
async def admin_only_cb_middleware(handler, event: CallbackQuery, data):
    if not is_admin(event.from_user.id):
        return
    return await handler(event, data)


# ==================== ЗАЯВКИ ====================

@router.message(F.text == "📥 Посмотреть заявки")
async def view_applications_menu(message: Message):
    await message.answer("Что вас интересует?", reply_markup=kb.admin_applications_menu())


@router.message(F.text == "🟢 Активные заявки")
async def view_active_applications(message: Message):
    apps = db.get_applications_by_status("pending")
    if not apps:
        await message.answer(t.NOTHING_FOUND)
        return
    for app in apps:
        text = (
            f"📥 Анкета #{app[0]}\n"
            f"📅 Дата рождения: {app[2]}\n"
            f"🎭 Роль: {app[3]}\n"
            f"📝 О себе: {app[4]}"
        )
        await message.answer(text, reply_markup=kb.application_card_kb(app[0]))


@router.message(F.text == "✔️ Проверенные")
async def view_processed_applications(message: Message):
    apps = db.get_applications_processed()
    if not apps:
        await message.answer(t.NOTHING_FOUND)
        return
    for app in apps:
        status_label = {"approved": "✅ Одобрена", "rejected": "❌ Отклонена"}.get(app[5], app[5])
        text = f"📄 Анкета #{app[0]} — {status_label}\n🎭 Роль: {app[3]}"
        await message.answer(text, reply_markup=kb.application_card_kb(app[0], pending=False))


@router.callback_query(F.data.startswith("app_accept_"))
async def app_accept(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не найдено", show_alert=True)
        return
    db.set_application_status(app_id, "approved", call.from_user.id)
    await call.message.edit_text(call.message.text + "\n\n✅ ОДОБРЕНА", reply_markup=None)
    await call.bot.send_message(app[1], t.ANKETA_APPROVED_USER)

    newcomer_text = (
        f"👋 Новый участник!\n\n"
        f"🎭 Роль: {app[3]}\n"
        f"📝 О себе: {app[4]}"
    )
    await call.bot.send_message(NEWCOMERS_GROUP_ID, newcomer_text)
    await call.answer("Принято")


@router.callback_query(F.data.startswith("app_reject_"))
async def app_reject(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не найдено", show_alert=True)
        return
    db.set_application_status(app_id, "rejected", call.from_user.id)
    await call.message.edit_text(call.message.text + "\n\n❌ ОТКЛОНЕНА", reply_markup=None)
    await call.bot.send_message(app[1], t.ANKETA_REJECTED_USER)
    await call.answer("Отклонено")


@router.callback_query(F.data.startswith("app_block_"))
async def app_block(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не найдено", show_alert=True)
        return
    db.set_application_status(app_id, "rejected", call.from_user.id)
    db.set_ban_status(app[1], "soft")
    await call.message.edit_text(call.message.text + "\n\n🚫 ЗАБЛОКИРОВАН", reply_markup=None)
    await call.bot.send_message(app[1], t.BANNED_SOFT)
    await call.answer("Заблокирован")


@router.callback_query(F.data.startswith("app_profile_"))
async def app_profile(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не найдено", show_alert=True)
        return
    user = db.get_user(app[1])
    banned = user and user[3] != "none"
    text = f"👤 Профиль по анкете #{app_id}\nID: {app[1]}\nСтатус бана: {user[3] if user else 'none'}"
    await call.message.answer(text, reply_markup=kb.profile_kb(app[1], banned))
    await call.answer()


# ==================== ОБРАЩЕНИЯ (ТИКЕТЫ) ====================

@router.message(F.text == "📨 Посмотреть обращения")
async def view_tickets_menu(message: Message):
    await message.answer("Что вас интересует?", reply_markup=kb.admin_tickets_menu())


@router.message(F.text == "🟢 Активные обращения")
async def view_active_tickets(message: Message):
    tickets = db.get_tickets_by_status("pending")
    if not tickets:
        await message.answer(t.NOTHING_FOUND)
        return
    type_labels = {"appeal": "⚖️ Аппеляция", "complaint": "📢 Жалоба", "other": "❓ Другое"}
    for tk in tickets:
        text = f"📨 {type_labels.get(tk[2], tk[2])} #{tk[0]}\n\n{tk[3]}"
        await message.answer(text, reply_markup=kb.ticket_card_kb(tk[0]))


@router.message(F.text == "✔️ Обработанные")
async def view_processed_tickets(message: Message):
    tickets = db.get_tickets_processed()
    if not tickets:
        await message.answer(t.NOTHING_FOUND)
        return
    status_labels = {"answered": "💬 Отвечено", "rejected": "❌ Отклонено", "banned": "🚫 Забанен"}
    for tk in tickets:
        text = f"📄 Обращение #{tk[0]} — {status_labels.get(tk[4], tk[4])}"
        await message.answer(text, reply_markup=kb.ticket_card_kb(tk[0], pending=False))


@router.callback_query(F.data.startswith("tk_reply_"))
async def tk_reply(call: CallbackQuery, state: FSMContext):
    ticket_id = int(call.data.split("_")[-1])
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminWriteToUser.waiting_text)
    await call.message.answer(f"Напишите ответ по обращению #{ticket_id}:")
    await call.answer()


@router.callback_query(F.data.startswith("tk_reject_"))
async def tk_reject(call: CallbackQuery):
    ticket_id = int(call.data.split("_")[-1])
    tk = db.get_ticket(ticket_id)
    if not tk:
        await call.answer("Не найдено", show_alert=True)
        return
    db.set_ticket_status(ticket_id, "rejected")
    await call.message.edit_text(call.message.text + "\n\n❌ ОТКЛОНЕНО", reply_markup=None)
    await call.bot.send_message(tk[1], "По вашему обращению принято решение: отклонено.")
    await call.answer("Отклонено")


@router.callback_query(F.data.startswith("tk_block_"))
async def tk_block(call: CallbackQuery):
    ticket_id = int(call.data.split("_")[-1])
    tk = db.get_ticket(ticket_id)
    if not tk:
        await call.answer("Не найдено", show_alert=True)
        return
    db.set_ticket_status(ticket_id, "banned")
    # если бан пришёл именно через аппеляцию — это жёсткий бан (полная блокировка)
    ban_type = "hard" if tk[2] == "appeal" else "soft"
    db.set_ban_status(tk[1], ban_type)
    await call.message.edit_text(call.message.text + "\n\n🚫 ЗАБЛОКИРОВАН", reply_markup=None)
    await call.bot.send_message(tk[1], t.BANNED_HARD if ban_type == "hard" else t.BANNED_SOFT)
    await call.answer("Заблокирован")


@router.callback_query(F.data.startswith("tk_profile_"))
async def tk_profile(call: CallbackQuery):
    ticket_id = int(call.data.split("_")[-1])
    tk = db.get_ticket(ticket_id)
    if not tk:
        await call.answer("Не найдено", show_alert=True)
        return
    user = db.get_user(tk[1])
    banned = user and user[3] != "none"
    text = f"👤 Профиль по обращению #{ticket_id}\nID: {tk[1]}\nСтатус бана: {user[3] if user else 'none'}"
    await call.message.answer(text, reply_markup=kb.profile_kb(tk[1], banned))
    await call.answer()


@router.message(AdminWriteToUser.waiting_text)
async def admin_write_text(message: Message, state: FSMContext):
    data = await state.get_data()

    # Вариант 1: ответ по конкретному обращению (тикету)
    ticket_id = data.get("ticket_id")
    if ticket_id:
        tk = db.get_ticket(ticket_id)
        if tk:
            db.set_ticket_status(ticket_id, "answered", message.text)
            await message.bot.send_message(
                tk[1], f"💬 Ответ администрации по обращению #{ticket_id}:\n\n{message.text}"
            )
            await message.answer("Ответ отправлен пользователю.", reply_markup=kb.admin_main_menu())
        await state.clear()
        return

    # Вариант 2: прямое сообщение юзеру из профиля
    direct_user = data.get("direct_write_user")
    if direct_user:
        await message.bot.send_message(direct_user, f"💬 Сообщение от администрации:\n\n{message.text}")
        await message.answer("Сообщение отправлено.", reply_markup=kb.admin_main_menu())
        await state.clear()


# ==================== ПРОФИЛЬ: НАПИСАТЬ / БАН / РАЗБАН ====================

@router.callback_query(F.data.startswith("write_"))
async def profile_write(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split("_")[-1])
    await state.update_data(direct_write_user=user_id)
    await state.set_state(AdminWriteToUser.waiting_text)
    await call.message.answer(f"Напишите сообщение пользователю {user_id}:")
    await call.answer()


@router.callback_query(F.data.startswith("ban_"))
async def profile_ban(call: CallbackQuery):
    user_id = int(call.data.split("_")[-1])
    db.set_ban_status(user_id, "hard")
    await call.bot.send_message(user_id, t.BANNED_HARD)
    await call.message.edit_reply_markup(reply_markup=kb.profile_kb(user_id, True))
    await call.answer("Заблокирован")


@router.callback_query(F.data.startswith("unban_"))
async def profile_unban(call: CallbackQuery):
    user_id = int(call.data.split("_")[-1])
    db.set_ban_status(user_id, "none")
    await call.bot.send_message(user_id, "Вы были разблокированы, снова добро пожаловать!")
    await call.message.edit_reply_markup(reply_markup=kb.profile_kb(user_id, False))
    await call.answer("Разбанен")


# ==================== ЧЁРНЫЙ СПИСОК ====================

@router.message(F.text == "🚫 Чёрный список")
async def view_blacklist(message: Message):
    users = db.get_banned_users()
    if not users:
        await message.answer(t.NOTHING_FOUND)
        return
    for u in users:
        text = f"🚫 {u[2]} (@{u[1]})\nID: {u[0]}\nСтатус: {u[3]}"
        await message.answer(text, reply_markup=kb.profile_kb(u[0], True))


# ==================== СПИСОК АДМИНОВ ====================

@router.message(F.text == "👑 Список админов")
async def view_admins(message: Message):
    text = "👑 Администрация бота:\n\n" + "\n".join(str(a) for a in ADMIN_IDS)
    await message.answer(text, reply_markup=kb.back_menu())


# ==================== АНКЕТА ЗАЯВОК (НАСТРОЙКИ) ====================

@router.message(F.text == "🗂 Анкета заявок")
async def anketa_settings(message: Message):
    is_open = db.get_setting("recruitment_open") == "1"
    template = db.get_setting("anketa_template") or "(пусто)"
    await message.answer(
        f"Текущий шаблон анкеты:\n\n{template}\n\nНабор: {'открыт 🟢' if is_open else 'закрыт 🔴'}",
        reply_markup=kb.admin_anketa_settings_menu(is_open),
    )


@router.message(F.text == "✏️ Изменить текст анкеты")
async def edit_template_start(message: Message, state: FSMContext):
    await state.set_state(AdminEditTemplate.waiting_text)
    await message.answer("Пришлите новый текст анкеты:", reply_markup=kb.back_menu())


@router.message(AdminEditTemplate.waiting_text)
async def edit_template_save(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.ADMIN_GREETING, reply_markup=kb.admin_main_menu())
        return
    db.set_setting("anketa_template", message.text)
    await state.clear()
    await message.answer("Текст анкеты обновлён.", reply_markup=kb.admin_main_menu())


@router.message(F.text == "🖼 Прикрепить/сменить фото")
async def edit_photo_start(message: Message, state: FSMContext):
    await state.set_state(AdminEditTemplate.waiting_photo)
    await message.answer("Пришлите фото для анкеты:", reply_markup=kb.back_menu())


@router.message(AdminEditTemplate.waiting_photo, F.photo)
async def edit_photo_save(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    db.set_setting("anketa_photo", file_id)
    await state.clear()
    await message.answer("Фото анкеты обновлено.", reply_markup=kb.admin_main_menu())


@router.message(F.text.in_(["🟢 Открыть набор", "🔴 Закрыть набор"]))
async def toggle_recruitment(message: Message):
    template = db.get_setting("anketa_template") or ""
    currently_open = db.get_setting("recruitment_open") == "1"

    if not currently_open:
        if len(template.strip()) < 10:
            await message.answer(
                "Нельзя открыть набор — текст анкеты должен быть не короче 10 символов. "
                "Сначала отредактируйте шаблон."
            )
            return
        db.set_setting("recruitment_open", "1")
        await message.answer("Набор анкет открыт! 🟢", reply_markup=kb.admin_anketa_settings_menu(True))
    else:
        db.set_setting("recruitment_open", "0")
        await message.answer("Набор анкет закрыт. 🔴", reply_markup=kb.admin_anketa_settings_menu(False))


# ==================== УПРАВЛЕНИЕ РОЛЯМИ ====================

@router.message(F.text == "🎭 Управление ролями")
async def manage_roles(message: Message):
    await message.answer("Нажмите на роль, чтобы включить/выключить её, или добавьте новую:", reply_markup=kb.admin_roles_menu())


@router.message(F.text == "➕ Добавить роль")
async def add_role_start(message: Message, state: FSMContext):
    await state.set_state(AdminManageRoles.waiting_new_role)
    await message.answer("Напишите название новой роли:", reply_markup=kb.back_menu())


@router.message(AdminManageRoles.waiting_new_role)
async def add_role_save(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await message.answer(t.ADMIN_GREETING, reply_markup=kb.admin_main_menu())
        return
    db.add_role(message.text)
    await state.clear()
    await message.answer(f"Роль «{message.text}» добавлена.", reply_markup=kb.admin_roles_menu())


@router.message(F.text.regexp(r"^(🟢|🔴) .+"))
async def toggle_role_handler(message: Message):
    role_name = message.text[2:].strip()
    roles = db.get_all_roles()
    for r in roles:
        if r[1] == role_name:
            db.toggle_role(r[0])
            break
    await message.answer("Обновлено.", reply_markup=kb.admin_roles_menu())


# ==================== ЕСЛИ РВЁТ КРЫШУ ====================

@router.message(F.text == "🙀 Если рвёт крышу")
async def stress_relief(message: Message):
    cat_url = await utils.get_random_cat_url()
    await message.answer_photo(cat_url, caption="Дыши, всё будет хорошо 🐱")

