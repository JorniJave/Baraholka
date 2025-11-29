from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
import logging

from config import config
from services import AdminService
from keyboards import admin_menu
from aiogram.filters import Command

router = Router()
admin_service = AdminService()


@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Системные настройки"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        text = (
            "🔧 <b>Системные настройки</b>\n\n"
            f"📊 <b>Текущие настройки:</b>\n"
            f"• ID канала: {config.CHANNEL_ID or 'Не настроен'}\n"
            f"• Админы: {len(config.ADMIN_IDS)} пользователей\n"
            f"• Привилегии: {len(config.PRIVILEGES)} уровней\n\n"
            "⚙️ <b>Доступные функции:</b>\n"
            "• Настройка канала для публикаций\n"
            "• Управление списком админов\n"
            "• Резервное копирование БД\n"
            "• Системные логи\n\n"
            "⚡ <b>Быстрые команды:</b>\n"
            "• <code>/set_channel -100123456</code> - установить канал\n"
            "• <code>/add_admin 123456</code> - добавить админа\n"
            "• <code>/backup</code> - создать backup БД"
        )

        await callback.message.edit_text(text, reply_markup=admin_menu(), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка системных настроек: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(Command("set_channel"))
async def set_channel(message: Message):
    """Установка канала для публикаций"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            return

        # Здесь будет логика установки канала
        await message.answer("📢 <b>Настройка канала</b>\n\n"
                             "Используйте: /set_channel [ID_канала]\n\n"
                             "Пример: /set_channel -100123456789", parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка установки канала: {e}")
        await message.answer("❌ Ошибка установки канала")


@router.message(Command("add_admin"))
async def add_admin(message: Message):
    """Добавление администратора"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            return

        # Здесь будет логика добавления админа
        await message.answer("👑 <b>Добавление администратора</b>\n\n"
                             "Используйте: /add_admin [ID_пользователя]\n\n"
                             "Пример: /add_admin 123456789", parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка добавления админа: {e}")
        await message.answer("❌ Ошибка добавления админа")


@router.message(Command("backup"))
async def create_backup(message: Message):
    """Создание резервной копии БД"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            return

        # Здесь будет логика создания backup
        await message.answer("💾 <b>Резервное копирование</b>\n\n"
                             "Создание резервной копии базы данных...", parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка создания backup: {e}")
        await message.answer("❌ Ошибка создания резервной копии")