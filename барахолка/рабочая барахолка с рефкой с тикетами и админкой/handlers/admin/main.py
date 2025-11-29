from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
import logging

from config import config
from services import AdminService
from keyboards import admin_menu

router = Router()
admin_service = AdminService()


@router.message(Command("admin"))
async def admin_panel(message: Message):
    try:
        user_id = message.from_user.id
        is_admin = await admin_service.is_admin(user_id)

        if not is_admin:
            await message.answer("❌ Доступ запрещен")
            return

        await message.answer("⚙️ Панель администратора:", reply_markup=admin_menu())
        logging.info(f"Открыта админ-панель: UserID={user_id}")
    except Exception as e:
        logging.error(f"Ошибка админ-панели: {e}")
        await message.answer("❌ Ошибка доступа к админ-панели")


@router.callback_query(F.data == "admin_main")
async def admin_main_panel(callback: CallbackQuery):
    try:
        user_id = callback.from_user.id
        if not await admin_service.is_admin(user_id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.message.edit_text("⚙️ Панель администратора:", reply_markup=admin_menu())
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        stats = await admin_service.get_statistics()
        text = f"""<b>📊 Статистика:</b>

👥 Пользователей: {stats['users_count']}
📦 Постов: {stats['posts_count']}  
🎫 Тикетов: {stats['tickets_count']}"""

        await callback.message.edit_text(text, reply_markup=admin_menu(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка статистики: {e}")
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)