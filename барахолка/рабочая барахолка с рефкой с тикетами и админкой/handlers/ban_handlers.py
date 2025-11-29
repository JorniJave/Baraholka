# handlers/ban_handlers.py
"""
Глобальные обработчики для проверки банов пользователей.
Эти handlers должны быть зарегистрированы первыми, чтобы проверять баны до обработки других событий.
"""
from aiogram import Router
from aiogram.types import Message, CallbackQuery
from services import UserService
from config import config

router = Router()
user_service = UserService()


@router.message()
async def check_ban_global(message: Message):
    """
    Глобальная проверка бана для всех сообщений.
    Не блокирует обработку, только проверяет и уведомляет.
    """
    # Пропускаем админов
    if message.from_user.id in config.ADMIN_IDS:
        return

    # Проверяем бан
    is_banned = await user_service.is_user_banned(message.from_user.id)

    if is_banned:
        # Отправляем уведомление, но не блокируем обработку
        # (другие handlers могут обработать команды даже для забаненных)
        await message.answer("🚫 Вы заблокированы и не можете использовать бота.")
        return


@router.callback_query()
async def check_ban_global_callback(callback: CallbackQuery):
    """
    Глобальная проверка бана для всех callback.
    Блокирует выполнение callback для забаненных пользователей.
    """
    # Пропускаем админов
    if callback.from_user.id in config.ADMIN_IDS:
        return

    # Проверяем бан
    is_banned = await user_service.is_user_banned(callback.from_user.id)

    if is_banned:
        await callback.answer("🚫 Вы заблокированы и не можете использовать бота.", show_alert=True)
        return