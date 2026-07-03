# -*- coding: utf-8 -*-
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

import database as db
import keyboards as kb
import texts as t
import utils
from states import AdminWriteToUser, AdminEditTemplate, AdminEditLink, AdminSearch
from config import ADMIN_IDS, NEWCOMERS_GROUP_ID

router = Router()


def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS


@router.message.middleware()
async def admin_only_middleware(handler, event: Message, data):
    if not is_admin(event.from_user.id):
        return
    return await handler(event, data)


@router.callback_query.middleware()
async def admin_only_cb_middleware(handler, event: CallbackQuery, data):
    if not is_admin(event.from_user.id):
        await event.answer("Это только для админов 🙈", show_alert=True)
        return
    return await handler(event, data)


# ==================== ОБЩАЯ ЛОГИКА "РЕШЕНО" (чистим все копии карточек) ====================

async def resolve_entity(bot, entity_type: str, entity_id: int):
    """
    Разбирается со всеми живыми карточками сущности: групповую карточку
    просто разоружаем (убираем кнопки), личные уведомления у админов —
    удаляем целиком. Возвращает список карточек (на случай, если вызывающий
    хочет понять, была ли карточка, с которой кликнули, среди них).
    """
    cards = db.get_cards(entity_type, entity_id)
    for _id, etype, eid, chat_id, message_id, kind in cards:
        try:
            if kind == "group":
                await bot.edit_message_reply_markup(chat_id, message_id, reply_markup=None)
            else:
                await bot.delete_message(chat_id, message_id)
        except Exception:
            pass
    db.clear_cards(entity_type, entity_id)
    return cards


def _card_contains(cards, chat_id, message_id):
    return any(c[3] == chat_id and c[4] == message_id for c in cards)


# ==================== ЗАЯВКИ: СПИСКИ (компактно, список + разворот) ====================

def _app_label(app):
    return f"№{app[0]}"


@router.message(F.text == "📥 Посмотреть заявки")
async def view_applications_menu(message: Message, state: FSMContext):
    await utils.replace_message(message, state, "Какие заявки глянем?", kb.admin_applications_menu())


async def render_applications_list(status: str):
    if status == "pending":
        apps = db.get_applications_by_status("pending")
        title = "🟢 Активные заявки:" if apps else t.NOTHING_FOUND
    else:
        apps = db.get_applications_processed()
        title = "✔️ Проверенные заявки:" if apps else t.NOTHING_FOUND
    items = [(a[0], _app_label(a)) for a in apps]
    return title, kb.entity_list_kb(items, "appview") if items else None


@router.message(F.text == "🟢 Активные заявки")
async def view_active_applications(message: Message, state: FSMContext):
    title, markup = await render_applications_list("pending")
    await utils.replace_message(message, state, title, markup)


@router.message(F.text == "✔️ Проверенные")
async def view_processed_applications(message: Message, state: FSMContext):
    title, markup = await render_applications_list("processed")
    await utils.replace_message(message, state, title, markup)


@router.callback_query(F.data.startswith("applist_"))
async def app_back_to_list(call: CallbackQuery):
    status = call.data.split("_", 1)[1]
    title, markup = await render_applications_list(status)
    try:
        await call.message.edit_text(title, reply_markup=markup)
    except Exception:
        # если исходная карточка была с фото — text редактировать нельзя, шлём заново
        await call.message.answer(title, reply_markup=markup)
    await call.answer()


@router.callback_query(F.data.startswith("appview_"))
async def app_view_detail(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не нашёл такую заявку", show_alert=True)
        return
    user_row = db.get_user(app[1])
    name = utils.esc(user_row[2]) if user_row else "?"
    username = f"@{user_row[1]}" if user_row and user_row[1] else "—"
    text = f"📥 Анкета #{app[0]}\nОт: {name} ({username})\n\n{utils.esc(app[2])}"
    markup = kb.application_detail_kb(app_id, app[4])
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except Exception:
        await call.message.answer(text, reply_markup=markup)
    await call.answer()


# ==================== ЗАЯВКИ: ДЕЙСТВИЯ ====================

@router.callback_query(F.data.startswith("app_accept_"))
async def app_accept(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не нашёл", show_alert=True)
        return

    cards = db.get_cards("application", app_id)
    was_registered = _card_contains(cards, call.message.chat.id, call.message.message_id)

    db.set_application_status(app_id, "approved", call.from_user.id)
    await resolve_entity(call.bot, "application", app_id)

    if not was_registered:
        title, markup = await render_applications_list("processed")
        try:
            await call.message.edit_text(title, reply_markup=markup)
        except Exception:
            pass

    await call.bot.send_message(app[1], t.ANKETA_APPROVED_USER)

    # пост в чат новичков — только сейчас, когда анкета реально принята
    user_row = db.get_user(app[1])
    username = f"@{user_row[1]}" if user_row and user_row[1] else "юзер"
    caption = f"Анкета участника: {username}\n\n{utils.esc(app[2])}"
    try:
        if app[3]:  # photo_file_id
            await call.bot.send_photo(
                NEWCOMERS_GROUP_ID, app[3], caption=caption, reply_markup=kb.write_button_kb(app[1])
            )
        else:
            await call.bot.send_message(
                NEWCOMERS_GROUP_ID, caption, reply_markup=kb.write_button_kb(app[1])
            )
    except Exception:
        pass

    await call.bot.send_message(
        call.from_user.id, t.INVITE_PROMPT, reply_markup=kb.invite_kb(app[1])
    )
    await call.answer("Принято! 🎉")


@router.callback_query(F.data.startswith("app_reject_"))
async def app_reject(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не нашёл", show_alert=True)
        return

    cards = db.get_cards("application", app_id)
    was_registered = _card_contains(cards, call.message.chat.id, call.message.message_id)

    db.set_application_status(app_id, "rejected", call.from_user.id)
    await resolve_entity(call.bot, "application", app_id)

    if not was_registered:
        title, markup = await render_applications_list("processed")
        try:
            await call.message.edit_text(title, reply_markup=markup)
        except Exception:
            pass

    await call.bot.send_message(app[1], t.ANKETA_REJECTED_USER)
    await call.answer("Отклонено")


@router.callback_query(F.data.startswith("app_block_"))
async def app_block(call: CallbackQuery):
    app_id = int(call.data.split("_")[-1])
    app = db.get_application(app_id)
    if not app:
        await call.answer("Не нашёл", show_alert=True)
        return

    cards = db.get_cards("application", app_id)
    was_registered = _card_contains(cards, call.message.chat.id, call.message.message_id)

    db.set_application_status(app_id, "rejected", call.from_user.id)
    db.set_ban_status(app[1], "soft")
    await resolve_entity(call.bot, "application", app_id)

    if not was_registered:
        title, markup = await render_applications_list("processed")
        try:
            await call.message.edit_text(title, reply_markup=markup)
        except Exception:
            pass

    await call.bot.send_message(app[1], t.BANNED_SOFT)
    await call.answer("Заблокирован")


# ==================== ССЫЛКА НА ВСТУПЛЕНИЕ ====================

@router.callback_query(F.data.startswith("invite_yes_"))
async def invite_yes(call: CallbackQuery):
    user_id = int(call.data.split("_")[-1])
    link = db.get_setting("invite_link")
    if not link:
        await call.message.edit_text(t.INVITE_NOT_SET, reply_markup=None)
        await call.answer()
        return
    await call.bot.send_message(user_id, f"{t.INVITE_SENT}\n{link}")
    await call.message.edit_text("Ссылку отправил ✅", reply_markup=None)
    await call.answer()


@router.callback_query(F.data == "invite_no")
async def invite_no(call: CallbackQuery):
    await call.message.edit_text("Окей, без ссылки 🙂", reply_markup=None)
    await call.answer()


@router.message(F.text == "🔗 Ссылка чата")
async def link_settings(message: Message, state: FSMContext):
    current = db.get_setting("invite_link") or "(не задана)"
    await state.set_state(AdminEditLink.waiting_text)
    await utils.replace_message(
        message, state, f"Текущая ссылка:\n{current}\n\nПришли новую, чтобы обновить:", kb.back_menu()
    )


@router.message(AdminEditLink.waiting_text)
async def link_settings_save(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.ADMIN_GREETING, kb.admin_main_menu())
        return
    db.set_setting("invite_link", message.text.strip())
    await state.clear()
    await message.answer("Ссылку обновил ✅", reply_markup=kb.admin_main_menu())


# ==================== ОБРАЩЕНИЯ (ТИКЕТЫ): СПИСКИ ====================

def _tk_label(tk):
    icons = {"appeal": "⚖️", "complaint": "📢", "other": "❓"}
    return f"{icons.get(tk[2], '❓')}№{tk[0]}"


async def render_tickets_list(status: str):
    if status == "pending":
        tickets = db.get_tickets_by_status("pending")
        title = "🟢 Активные обращения:" if tickets else t.NOTHING_FOUND
    else:
        tickets = db.get_tickets_processed()
        title = "✔️ Обработанные обращения:" if tickets else t.NOTHING_FOUND
    items = [(tk[0], _tk_label(tk)) for tk in tickets]
    return title, kb.entity_list_kb(items, "tkview") if items else None


@router.message(F.text == "📨 Посмотреть обращения")
async def view_tickets_menu(message: Message, state: FSMContext):
    await utils.replace_message(message, state, "Какие обращения глянем?", kb.admin_tickets_menu())


@router.message(F.text == "🟢 Активные обращения")
async def view_active_tickets(message: Message, state: FSMContext):
    title, markup = await render_tickets_list("pending")
    await utils.replace_message(message, state, title, markup)


@router.message(F.text == "✔️ Обработанные")
async def view_processed_tickets(message: Message, state: FSMContext):
    title, markup = await render_tickets_list("processed")
    await utils.replace_message(message, state, title, markup)


@router.callback_query(F.data.startswith("tklist_"))
async def tk_back_to_list(call: CallbackQuery):
    status = call.data.split("_", 1)[1]
    title, markup = await render_tickets_list(status)
    try:
        await call.message.edit_text(title, reply_markup=markup)
    except Exception:
        await call.message.answer(title, reply_markup=markup)
    await call.answer()


@router.callback_query(F.data.startswith("tkview_"))
async def tk_view_detail(call: CallbackQuery):
    ticket_id = int(call.data.split("_")[-1])
    tk = db.get_ticket(ticket_id)
    if not tk:
        await call.answer("Не нашёл", show_alert=True)
        return
    type_labels = {"appeal": "⚖️ Аппеляция", "complaint": "📢 Жалоба", "other": "❓ Другое"}
    text = f"{type_labels.get(tk[2], tk[2])} #{tk[0]}\n\n{utils.esc(tk[3])}"
    markup = kb.ticket_detail_kb(ticket_id, tk[4])
    try:
        await call.message.edit_text(text, reply_markup=markup)
    except Exception:
        await call.message.answer(text, reply_markup=markup)
    await call.answer()


# ==================== ОБРАЩЕНИЯ: ДЕЙСТВИЯ ====================

@router.callback_query(F.data.startswith("tk_reply_"))
async def tk_reply(call: CallbackQuery, state: FSMContext):
    ticket_id = int(call.data.split("_")[-1])
    await state.update_data(ticket_id=ticket_id)
    await state.set_state(AdminWriteToUser.waiting_text)
    await call.message.answer(f"Что ответить по обращению #{ticket_id}?")
    await call.answer()


@router.callback_query(F.data.startswith("tk_reject_"))
async def tk_reject(call: CallbackQuery):
    ticket_id = int(call.data.split("_")[-1])
    tk = db.get_ticket(ticket_id)
    if not tk:
        await call.answer("Не нашёл", show_alert=True)
        return

    cards = db.get_cards("ticket", ticket_id)
    was_registered = _card_contains(cards, call.message.chat.id, call.message.message_id)

    db.set_ticket_status(ticket_id, "rejected")
    await resolve_entity(call.bot, "ticket", ticket_id)

    if not was_registered:
        title, markup = await render_tickets_list("processed")
        try:
            await call.message.edit_text(title, reply_markup=markup)
        except Exception:
            pass

    await call.bot.send_message(tk[1], "По твоему обращению решение: отклонено.")
    await call.answer("Отклонено")


@router.callback_query(F.data.startswith("tk_block_"))
async def tk_block(call: CallbackQuery):
    ticket_id = int(call.data.split("_")[-1])
    tk = db.get_ticket(ticket_id)
    if not tk:
        await call.answer("Не нашёл", show_alert=True)
        return

    cards = db.get_cards("ticket", ticket_id)
    was_registered = _card_contains(cards, call.message.chat.id, call.message.message_id)

    db.set_ticket_status(ticket_id, "banned")
    ban_type = "hard" if tk[2] == "appeal" else "soft"
    db.set_ban_status(tk[1], ban_type)
    await resolve_entity(call.bot, "ticket", ticket_id)

    if not was_registered:
        title, markup = await render_tickets_list("processed")
        try:
            await call.message.edit_text(title, reply_markup=markup)
        except Exception:
            pass

    await call.bot.send_message(tk[1], t.BANNED_HARD if ban_type == "hard" else t.BANNED_SOFT)
    await call.answer("Заблокирован")


@router.message(AdminWriteToUser.waiting_text)
async def admin_write_text(message: Message, state: FSMContext):
    data = await state.get_data()

    ticket_id = data.get("ticket_id")
    if ticket_id:
        tk = db.get_ticket(ticket_id)
        if tk:
            db.set_ticket_status(ticket_id, "answered", message.text)
            await resolve_entity(message.bot, "ticket", ticket_id)
            await message.bot.send_message(
                tk[1], f"💬 Ответ по обращению #{ticket_id}:\n\n{utils.esc(message.text)}"
            )
            await message.answer(t.MESSAGE_SENT_OK, reply_markup=kb.admin_main_menu())
        await state.clear()
        return

    direct_user = data.get("direct_write_user")
    if direct_user:
        await message.bot.send_message(direct_user, f"💬 {utils.esc(message.text)}")
        await message.answer(t.MESSAGE_SENT_OK, reply_markup=kb.admin_main_menu())
        await state.clear()


# ==================== "НАПИСАТЬ" С ПОСТА ОДОБРЕННОЙ АНКЕТЫ ====================

@router.callback_query(F.data.startswith("write_"))
async def profile_write_from_post(call: CallbackQuery, state: FSMContext):
    user_id = int(call.data.split("_")[-1])
    await state.update_data(direct_write_user=user_id)
    await state.set_state(AdminWriteToUser.waiting_text)
    await call.bot.send_message(call.from_user.id, t.WRITE_TO_USER_PROMPT)
    await call.answer()


# ==================== ЧЁРНЫЙ СПИСОК ====================

@router.message(F.text == "🚫 Чёрный список")
async def view_blacklist(message: Message, state: FSMContext):
    await state.clear()
    users = db.get_banned_users()
    if not users:
        await utils.replace_message(message, state, t.NOTHING_FOUND, kb.admin_main_menu())
        return
    lines = [f"🚫 {utils.esc(u[2])} (@{u[1]}) — ID {u[0]}, статус: {u[3]}" for u in users]
    text = "Чёрный список:\n\n" + "\n".join(lines)
    await utils.replace_message(message, state, text, kb.admin_main_menu())


# ==================== ПОИСК ЧЕЛОВЕКА ====================

@router.message(F.text == "🔍 Поиск")
async def search_start(message: Message, state: FSMContext):
    await state.set_state(AdminSearch.waiting_query)
    await utils.replace_message(message, state, "Введи ID или юзернейм:", kb.back_menu())


@router.message(AdminSearch.waiting_query)
async def search_do(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.ADMIN_GREETING, kb.admin_main_menu())
        return

    query = message.text.strip()
    user_row = None
    if query.lstrip("-").isdigit():
        user_row = db.get_user(int(query))
    if not user_row:
        user_row = db.get_user_by_username(query)

    if not user_row:
        await utils.replace_message(message, state, "Никого не нашёл 🤷", kb.back_menu())
        return

    profile_row = db.get_profile(user_row[0])
    text, photo = utils.format_profile_text(user_row, profile_row)
    banned = user_row[3] != "none"
    await state.update_data(search_target=user_row[0])
    await state.set_state(None)
    if photo:
        await utils.replace_message_photo(message, state, photo, text, kb.admin_profile_result_menu(banned))
    else:
        await utils.replace_message(message, state, text, kb.admin_profile_result_menu(banned))


@router.message(F.text.in_(["🚫 Заблокировать", "✅ Разбанить"]))
async def search_toggle_ban(message: Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("search_target")
    if not target:
        return
    if message.text == "🚫 Заблокировать":
        db.set_ban_status(target, "hard")
        await message.bot.send_message(target, t.BANNED_HARD)
        await message.answer("Заблокировал 🚫", reply_markup=kb.admin_profile_result_menu(True))
    else:
        db.set_ban_status(target, "none")
        await message.bot.send_message(target, "Тебя разблокировали, добро пожаловать обратно! 🤍")
        await message.answer("Разбанил ✅", reply_markup=kb.admin_profile_result_menu(False))


@router.message(F.text == "✍️ Написать")
async def search_write(message: Message, state: FSMContext):
    data = await state.get_data()
    target = data.get("search_target")
    if not target:
        return
    await state.update_data(direct_write_user=target)
    await state.set_state(AdminWriteToUser.waiting_text)
    await utils.replace_message(message, state, t.WRITE_TO_USER_PROMPT, kb.back_menu())


# ==================== СПИСОК АДМИНОВ ====================

@router.message(F.text == "👑 Список админов")
async def view_admins(message: Message, state: FSMContext):
    text = "👑 Админы флуда:\n\n" + "\n".join(str(a) for a in ADMIN_IDS)
    await utils.replace_message(message, state, text, kb.admin_main_menu())


# ==================== АНКЕТА ЗАЯВОК (НАСТРОЙКИ) ====================

@router.message(F.text == "🗂 Анкета заявок")
async def anketa_settings(message: Message, state: FSMContext):
    is_open = db.get_setting("recruitment_open") == "1"
    template = db.get_setting("anketa_template") or "(пусто)"
    text = f"Текущий шаблон анкеты:\n\n{template}\n\nНабор: {'открыт 🟢' if is_open else 'закрыт 🔴'}"
    await utils.replace_message(message, state, text, kb.admin_anketa_settings_menu(is_open))


@router.message(F.text == "✏️ Изменить текст анкеты")
async def edit_template_start(message: Message, state: FSMContext):
    await state.set_state(AdminEditTemplate.waiting_text)
    await utils.replace_message(message, state, "Пришли новый текст анкеты:", kb.back_menu())


@router.message(AdminEditTemplate.waiting_text)
async def edit_template_save(message: Message, state: FSMContext):
    if message.text == "⬅️ Назад":
        await state.clear()
        await utils.replace_message(message, state, t.ADMIN_GREETING, kb.admin_main_menu())
        return
    db.set_setting("anketa_template", message.text)
    await state.clear()
    await message.answer("Текст анкеты обновил ✅", reply_markup=kb.admin_main_menu())


@router.message(F.text == "🖼 Прикрепить/сменить фото")
async def edit_photo_start(message: Message, state: FSMContext):
    await state.set_state(AdminEditTemplate.waiting_photo)
    await utils.replace_message(message, state, "Пришли фото для анкеты:", kb.back_menu())


@router.message(AdminEditTemplate.waiting_photo, F.photo)
async def edit_photo_save(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    db.set_setting("anketa_photo", file_id)
    await state.clear()
    await message.answer("Фото анкеты обновил ✅", reply_markup=kb.admin_main_menu())


@router.message(F.text.in_(["🟢 Открыть набор", "🔴 Закрыть набор"]))
async def toggle_recruitment(message: Message):
    template = db.get_setting("anketa_template") or ""
    currently_open = db.get_setting("recruitment_open") == "1"

    if not currently_open:
        if len(template.strip()) < 10:
            await message.answer(
                "Не могу открыть набор — текст анкеты короче 10 символов. Сначала отредактируй шаблон."
            )
            return
        db.set_setting("recruitment_open", "1")
        await message.answer("Набор анкет открыт! 🟢", reply_markup=kb.admin_anketa_settings_menu(True))
    else:
        db.set_setting("recruitment_open", "0")
        await message.answer("Набор анкет закрыт. 🔴", reply_markup=kb.admin_anketa_settings_menu(False))


# ==================== ЕСЛИ РВЁТ КРЫШУ ====================

@router.message(F.text == "🙀 Если рвёт крышу")
async def stress_relief(message: Message):
    cat_url = await utils.get_random_cat_url()
    await message.answer_photo(cat_url, caption="Дыши, всё будет хорошо 🐱")
