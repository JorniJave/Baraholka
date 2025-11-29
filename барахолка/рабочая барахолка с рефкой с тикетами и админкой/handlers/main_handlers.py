# handlers/main_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.filters import CommandObject  # ✅ ДОБАВИТЬ ЭТОТ ИМПОРТ
import logging

from config import config
from services import UserService, AdminService
from keyboards import main_menu
from simple_referral import simple_referral
from database import AsyncSessionLocal, User, Referral

router = Router()
user_service = UserService()
admin_service = AdminService()


@router.message(CommandStart())
async def cmd_start(message: Message, command: CommandObject):  # ✅ Теперь работает
    """Обработчик команды /start"""
    try:
        # Получаем аргументы из команды
        args = command.args

        user, referrer_id, is_new = await simple_referral.handle_start_command(
            user_id=message.from_user.id,
            username=message.from_user.username,
            full_name=message.from_user.full_name,
            args=args,
            bot=message.bot
        )

        # Логируем только важное
        if is_new:
            if referrer_id:
                welcome_text = (
                    f"{message.from_user.full_name}, вы зарегистрированы в боте и закреплены за "
                    f"пользователем с ID <b>{referrer_id}</b>.\n\n"
                    f"🏪 Добро пожаловать на барахолку! Используйте меню ниже для навигации:"
                )
                logging.info(f"Новый пользователь: ID={message.from_user.id}, Referrer={referrer_id}")
            else:
                welcome_text = (
                    f"{message.from_user.full_name}, вы зарегистрированы в боте.\n\n"
                    f"🏪 Добро пожаловать на барахолку! Используйте меню ниже для навигации:"
                )
        else:
            welcome_text = (
                f"{message.from_user.full_name}, вижу что вы уже в базе данных.\n\n"
                f"🏪 Добро пожаловать на барахолку! Используйте меню ниже для навигации:"
            )

        await message.answer(
            welcome_text,
            reply_markup=main_menu(message.from_user.id, config.ADMIN_IDS),
            parse_mode="HTML"
        )

    except Exception as e:
        logging.error(f"Ошибка в старт команде: {e}")
        await message.answer(
            "🏪 Добро пожаловать! Используйте меню для навигации:",
            reply_markup=main_menu(message.from_user.id, config.ADMIN_IDS)
        )


@router.message(Command("myid"))
async def cmd_myid(message: Message):
    """Показывает ID пользователя"""
    user_id = message.from_user.id
    username = message.from_user.username
    is_admin = await admin_service.is_admin(user_id)

    response = f"🆔 Ваш ID: <code>{user_id}</code>\n"
    response += f"📛 Ваш username: @{username}\n"
    response += f"👑 Статус админа: {'✅ Да' if is_admin else '❌ Нет'}"

    await message.answer(response, parse_mode="HTML")


@router.message(Command("ref"))
async def cmd_ref(message: Message):
    """Реферальная команда - показывает профиль с ссылкой"""
    user_id = message.from_user.id

    # Получаем статистику
    stats = await simple_referral.get_referral_stats(user_id)

    # Генерируем ссылку
    ref_link = await simple_referral.generate_referral_link(user_id, message.bot)

    text = (
        "<b>🔗 Реферальная система</b>\n\n"
        f"🆔 Ваш телеграм ID: <code>{user_id}</code>\n"
        f"👥 Количество приглашенных пользователей: <b>{stats['total_referrals']}</b>\n"
        f"🎯 До VIP осталось: <b>{stats['needed_for_vip']}</b>\n\n"
        f"<b>🚀 Ваша персональная ссылка для приглашений:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        "<b>💡 Приглашайте друзей и получайте VIP статус автоматически после 20 рефералов!</b>"
    )

    await message.answer(text, parse_mode="HTML")


@router.message(Command("ref_top"))
async def cmd_ref_top(message: Message):
    """Топ рефереров"""
    leaderboard = await simple_referral.get_leaderboard(10)

    if not leaderboard:
        await message.answer("🏆 Пока нет активных рефереров")
        return

    text = "<b>🏆 Топ рефереров:</b>\n\n"
    for i, user in enumerate(leaderboard, 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} @{user['username']} - {user['referrals_count']} реф. ({user['privilege'].upper()})\n"

    await message.answer(text, parse_mode="HTML")


@router.message(Command("debug_ref"))
async def cmd_debug_ref(message: Message, command: CommandObject):
    """Отладочная команда для проверки реферальной системы"""
    user_id = message.from_user.id
    args = command.args if command else None

    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            await message.answer("❌ Пользователь не найден в БД")
            return

        # Получаем рефералов
        from sqlalchemy import select
        stmt = select(Referral).where(Referral.referrer_id == user_id)
        result = await session.execute(stmt)
        referrals = result.scalars().all()

        # Получаем реферера
        referrer = None
        if user.referrer_id:
            referrer = await session.get(User, user.referrer_id)

        # Генерируем ссылку
        ref_link = await simple_referral.generate_referral_link(user_id, message.bot)

        # Безопасное получение ID реферера
        referrer_info = referrer.id if referrer else 'Нет'

        text = (
            f"<b>🔧 Отладочная информация рефералов:</b>\n\n"
            f"🆔 Ваш ID: <code>{user_id}</code>\n"
            f"👥 Ваши рефералы: {user.referrals_count}\n"
            f"📋 Список рефералов: {[r.referred_id for r in referrals]}\n"
            f"🔗 Ваш реферер: {referrer_info}\n"
            f"⭐ Ваш статус: {user.privilege}\n"
            f"📝 Аргументы команды: <code>{args}</code>\n\n"
            f"<b>Ваша ссылка:</b>\n"
            f"<code>{ref_link}</code>\n\n"
            f"<b>Проверка ссылки:</b>\n"
            f"1. Скопируйте ссылку выше\n"
            f"2. Отправьте другу\n"
            f"3. При переходе должно быть: /start {user_id}"
        )

        await message.answer(text, parse_mode="HTML")


@router.callback_query(F.data == "main")
async def back_to_main(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "🏪 Добро пожаловать на барахолку:",
            reply_markup=main_menu(callback.from_user.id, config.ADMIN_IDS)
        )
    except Exception:
        await callback.answer()


@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    try:
        profile = await user_service.get_user_profile(callback.from_user.id, callback.bot)

        # Безопасная проверка профиля
        if not profile:
            await callback.answer("❌ Профиль не найден. Используйте /start", show_alert=True)
            return

        vip_progress = ""
        if profile['privilege'] == "user":
            vip_progress = f"\n🎯 До VIP: {profile['ref_stats']['needed_for_vip']} рефералов"

        text = f"""<b>👤 Профиль</b>

📛 Тег: @{profile['username']}
🆔 ID: {profile['user_id']}
⭐ Статус: {profile['privilege'].upper()}
⏰ Кулдаун: {profile['cooldown']} мин
📊 Постов: {profile['posts_count']}
👥 Рефералов: {profile['ref_stats']['total_referrals']}
{vip_progress}

<b>🔗 Реферальная ссылка:</b>
<code>{profile['referral_link']}</code>

<b>💡 Пригласи 20 друзей и получи VIP статус!</b>"""

        await callback.message.edit_text(text, reply_markup=main_menu(callback.from_user.id, config.ADMIN_IDS),
                                         parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка в профиле для пользователя {callback.from_user.id}: {e}")
        await callback.answer("❌ Ошибка загрузки профиля", show_alert=True)