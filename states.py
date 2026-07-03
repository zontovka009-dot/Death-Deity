# -*- coding: utf-8 -*-
from aiogram.fsm.state import State, StatesGroup


class AnketaForm(StatesGroup):
    filling = State()
    confirm = State()


class SupportForm(StatesGroup):
    choosing_type = State()
    writing_text = State()
    confirm = State()


class AdminWriteToUser(StatesGroup):
    waiting_text = State()


class AdminEditTemplate(StatesGroup):
    waiting_text = State()
    waiting_photo = State()
