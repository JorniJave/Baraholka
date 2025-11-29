import logging
from database import AsyncSessionLocal, User, Referral
from sqlalchemy import select
from aiogram import Bot


class SimpleReferralSystem:
    def __init__(self):
        self.bot_username_cache = None

    async def get_bot_username(self, bot: Bot = None):
        """Получает username бота один раз и кэширует"""
        if not self.bot_username_cache and bot:
            try:
                bot_info = await bot.get_me()
                self.bot_username_cache = bot_info.username
                logging.info(f"Bot username: {self.bot_username_cache}")
            except Exception as e:
                logging.error(f"Error getting bot username: {e}")
        return self.bot_username_cache

    def get_referral_id(self, args: str) -> int:
        """Парсит реферальный ID из аргументов команды /start"""
        try:
            logging.info(f"Parsing referral args: '{args}'")

            if not args:
                return None

            # Обрабатываем оба формата: ref_123456 и просто 123456
            if args.startswith('ref_'):
                # Формат: /start ref_123456
                ref_id_str = args[4:]  # убираем 'ref_'
                if ref_id_str.isdigit():
                    referrer_id = int(ref_id_str)
                    logging.info(f"Referral ID parsed (ref_ format): {referrer_id}")
                    return referrer_id
            elif args.isdigit():
                # Формат: /start 123456 (для обратной совместимости)
                referrer_id = int(args)
                logging.info(f"Referral ID parsed (digits only): {referrer_id}")
                return referrer_id

        except (ValueError, TypeError) as e:
            logging.error(f"Error parsing referral ID: {e}")
        return None

    async def handle_start_command(self, user_id: int, username: str, full_name: str, args: str, bot: Bot = None):
        """Обрабатывает команду /start и возвращает (user, referrer_id, is_new)"""
        referral_id = self.get_referral_id(args)
        is_new_user = False

        logging.info(f"Start command: user_id={user_id}, username={username}, args='{args}', referral_id={referral_id}")

        async with AsyncSessionLocal() as session:
            # Проверяем существующего пользователя
            user = await session.get(User, user_id)

            if not user:
                # Новый пользователь
                user = User(
                    id=user_id,
                    username=username or "без username",
                    referrer_id=referral_id
                )
                session.add(user)
                await session.commit()
                is_new_user = True
                logging.info(f"New user created: {user_id} with referrer: {referral_id}")

                # Обрабатываем реферала если есть refer_id
                if referral_id:
                    success = await self.add_referral(referral_id, user_id)
                    if success and bot:
                        # Отправляем уведомление рефереру
                        await self.notify_referrer(bot, referral_id, user_id, username, full_name)
                    else:
                        logging.error(f"Failed to add referral: {referral_id} -> {user_id}")
            else:
                # Обновляем username если изменился
                current_username = username or "без username"
                if user.username != current_username:
                    user.username = current_username
                    await session.commit()
                    logging.info(f"User username updated: {user_id} -> @{current_username}")

            return user, referral_id, is_new_user

    async def add_referral(self, referrer_id: int, referred_id: int) -> bool:
        """Добавляет реферала и увеличивает счетчик у реферера"""
        async with AsyncSessionLocal() as session:
            try:
                # Проверяем что реферер существует
                referrer = await session.get(User, referrer_id)
                if not referrer:
                    logging.error(f"Referrer {referrer_id} not found in database")
                    return False

                # Проверяем что реферал еще не был добавлен
                existing_stmt = select(Referral).where(Referral.referred_id == referred_id)
                existing_result = await session.execute(existing_stmt)
                existing = existing_result.scalar_one_or_none()

                if existing:
                    logging.info(f"Referral already exists: {referrer_id} -> {referred_id}")
                    return True

                # Создаем запись о реферале
                referral = Referral(
                    referrer_id=referrer_id,
                    referred_id=referred_id
                )
                session.add(referral)

                # Обновляем счетчик у реферера
                referrer.referrals_count += 1

                # Автоматический VIP за 20 рефералов
                if referrer.referrals_count >= 20 and referrer.privilege == "user":
                    referrer.privilege = "vip"
                    logging.info(f"User {referrer_id} got VIP for 20 referrals")

                await session.commit()
                logging.info(
                    f"Referral added successfully: {referrer_id} -> {referred_id}, total: {referrer.referrals_count}")
                return True

            except Exception as e:
                logging.error(f"Error adding referral {referrer_id} -> {referred_id}: {e}")
                await session.rollback()
                return False

    async def notify_referrer(self, bot: Bot, referrer_id: int, new_user_id: int, new_username: str,
                              new_full_name: str):
        """Уведомляет реферера о новом реферале с улучшенным форматированием"""
        try:
            # Получаем статистику реферера
            stats = await self.get_referral_stats(referrer_id)

            # Форматируем информацию о новом пользователе
            user_info = f"👤 {new_full_name}"
            if new_username and new_username != "без username":
                user_info += f" (@{new_username})"
            user_info += f"\n🆔 ID: `{new_user_id}`"

            # Форматируем статистику
            stats_info = (
                f"📊 Ваша статистика:\n"
                f"• Всего рефералов: {stats['total_referrals']}\n"
                f"• До VIP: {stats['needed_for_vip']}"
            )

            message = (
                "🎉 <b>Новый реферал!</b>\n\n"
                f"{user_info}\n\n"
                f"{stats_info}"
            )

            await bot.send_message(referrer_id, message, parse_mode="HTML")
            logging.info(f"📩 Notification sent to referrer {referrer_id} about new referral {new_user_id}")

        except Exception as e:
            logging.error(f"Failed to notify referrer {referrer_id}: {e}")

    async def generate_referral_link(self, user_id: int, bot: Bot = None) -> str:
        """Генерирует реферальную ссылку в формате ref_123456"""
        bot_username = await self.get_bot_username(bot)
        if not bot_username:
            return "❌ Ошибка: username бота не найден"

        link = f"https://t.me/{bot_username}?start=ref_{user_id}"
        logging.info(f"Generated referral link for {user_id}: {link}")
        return link

    async def get_referral_link(self, user_id: int, bot: Bot = None) -> str:
        """Алиас для generate_referral_link для совместимости"""
        return await self.generate_referral_link(user_id, bot)

    async def get_referral_stats(self, user_id: int) -> dict:
        """Получает статистику рефералов"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return {'total_referrals': 0, 'needed_for_vip': 20}

            return {
                'total_referrals': user.referrals_count,
                'needed_for_vip': max(0, 20 - user.referrals_count)
            }

    async def get_detailed_referral_stats(self, user_id: int) -> dict:
        """Получает детальную статистику рефералов со списком"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return {
                    'total_referrals': 0,
                    'needed_for_vip': 20,
                    'referrals_list': [],
                    'vip_progress': "0/20"
                }

            # Получаем список рефералов
            stmt = select(Referral).where(Referral.referrer_id == user_id).order_by(Referral.created_at.desc())
            result = await session.execute(stmt)
            referrals = result.scalars().all()

            referrals_list = []
            for ref in referrals:
                # Получаем информацию о реферале
                ref_user = await session.get(User, ref.referred_id)
                username = ref_user.username if ref_user else "неизвестно"
                referrals_list.append({
                    'user_id': ref.referred_id,
                    'username': username,
                    'joined_at': ref.created_at.strftime('%d.%m.%Y %H:%M')
                })

            return {
                'total_referrals': user.referrals_count,
                'needed_for_vip': max(0, 20 - user.referrals_count),
                'referrals_list': referrals_list,
                'vip_progress': f"{min(user.referrals_count, 20)}/20"
            }

    async def get_leaderboard(self, limit: int = 10):
        """Топ рефереров"""
        async with AsyncSessionLocal() as session:
            from sqlalchemy import desc

            stmt = (
                select(User)
                .where(User.referrals_count > 0)
                .order_by(desc(User.referrals_count))
                .limit(limit)
            )

            result = await session.execute(stmt)
            users = result.scalars().all()

            return [
                {
                    'user_id': user.id,
                    'username': user.username or "без username",
                    'referrals_count': user.referrals_count,
                    'privilege': user.privilege
                }
                for user in users
            ]

    async def check_and_update_vip_status(self, user_id: int) -> bool:
        """Проверяет и обновляет VIP статус по рефералам"""
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            if not user:
                return False

            # Проверяем условия для VIP
            if user.referrals_count >= 20 and user.privilege == "user":
                user.privilege = "vip"
                await session.commit()
                logging.info(f"User {user_id} automatically promoted to VIP for {user.referrals_count} referrals")
                return True

            return False

    async def get_user_referral_info(self, user_id: int, bot: Bot = None) -> dict:
        """Полная информация о реферальной системе для пользователя"""
        stats = await self.get_detailed_referral_stats(user_id)
        referral_link = await self.generate_referral_link(user_id, bot)

        return {
            **stats,
            'referral_link': referral_link,
            'referral_example': f"/start ref_{user_id}",
            'can_get_vip': stats['total_referrals'] >= 20
        }


# Глобальный экземпляр
simple_referral = SimpleReferralSystem()