import asyncio
import logging
import os
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeChat

from config import config
from database import init_db
from handlers import all_routers


# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
    handlers=[
        logging.FileHandler("baraholka.log", encoding='utf-8'),
        logging.StreamHandler()
    ]
)


async def set_bot_commands(bot: Bot):
    """Устанавливает меню команд бота"""
    # Базовые команды для всех пользователей
    commands = [
        BotCommand(command="/start", description="Запустить бота"),
        BotCommand(command="/myid", description="Показать ваш ID"),
        BotCommand(command="/ref", description="Реферальная система"),
        BotCommand(command="/ref_top", description="Топ рефереров"),
    ]

    # Добавляем команду /admin для админов
    admin_commands = commands + [
        BotCommand(command="/admin", description="Админ-панель"),
        BotCommand(command="/stats", description="Статистика бота"),
    ]

    # Устанавливаем команды для всех пользователей
    await bot.set_my_commands(commands)

    # Устанавливаем команды для каждого админа отдельно
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.set_my_commands(admin_commands, scope=BotCommandScopeChat(chat_id=admin_id))
            logging.info(f"✅ Команды админа установлены для {admin_id}")
        except Exception as e:
            logging.error(f"❌ Ошибка установки команд для админа {admin_id}: {e}")

    logging.info("✅ Меню команд бота установлено")


async def main():
    # Инициализация БД
    try:
        await init_db()
        logging.info("✅ База данных инициализирована")
    except Exception as e:
        logging.error(f"❌ Ошибка инициализации БД: {e}")
        return

    # Создание бота и диспетчера
    try:
        bot = Bot(token=config.BOT_TOKEN)
        storage = MemoryStorage()
        dp = Dispatcher(storage=storage)

        # Установка команд бота
        await set_bot_commands(bot)

        # Подключаем ВСЕ роутеры
        for router in all_routers:
            dp.include_router(router)

        logging.info("✅ Бот запущен")

        # Запуск бота в режиме polling
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())

    except Exception as e:
        logging.error(f"❌ Ошибка при работе бота: {e}")
    finally:
        if 'bot' in locals():
            await bot.session.close()
        logging.info("🛑 Бот остановлен")


if __name__ == "__main__":
    asyncio.run(main())