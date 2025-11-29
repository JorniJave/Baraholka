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
    except Exception as e:
        logging.error(f"Ошибка админ-панели: {e}")
        await message.answer("❌ Ошибка доступа к админ-панели")


@router.callback_query(F.data == "admin_main")
async def admin_main_panel(callback: CallbackQuery):
    try:
        
        user_id = callback.from_user.id
        if not await admin_service.is_admin(user_id):
            await callback.answer("❌ Доступ запрещен", show_alert=True)
            return

        # Получаем быструю статистику для главного экрана
        from services import TicketService, UserService, PostService
        ticket_service = TicketService()
        user_service = UserService()
        
        # Быстрая статистика
        stats = await admin_service.get_statistics()
        new_tickets = await ticket_service.get_tickets_by_status("new")
        in_progress_tickets = await ticket_service.get_tickets_by_status("in_progress")
        
        new_tickets_count = len(new_tickets) if new_tickets else 0
        in_progress_count = len(in_progress_tickets) if in_progress_tickets else 0
        
        text = "⚙️ <b>Панель администратора</b>\n\n"
        text += "📊 <b>Краткая статистика:</b>\n"
        text += f"👥 Пользователей: <b>{stats['users_count']}</b>\n"
        text += f"📦 Постов: <b>{stats['posts_count']}</b>\n"
        text += f"🎫 Тикетов: <b>{stats['tickets_count']}</b>\n"
        text += f"🚫 Забанено: <b>{stats['banned_count']}</b>\n\n"
        text += "🎫 <b>Тикеты:</b>\n"
        text += f"🆕 Новые: <b>{new_tickets_count}</b>\n"
        text += f"🔄 В работе: <b>{in_progress_count}</b>\n\n"
        text += "💡 Выберите раздел для управления:"

        await callback.answer()  # Убираем индикатор загрузки
        await callback.message.edit_text(text, reply_markup=admin_menu(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка в admin_main_panel для пользователя {callback.from_user.id}: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        from services import TicketService, UserService, PostService
        from database import AsyncSessionLocal, User, Post, Ticket, Referral
        from sqlalchemy import select, func
        from datetime import datetime, timedelta
        
        ticket_service = TicketService()
        
        # Основная статистика
        stats = await admin_service.get_statistics()
        
        # Детальная статистика
        async with AsyncSessionLocal() as session:
            # Статистика по привилегиям
            privilege_stats = {}
            for privilege in ["user", "vip", "premium", "god", "ultra_seller"]:
                stmt = select(func.count(User.id)).where(User.privilege == privilege)
                result = await session.execute(stmt)
                privilege_stats[privilege] = result.scalar()
            
            # Статистика по тикетам
            new_tickets = await ticket_service.get_tickets_by_status("new")
            in_progress_tickets = await ticket_service.get_tickets_by_status("in_progress")
            
            # Статистика за последние 24 часа
            yesterday = datetime.now() - timedelta(days=1)
            new_users_24h = await session.execute(
                select(func.count(User.id)).where(User.created_at >= yesterday)
            )
            new_posts_24h = await session.execute(
                select(func.count(Post.id)).where(Post.created_at >= yesterday)
            )
            new_tickets_24h = await session.execute(
                select(func.count(Ticket.id)).where(Ticket.created_at >= yesterday)
            )
            
            # Статистика по рефералам
            total_referrals = await session.execute(select(func.count(Referral.id)))
            
            # Топ пользователей по постам
            top_posts_stmt = select(User.id, User.username, User.posts_count).order_by(User.posts_count.desc()).limit(5)
            top_posts_result = await session.execute(top_posts_stmt)
            top_posts = top_posts_result.all()

        text = "📊 <b>Детальная статистика бота</b>\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "<b>👥 Пользователи:</b>\n"
        text += f"Всего: <b>{stats['users_count']}</b>\n"
        text += f"Новых за 24ч: <b>{new_users_24h.scalar()}</b>\n"
        text += f"Забанено: <b>{stats['banned_count']}</b>\n\n"
        
        text += "<b>⭐ По привилегиям:</b>\n"
        text += f"👤 User: <b>{privilege_stats['user']}</b>\n"
        text += f"💎 VIP: <b>{privilege_stats['vip']}</b>\n"
        text += f"⭐ Premium: <b>{privilege_stats['premium']}</b>\n"
        text += f"👑 God: <b>{privilege_stats['god']}</b>\n"
        text += f"🔥 Ultra Seller: <b>{privilege_stats['ultra_seller']}</b>\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "<b>📦 Посты:</b>\n"
        text += f"Всего: <b>{stats['posts_count']}</b>\n"
        text += f"Новых за 24ч: <b>{new_posts_24h.scalar()}</b>\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "<b>🎫 Тикеты:</b>\n"
        text += f"Всего: <b>{stats['tickets_count']}</b>\n"
        text += f"🆕 Новые: <b>{len(new_tickets) if new_tickets else 0}</b>\n"
        text += f"🔄 В работе: <b>{len(in_progress_tickets) if in_progress_tickets else 0}</b>\n"
        text += f"Новых за 24ч: <b>{new_tickets_24h.scalar()}</b>\n\n"
        
        text += "━━━━━━━━━━━━━━━━━━━━\n"
        text += "<b>🔗 Реферальная система:</b>\n"
        text += f"Всего рефералов: <b>{total_referrals.scalar()}</b>\n\n"
        
        if top_posts:
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "<b>🏆 Топ-5 по постам:</b>\n"
            for i, (user_id, username, posts) in enumerate(top_posts, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                text += f"{medal} @{username or 'нет'} - {posts} постов\n"

        await callback.message.edit_text(text, reply_markup=admin_menu(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка статистики: {e}", exc_info=True)
        await callback.answer("❌ Ошибка загрузки статистики", show_alert=True)