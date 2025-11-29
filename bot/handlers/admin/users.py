from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import logging

from config import config
from services import AdminService, UserService
from database import AsyncSessionLocal, User
from keyboards import (admin_menu, user_management_keyboard, user_search_keyboard,
                       privilege_selection_keyboard, user_actions_keyboard)  # ✅ ИСПРАВЛЕННЫЙ ИМПОРТ
from sqlalchemy import select

router = Router()
admin_service = AdminService()
user_service = UserService()


# ✅ СОСТОЯНИЯ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ
class UserManagementStates(StatesGroup):
    waiting_user_id = State()
    waiting_username = State()


# ✅ ГЛОБАЛЬНЫЙ СЛОВАРЬ ДЛЯ ХРАНЕНИЯ ВЫБРАННЫХ ПОЛЬЗОВАТЕЛЕЙ
selected_users = {}


@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Главное меню управления пользователями"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        # ✅ ОЧИЩАЕМ ВЫБРАННОГО ПОЛЬЗОВАТЕЛЯ ПРИ ВХОДЕ
        admin_id = callback.from_user.id
        if admin_id in selected_users:
            del selected_users[admin_id]

        text = (
            "👥 <b>Управление пользователями</b>\n\n"
            "🔍 <b>Сначала найдите пользователя</b>, затем выберите действие:\n\n"
            "1. Нажмите '🔍 Найти пользователя'\n"
            "2. Выберите пользователя из результатов\n"
            "3. Используйте кнопки управления\n\n"
            "💡 <i>Все действия выполняются только с выбранным пользователем</i>"
        )

        await callback.message.edit_text(text, reply_markup=user_management_keyboard(), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка управления пользователями: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


# ✅ ПОИСК ПОЛЬЗОВАТЕЛЯ
@router.callback_query(F.data == "find_user_menu")
async def find_user_menu(callback: CallbackQuery):
    """Меню поиска пользователя"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        text = "🔍 <b>Поиск пользователя</b>\n\nВыберите способ поиска:"
        await callback.message.edit_text(text, reply_markup=user_search_keyboard(), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка меню поиска: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "search_by_id")
async def search_by_id_start(callback: CallbackQuery, state: FSMContext):
    """Начало поиска по ID"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await state.set_state(UserManagementStates.waiting_user_id)
        text = "🔍 <b>Поиск по ID</b>\n\nВведите ID пользователя:"
        await callback.message.edit_text(text, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка поиска по ID: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "search_by_username")
async def search_by_username_start(callback: CallbackQuery, state: FSMContext):
    """Начало поиска по username"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await state.set_state(UserManagementStates.waiting_username)
        text = "🔍 <b>Поиск по username</b>\n\nВведите username пользователя (без @):"
        await callback.message.edit_text(text, parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка поиска по username: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(UserManagementStates.waiting_user_id)
async def process_user_id_search(message: Message, state: FSMContext):
    """Обработка поиска по ID"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            await state.clear()
            return

        if not message.text or not message.text.strip().isdigit():
            await message.answer("❌ Введите корректный ID (только цифры):")
            return

        user_id = int(message.text.strip())
        logging.info(f"🔍 Поиск пользователя по ID: {user_id} (админ: {message.from_user.id})")
        
        # Проверяем существование пользователя перед показом
        user = await user_service.get_user_by_id(user_id)
        if not user:
            logging.warning(f"❌ Пользователь с ID {user_id} не найден в базе данных")
            await message.answer(
                f"❌ Пользователь с ID <code>{user_id}</code> не найден в базе данных.\n\n"
                f"💡 Убедитесь, что пользователь использовал бота хотя бы раз (/start).",
                parse_mode="HTML"
            )
            await state.clear()
            return
        
        await find_and_show_user(message, user_id=user_id)
        await state.clear()

    except ValueError as e:
        logging.error(f"Ошибка парсинга ID: {e}")
        await message.answer("❌ Введите корректный ID (только цифры):")
    except Exception as e:
        logging.error(f"Ошибка обработки поиска по ID: {e}", exc_info=True)
        await message.answer("❌ Ошибка поиска. Попробуйте еще раз.")
        await state.clear()


@router.message(UserManagementStates.waiting_username)
async def process_username_search(message: Message, state: FSMContext):
    """Обработка поиска по username"""
    try:
        if not await admin_service.is_admin(message.from_user.id):
            await message.answer("❌ Доступ запрещен")
            await state.clear()
            return

        if not message.text or not message.text.strip():
            await message.answer("❌ Введите username пользователя:")
            return

        username = message.text.strip().lstrip('@').lower()
        logging.info(f"🔍 Поиск пользователя по username: {username} (админ: {message.from_user.id})")

        async with AsyncSessionLocal() as session:
            # Точный поиск
            stmt = select(User).where(User.username.ilike(username))
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()

            if user:
                await find_and_show_user(message, user=user)
            else:
                # Частичный поиск (если точный не дал результатов)
                stmt = select(User).where(User.username.ilike(f"%{username}%"))
                result = await session.execute(stmt)
                users = result.scalars().all()
                
                if users:
                    if len(users) == 1:
                        # Если найден один пользователь - показываем его
                        await find_and_show_user(message, user=users[0])
                    else:
                        # Если найдено несколько - показываем список
                        text = f"🔍 Найдено пользователей: {len(users)}\n\n"
                        text += "💡 Выберите пользователя из списка:\n\n"
                        
                        keyboard = []
                        for u in users[:10]:  # Ограничиваем 10 результатами
                            text += f"👤 @{u.username or 'нет'} (ID: {u.id})\n"
                            keyboard.append([InlineKeyboardButton(
                                text=f"@{u.username or 'нет'} (ID: {u.id})",
                                callback_data=f"select_user_{u.id}"
                            )])
                        
                        if len(users) > 10:
                            text += f"\n... и еще {len(users) - 10} пользователей"
                        
                        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="find_user_menu")])
                        
                        await message.answer(
                            text,
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                            parse_mode="HTML"
                        )
                else:
                    logging.warning(f"❌ Пользователь с username '{username}' не найден в базе данных")
                    await message.answer(
                        f"❌ Пользователь с username <b>@{username}</b> не найден в базе данных.\n\n"
                        f"💡 Возможные причины:\n"
                        f"• Пользователь еще не использовал бота\n"
                        f"• Username указан неверно\n"
                        f"• Пользователь изменил username\n\n"
                        f"💡 Попробуйте поиск по ID пользователя.",
                        parse_mode="HTML"
                    )

        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка обработки поиска по username: {e}", exc_info=True)
        await message.answer("❌ Ошибка поиска. Попробуйте еще раз.")
        await state.clear()


@router.callback_query(F.data.startswith("select_user_"))
async def select_user_from_list(callback: CallbackQuery):
    """Выбор пользователя из списка результатов поиска"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return
        
        user_id = int(callback.data.split("_")[2])
        logging.info(f"🔍 Выбран пользователь из списка: {user_id} (админ: {callback.from_user.id})")
        
        user = await user_service.get_user_by_id(user_id)
        if not user:
            await callback.answer("❌ Пользователь не найден", show_alert=True)
            return
        
        # Используем find_and_show_user для отображения
        await callback.message.delete()  # Удаляем список
        await find_and_show_user(callback.message, user=user)
        await callback.answer()
        
    except Exception as e:
        logging.error(f"Ошибка выбора пользователя из списка: {e}", exc_info=True)
        await callback.answer("❌ Ошибка", show_alert=True)


async def find_and_show_user(message: Message, user_id: int = None, user: User = None):
    """Поиск и отображение информации о пользователе"""
    try:
        async with AsyncSessionLocal() as session:
            if user_id and not user:
                user = await session.get(User, user_id)
                logging.info(f"🔍 Поиск пользователя по ID: {user_id}, найден: {user is not None}")

            if not user:
                logging.warning(f"❌ Пользователь не найден: user_id={user_id}, user={user}")
                await message.answer(
                    "❌ Пользователь не найден в базе данных.\n\n"
                    "💡 Убедитесь, что пользователь использовал бота хотя бы раз (/start)."
                )
                return

            # ✅ СОХРАНЯЕМ ВЫБРАННОГО ПОЛЬЗОВАТЕЛЯ
            selected_users[message.from_user.id] = user.id

            # Получаем статистику пользователя
            profile = await user_service.get_user_profile(user.id)
            
            # Проверяем, забанен ли пользователь (профиль может быть неполным)
            is_banned = profile.get('banned', False) or user.banned

            # Получаем дополнительную информацию
            from database import Referral, Post
            from sqlalchemy import select, func
            
            # Количество рефералов в базе
            referrals_stmt = select(func.count(Referral.id)).where(Referral.referrer_id == user.id)
            referrals_result = await session.execute(referrals_stmt)
            actual_referrals = referrals_result.scalar()
            
            # Количество постов в базе
            posts_stmt = select(func.count(Post.id)).where(Post.user_id == user.id)
            posts_result = await session.execute(posts_stmt)
            actual_posts = posts_result.scalar()
            
            # Информация о реферере
            referrer_info = ""
            if user.referrer_id:
                referrer = await session.get(User, user.referrer_id)
                if referrer:
                    referrer_info = f"👤 Реферер: @{referrer.username or 'нет'} (ID: {referrer.id})\n"
            
            # Эмодзи для привилегии
            privilege_emoji = {
                "user": "👤",
                "vip": "💎",
                "premium": "⭐",
                "god": "👑",
                "ultra_seller": "🔥"
            }
            privilege_icon = privilege_emoji.get(user.privilege, "⭐")
            
            ban_status = "🚫 ЗАБЛОКИРОВАН" if is_banned else "✅ АКТИВЕН"
            ban_icon = "🚫" if is_banned else "✅"

            text = "━━━━━━━━━━━━━━━━━━━━\n"
            text += f"👤 <b>Информация о пользователе</b>\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            text += f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            text += f"📛 <b>Username:</b> @{user.username or 'нет'}\n"
            text += f"{privilege_icon} <b>Привилегия:</b> {user.privilege.upper()}\n"
            text += f"{ban_icon} <b>Статус:</b> {ban_status}\n\n"
            
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "<b>📊 Статистика:</b>\n"
            text += f"📦 Постов: <b>{user.posts_count}</b> (в БД: {actual_posts})\n"
            text += f"👥 Рефералов: <b>{user.referrals_count}</b> (в БД: {actual_referrals})\n"
            
            # Безопасное получение cooldown (может отсутствовать для забаненных)
            cooldown = profile.get('cooldown', 0) if not is_banned else 0
            text += f"⏰ Кулдаун: <b>{cooldown}</b> мин\n\n"
            
            if referrer_info:
                text += "━━━━━━━━━━━━━━━━━━━━\n"
                text += referrer_info + "\n"
            
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "<b>📅 Даты:</b>\n"
            text += f"Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if user.last_post_time:
                text += f"Последний пост: {user.last_post_time.strftime('%d.%m.%Y %H:%M')}\n"
            else:
                text += "Последний пост: никогда\n"
            
            text += "\n💡 <i>Пользователь выбран для управления</i>"

            await message.answer(text, reply_markup=user_actions_keyboard(user.id), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка показа пользователя: {e}")
        await message.answer("❌ Ошибка загрузки информации")


# ✅ ПРОВЕРКА ВЫБРАННОГО ПОЛЬЗОВАТЕЛЯ
async def check_selected_user(callback: CallbackQuery) -> tuple:
    """Проверяет, выбран ли пользователь для управления"""
    admin_id = callback.from_user.id
    if admin_id not in selected_users:
        await callback.answer("❌ Сначала выберите пользователя через поиск", show_alert=True)
        return None, None

    user_id = selected_users[admin_id]

    # Проверяем, что пользователь все еще существует
    async with AsyncSessionLocal() as session:
        user = await session.get(User, user_id)
        if not user:
            del selected_users[admin_id]
            await callback.answer("❌ Пользователь не найден. Выберите заново.", show_alert=True)
            return None, None

    return user_id, user


# ✅ БЛОКИРОВКА/РАЗБЛОКИРОВКА
@router.callback_query(F.data.startswith("ban_"))
async def ban_user(callback: CallbackQuery):
    """Блокировка пользователя"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        user_id, user = await check_selected_user(callback)
        if not user_id:
            return

        # ✅ РЕАЛЬНАЯ БЛОКИРОВКА
        success = await user_service.ban_user(user_id)

        if success:
            # Отправляем уведомление забаненному пользователю
            try:
                from config import config
                from aiogram import Bot
                bot = Bot(token=config.BOT_TOKEN)
                await bot.send_message(
                    user_id,
                    "🚫 Вы были заблокированы администратором и не можете использовать бота."
                )
                await bot.session.close()
            except Exception as e:
                logging.error(f"Не удалось отправить уведомление о бане пользователю {user_id}: {e}")
            
            await callback.answer(f"✅ Пользователь {user_id} заблокирован")
            logging.info(f"Пользователь {user_id} заблокирован админом {callback.from_user.id}")
            # ✅ ОБНОВЛЯЕМ СООБЩЕНИЕ БЕЗ ДУБЛИРОВАНИЯ
            await update_user_info(callback, user_id)
        else:
            await callback.answer("❌ Ошибка блокировки", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка блокировки пользователя: {e}")
        await callback.answer("❌ Ошибка блокировки", show_alert=True)


@router.callback_query(F.data.startswith("unban_"))
async def unban_user(callback: CallbackQuery):
    """Разблокировка пользователя"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        user_id, user = await check_selected_user(callback)
        if not user_id:
            return

        # ✅ РЕАЛЬНАЯ РАЗБЛОКИРОВКА
        success = await user_service.unban_user(user_id)

        if success:
            await callback.answer(f"✅ Пользователь {user_id} разблокирован")
            # ✅ ОБНОВЛЯЕМ СООБЩЕНИЕ БЕЗ ДУБЛИРОВАНИЯ
            await update_user_info(callback, user_id)
        else:
            await callback.answer("❌ Ошибка разблокировки", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка разблокировки пользователя: {e}")
        await callback.answer("❌ Ошибка разблокировки", show_alert=True)


# ✅ ОБНУЛЕНИЕ АККАУНТА
@router.callback_query(F.data.startswith("reset_"))
async def reset_user_account(callback: CallbackQuery):
    """Обнуление аккаунта пользователя"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        user_id, user = await check_selected_user(callback)
        if not user_id:
            return

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                # Обнуляем статистику
                user.posts_count = 0
                user.referrals_count = 0
                user.last_post_time = None
                user.privilege = "user"
                await session.commit()

                await callback.answer(f"✅ Аккаунт пользователя {user_id} обнулен")
                await update_user_info(callback, user_id)
            else:
                await callback.answer("❌ Пользователь не найден", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка обнуления аккаунта: {e}")
        await callback.answer("❌ Ошибка обнуления", show_alert=True)


# ✅ СБРОС КУЛДАУНА
@router.callback_query(F.data.startswith("reset_cd_"))
async def reset_user_cooldown(callback: CallbackQuery):
    """Сброс кулдауна пользователя"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        user_id, user = await check_selected_user(callback)
        if not user_id:
            return

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                # ✅ ПРОВЕРЯЕМ, ЕСТЬ ЛИ КУЛДАУН ДЛЯ СБРОСА
                if not user.last_post_time:
                    await callback.answer("ℹ️ У пользователя нет активного кулдауна", show_alert=True)
                    return

                # Сбрасываем время последнего поста
                user.last_post_time = None
                await session.commit()

                await callback.answer(f"✅ Кулдаун пользователя {user_id} сброшен")
                await update_user_info(callback, user_id)
            else:
                await callback.answer("❌ Пользователь не найден", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка сброса кулдауна: {e}")
        await callback.answer("❌ Ошибка сброса", show_alert=True)


# ✅ ВЫДАЧА ПРИВИЛЕГИЙ
@router.callback_query(F.data.startswith("change_priv_"))
async def change_privilege_menu(callback: CallbackQuery):
    """Меню изменения привилегии"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        user_id, user = await check_selected_user(callback)
        if not user_id:
            return

        text = f"⭐ <b>Выбор привилегии для пользователя {user_id}</b>\n\n"
        text += "Выберите новую привилегию:"

        await callback.message.edit_text(text,
                                         reply_markup=privilege_selection_keyboard("grant", user_id),
                                         parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка меню выдачи привилегии: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("grant_"))
async def grant_privilege(callback: CallbackQuery):
    """Выдача привилегии пользователю"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        user_id, user = await check_selected_user(callback)
        if not user_id:
            return

        data = callback.data.split("_")
        privilege_type = data[1]

        if privilege_type not in config.PRIVILEGES:
            await callback.answer("❌ Неверный тип привилегии")
            return

        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                old_privilege = user.privilege
                user.privilege = privilege_type
                await session.commit()

                privilege_info = config.PRIVILEGES[privilege_type]
                await callback.answer(f"✅ Пользователю выдана привилегия: {privilege_info['label']}")

                # Обновляем информацию о пользователе
                await update_user_info(callback, user_id)
            else:
                await callback.answer("❌ Пользователь не найден", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка выдачи привилегии: {e}")
        await callback.answer("❌ Ошибка выдачи привилегии", show_alert=True)


# ✅ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
async def update_user_info(callback: CallbackQuery, user_id: int):
    """Обновляет информацию о пользователе без дублирования меню"""
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return

            profile = await user_service.get_user_profile(user.id)
            
            # Проверяем, забанен ли пользователь (профиль может быть неполным)
            is_banned = profile.get('banned', False) or user.banned

            # Получаем дополнительную информацию
            from database import Referral, Post
            from sqlalchemy import select, func
            
            # Количество рефералов в базе
            referrals_stmt = select(func.count(Referral.id)).where(Referral.referrer_id == user.id)
            referrals_result = await session.execute(referrals_stmt)
            actual_referrals = referrals_result.scalar()
            
            # Количество постов в базе
            posts_stmt = select(func.count(Post.id)).where(Post.user_id == user.id)
            posts_result = await session.execute(posts_stmt)
            actual_posts = posts_result.scalar()
            
            # Информация о реферере
            referrer_info = ""
            if user.referrer_id:
                referrer = await session.get(User, user.referrer_id)
                if referrer:
                    referrer_info = f"👤 Реферер: @{referrer.username or 'нет'} (ID: {referrer.id})\n"
            
            # Эмодзи для привилегии
            privilege_emoji = {
                "user": "👤",
                "vip": "💎",
                "premium": "⭐",
                "god": "👑",
                "ultra_seller": "🔥"
            }
            privilege_icon = privilege_emoji.get(user.privilege, "⭐")
            
            ban_status = "🚫 ЗАБЛОКИРОВАН" if is_banned else "✅ АКТИВЕН"
            ban_icon = "🚫" if is_banned else "✅"

            text = "━━━━━━━━━━━━━━━━━━━━\n"
            text += f"👤 <b>Информация о пользователе</b>\n"
            text += "━━━━━━━━━━━━━━━━━━━━\n\n"
            
            text += f"🆔 <b>ID:</b> <code>{user.id}</code>\n"
            text += f"📛 <b>Username:</b> @{user.username or 'нет'}\n"
            text += f"{privilege_icon} <b>Привилегия:</b> {user.privilege.upper()}\n"
            text += f"{ban_icon} <b>Статус:</b> {ban_status}\n\n"
            
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "<b>📊 Статистика:</b>\n"
            text += f"📦 Постов: <b>{user.posts_count}</b> (в БД: {actual_posts})\n"
            text += f"👥 Рефералов: <b>{user.referrals_count}</b> (в БД: {actual_referrals})\n"
            
            # Безопасное получение cooldown (может отсутствовать для забаненных)
            cooldown = profile.get('cooldown', 0) if not is_banned else 0
            text += f"⏰ Кулдаун: <b>{cooldown}</b> мин\n\n"
            
            if referrer_info:
                text += "━━━━━━━━━━━━━━━━━━━━\n"
                text += referrer_info + "\n"
            
            text += "━━━━━━━━━━━━━━━━━━━━\n"
            text += "<b>📅 Даты:</b>\n"
            text += f"Регистрация: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
            if user.last_post_time:
                text += f"Последний пост: {user.last_post_time.strftime('%d.%m.%Y %H:%M')}\n"
            else:
                text += "Последний пост: никогда\n"
            
            text += "\n💡 <i>Пользователь выбран для управления</i>"

            # ✅ РЕДАКТИРУЕМ СУЩЕСТВУЮЩЕЕ СООБЩЕНИЕ ВМЕСТО ОТПРАВКИ НОВОГО
            await callback.message.edit_text(text, reply_markup=user_actions_keyboard(user.id), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка обновления информации о пользователе: {e}", exc_info=True)
        await callback.answer("❌ Ошибка обновления", show_alert=True)


@router.callback_query(F.data == "back_to_user_management")
async def back_to_user_management(callback: CallbackQuery):
    """Возврат к управлению пользователями"""
    await admin_users(callback)