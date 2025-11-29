# states.py
from aiogram.fsm.state import State, StatesGroup

class SellItem(StatesGroup):
    photos = State()
    title = State()
    price = State()
    description = State()
    confirm = State()

class TicketStates(StatesGroup):
    waiting_for_theme = State()
    waiting_for_message = State()
    user_chat_active = State()

class AdminStates(StatesGroup):
    admin_chat_active = State()