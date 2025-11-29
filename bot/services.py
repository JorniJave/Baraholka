# services.py
"""
Сервисы для работы с бизнес-логикой бота.
Содержит классы для работы с пользователями, постами, тикетами и админ-функциями.
"""
from aiogram import Bot
from aiogram.types import InputMediaPhoto
from database import AsyncSessionLocal, User, Post, Ticket, TicketMessage, Referral
from config import config
import datetime
import logging
from sqlalchemy import select, func, delete

from simple_referral import simple_referral


class UserService:
    async def get_or_create_user(self, user_id: int, username: str = None):
        """Создает или обновляет пользователя с актуальным username"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                # Создаем нового пользователя с реальным username
                actual_username = username or "без username"
                user = User(id=user_id, username=actual_username)
                session.add(user)
                await session.commit()
            elif user.username != username:
                # Обновляем username если он изменился
                user.username = username or "без username"
                await session.commit()
            return user

    async def get_user_profile(self, user_id: int, bot=None):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                # Если пользователь не найден, создаем его с реальным username
                actual_username = "без username"
                # Не используем bot здесь, так как он может быть не инициализирован

                user = User(id=user_id, username=actual_username)
                session.add(user)
                await session.commit()
                logging.info(f"Создан новый пользователь при запросе профиля: {user_id}")

            # Вычисляем cooldown (даже для забаненных, чтобы админы видели полную информацию)
            cooldown = await self._calculate_cooldown(user)

            # Используем новую систему для получения статистики
            try:
                ref_stats_data = await simple_referral.get_referral_stats(user_id)
                referral_link = await simple_referral.get_referral_link(user_id, bot)
            except Exception as e:
                logging.error(f"Ошибка получения реферальной статистики для {user_id}: {e}")
                ref_stats_data = {'total_referrals': 0, 'needed_for_vip': 20}
                referral_link = "Ошибка генерации ссылки"

            # Определяем реальный username пользователя
            actual_username = user.username
            if not actual_username or actual_username == "unknown":
                actual_username = "без username"

            # ✅ ВОЗВРАЩАЕМ ПОЛНЫЙ ПРОФИЛЬ ДЛЯ ВСЕХ ПОЛЬЗОВАТЕЛЕЙ (включая забаненных)
            # Это нужно для админ-панели, чтобы можно было видеть всю информацию о пользователе
            return {
                'username': actual_username,
                'user_id': user.id,
                'privilege': user.privilege,
                'cooldown': cooldown,
                'posts_count': user.posts_count,
                'referrals_count': user.referrals_count,
                'referral_link': referral_link,
                'ref_stats': ref_stats_data,
                'banned': user.banned  # ✅ ДОБАВЛЯЕМ СТАТУС БАНА
            }

    async def _calculate_cooldown(self, user):
        if user.last_post_time:
            time_passed = datetime.datetime.now() - user.last_post_time
            cooldown_minutes = config.PRIVILEGES[user.privilege]["cooldown"]
            remaining = cooldown_minutes - (time_passed.total_seconds() / 60)
            return max(0, int(remaining))
        return 0

    async def check_vip_eligibility(self, user_id: int):
        profile = await self.get_user_profile(user_id)
        return (profile['posts_count'] >= 50 or profile['referrals_count'] >= 20)

    async def update_privilege(self, user_id: int, privilege: str):
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                user.privilege = privilege
                await session.commit()

    # ✅ МЕТОДЫ ДЛЯ РАБОТЫ С БАНАМИ
    async def is_user_banned(self, user_id: int) -> bool:
        """Проверяет, забанен ли пользователь"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False
            # Явно проверяем значение banned
            is_banned = bool(user.banned) if user.banned is not None else False
            logging.info(f"Проверка бана для {user_id}: banned={user.banned}, result={is_banned}")
            return is_banned

    async def ban_user(self, user_id: int) -> bool:
        """Банит пользователя"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                user.banned = True
                await session.commit()
                logging.info(f"Пользователь забанен: {user_id}")
                return True
            return False

    async def unban_user(self, user_id: int) -> bool:
        """Разбанивает пользователя"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                user.banned = False
                await session.commit()
                logging.info(f"Пользователь разбанен: {user_id}")
                return True
            return False

    async def reset_user_account(self, user_id: int) -> bool:
        """Обнуляет аккаунт пользователя"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                user.posts_count = 0
                user.referrals_count = 0
                user.last_post_time = None
                user.privilege = "user"
                await session.commit()
                logging.info(f"Аккаунт пользователя обнулен: {user_id}")
                return True
            return False

    async def reset_user_cooldown(self, user_id: int) -> bool:
        """Сбрасывает кулдаун пользователя"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if user:
                user.last_post_time = None
                await session.commit()
                logging.info(f"Кулдаун пользователя сброшен: {user_id}")
                return True
            return False

    async def get_user_by_id(self, user_id: int):
        """Получает пользователя по ID"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            return user

    async def search_user_by_username(self, username: str):
        """Ищет пользователя по username"""
        async with AsyncSessionLocal() as session:
            stmt = select(User).where(User.username == username)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()


class PostService:
    def __init__(self):
        self._bot = None
    
    @property
    def bot(self):
        """Ленивая инициализация бота"""
        if self._bot is None:
            if not config.BOT_TOKEN:
                raise ValueError("BOT_TOKEN не установлен! Создайте файл .env с токеном бота.")
            self._bot = Bot(token=config.BOT_TOKEN)
        return self._bot

    async def create_post(self, user_id: int, data: dict):
        async with AsyncSessionLocal() as session:
            post = Post(
                user_id=user_id,
                photo_id=data['photo_ids'][0],  # Берем только первую фото
                title=data['title'],
                price=data['price'],
                description=data['description']
            )

            user = await session.get(User, user_id)
            user.posts_count += 1
            user.last_post_time = datetime.datetime.now()

            session.add(post)
            await session.commit()
            return post

    async def format_post_text(self, post_data: dict, user_privilege: str, include_contact_info: bool = False):
        privilege_label = config.PRIVILEGES[user_privilege]["label"]
        
        # Определяем цвет и стиль для привилегии
        privilege_emoji = {
            "user": "👤",
            "vip": "💎",
            "premium": "⭐",
            "god": "👑",
            "ultra_seller": "🔥"
        }
        privilege_emoji_icon = privilege_emoji.get(user_privilege, "⭐")

        # Форматируем цену для отображения
        price_display = post_data['price']
        price_line = ""

        # Если цена - "торг" или "бесплатно", показываем просто текст без "Цена:"
        if price_display.lower() == "торг":
            price_line = "🤝 <b>Торг</b>"
        elif price_display.lower() == "бесплатно":
            price_line = "🎁 <b>Бесплатно</b>"
        elif price_display.isdigit():
            # Если цена - цифры, показываем с "Цена:"
            price_line = f"💰 <b>Цена:</b> <code>{price_display}</code> ₽"
        else:
            # На всякий случай, если что-то другое
            price_line = f"💰 <b>Цена:</b> {price_display}"

        # Красивое оформление поста
        text = f"""
━━━━━━━━━━━━━━━━━━━━
<b>📦 {post_data['title']}</b>
━━━━━━━━━━━━━━━━━━━━

{price_line}

━━━━━━━━━━━━━━━━━━━━
<b>📝 Описание:</b>
━━━━━━━━━━━━━━━━━━━━

{post_data['description']}

━━━━━━━━━━━━━━━━━━━━
{privilege_emoji_icon} <b>Статус продавца:</b> {privilege_label}
━━━━━━━━━━━━━━━━━━━━
"""

        # Добавляем контактную информацию в текст поста
        if include_contact_info:
            async with AsyncSessionLocal() as session:
                user = await session.get(User, post_data['user_id'])
                seller_username = user.username if user else None

            text += f"\n💬 <b>Связаться с продавцом:</b>\n"
            text += f"🆔 ID: <code>{post_data['user_id']}</code>\n"

            # Показываем username ТОЛЬКО если он валидный и не "unknown"
            if seller_username and seller_username != "unknown" and seller_username != "без username":
                text += f"📛 @{seller_username}"
        else:
            text += "\n💬 <b>Написать продавцу:</b> Нажмите кнопку ниже ⬇️"

        return text

    async def publish_to_channel(self, post_data: dict, user_privilege: str):
        try:
            # Получаем информацию о продавце
            async with AsyncSessionLocal() as session:
                user = await session.get(User, post_data['user_id'])
                seller_username = user.username if user else None

            from keyboards import contact_seller_keyboard
            seller_keyboard = contact_seller_keyboard(post_data['user_id'], seller_username)

            # Если кнопка создалась успешно - отправляем с кнопкой
            if seller_keyboard:
                post_text = await self.format_post_text(post_data, user_privilege, include_contact_info=False)

                message = await self.bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=post_data['photo_ids'][0],
                    caption=post_text,
                    reply_markup=seller_keyboard,
                    parse_mode="HTML"
                )
            else:
                # Если кнопку создать не удалось - добавляем контактную информацию в текст
                post_text = await self.format_post_text(post_data, user_privilege, include_contact_info=True)

                message = await self.bot.send_photo(
                    chat_id=config.CHANNEL_ID,
                    photo=post_data['photo_ids'][0],
                    caption=post_text,
                    parse_mode="HTML"
                )

            # Закрепление для ULTRA SELLER
            if user_privilege == "ultra_seller":
                await self.bot.pin_chat_message(
                    chat_id=config.CHANNEL_ID,
                    message_id=message.message_id,
                    disable_notification=True
                )

            return message.message_id

        except Exception as e:
            logging.error(f"Ошибка публикации в канал: {e}")
            raise


class TicketService:
    async def create_ticket(self, user_id: int, theme: str):
        async with AsyncSessionLocal() as session:
            ticket = Ticket(user_id=user_id, theme=theme)
            session.add(ticket)
            await session.commit()
            return ticket

    async def add_message_to_ticket(self, ticket_id: int, user_id: int, message_text: str, is_admin: bool = False):
        async with AsyncSessionLocal() as session:
            message = TicketMessage(
                ticket_id=ticket_id,
                user_id=user_id,
                message_text=message_text,
                is_admin=is_admin
            )
            session.add(message)
            await session.commit()
            return message

    async def get_user_tickets(self, user_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(Ticket).where(Ticket.user_id == user_id).order_by(Ticket.created_at.desc())
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_tickets_by_status(self, status: str):
        async with AsyncSessionLocal() as session:
            stmt = select(Ticket).where(Ticket.status == status).order_by(Ticket.created_at.desc())
            result = await session.execute(stmt)
            return result.scalars().all()

    async def get_ticket_by_id(self, ticket_id: int):
        async with AsyncSessionLocal() as session:
            ticket = await session.get(Ticket, ticket_id)
            return ticket

    async def get_ticket_messages(self, ticket_id: int):
        async with AsyncSessionLocal() as session:
            stmt = select(TicketMessage).where(TicketMessage.ticket_id == ticket_id).order_by(
                TicketMessage.created_at.asc())
            result = await session.execute(stmt)
            return result.scalars().all()

    async def update_ticket_status(self, ticket_id: int, status: str, admin_id: int = None):
        async with AsyncSessionLocal() as session:
            ticket = await session.get(Ticket, ticket_id)
            if ticket:
                ticket.status = status
                if admin_id:
                    ticket.admin_id = admin_id
                await session.commit()
                return True
            return False

    async def get_tickets_count_by_status(self, status: str = None):
        async with AsyncSessionLocal() as session:
            if status:
                stmt = select(func.count(Ticket.id)).where(Ticket.status == status)
            else:
                stmt = select(func.count(Ticket.id))
            result = await session.execute(stmt)
            return result.scalar()

    async def delete_ticket(self, ticket_id: int) -> bool:
        """Удаляет тикет и все его сообщения"""
        try:
            async with AsyncSessionLocal() as session:
                # Удаляем все сообщения тикета
                stmt = delete(TicketMessage).where(TicketMessage.ticket_id == ticket_id)
                await session.execute(stmt)

                # Удаляем сам тикет
                stmt = delete(Ticket).where(Ticket.id == ticket_id)
                await session.execute(stmt)

                await session.commit()
                logging.info(f"Тикет {ticket_id} успешно удален")
                return True
        except Exception as e:
            logging.error(f"Ошибка удаления тикета {ticket_id}: {e}")
            return False


class AdminService:
    async def is_admin(self, user_id: int):
        is_admin = user_id in config.ADMIN_IDS
        logging.info(f"Проверка админа: user_id={user_id}, result={is_admin}, allowed_ids={config.ADMIN_IDS}")
        return is_admin

    async def get_statistics(self):
        async with AsyncSessionLocal() as session:
            # Количество пользователей
            users_stmt = select(func.count(User.id))
            users_result = await session.execute(users_stmt)
            users_count = users_result.scalar()

            # Количество постов
            posts_stmt = select(func.count(Post.id))
            posts_result = await session.execute(posts_stmt)
            posts_count = posts_result.scalar()

            # Количество тикетов
            tickets_stmt = select(func.count(Ticket.id))
            tickets_result = await session.execute(tickets_stmt)
            tickets_count = tickets_result.scalar()

            # ✅ КОЛИЧЕСТВО ЗАБАНЕННЫХ ПОЛЬЗОВАТЕЛЕЙ
            banned_stmt = select(func.count(User.id)).where(User.banned == True)
            banned_result = await session.execute(banned_stmt)
            banned_count = banned_result.scalar()

            return {
                'users_count': users_count,
                'posts_count': posts_count,
                'tickets_count': tickets_count,
                'banned_count': banned_count  # ✅ ДОБАВЛЯЕМ СТАТИСТИКУ БАНОВ
            }

    async def get_detailed_statistics(self):
        """Детальная статистика для админ-панели"""
        async with AsyncSessionLocal() as session:
            # Общая статистика
            total_users = await session.execute(select(func.count(User.id)))
            total_posts = await session.execute(select(func.count(Post.id)))
            total_tickets = await session.execute(select(func.count(Ticket.id)))
            banned_users = await session.execute(select(func.count(User.id)).where(User.banned == True))

            # Статистика по привилегиям
            privileges_stats = {}
            for privilege in config.PRIVILEGES.keys():
                stmt = select(func.count(User.id)).where(User.privilege == privilege)
                result = await session.execute(stmt)
                privileges_stats[privilege] = result.scalar()

            # Активные пользователи за последние 7 дней
            week_ago = datetime.datetime.now() - datetime.timedelta(days=7)
            active_users_stmt = select(func.count(User.id)).where(User.last_post_time >= week_ago)
            active_users_result = await session.execute(active_users_stmt)
            active_users = active_users_result.scalar()

            return {
                'total_users': total_users.scalar(),
                'total_posts': total_posts.scalar(),
                'total_tickets': total_tickets.scalar(),
                'banned_users': banned_users.scalar(),
                'privileges_stats': privileges_stats,
                'active_users_week': active_users
            }