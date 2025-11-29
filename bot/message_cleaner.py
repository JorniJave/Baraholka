"""
Утилита для автоматической очистки сообщений бота
"""
import asyncio
import logging
from typing import Dict, Optional
from aiogram import Bot
from aiogram.types import Message, CallbackQuery


class MessageCleaner:
    """Класс для управления автоудалением сообщений бота"""
    
    def __init__(self, auto_delete_delay: int = 30):
        """
        Args:
            auto_delete_delay: Задержка в секундах перед автоматическим удалением (0 = отключено)
        """
        self.last_messages: Dict[int, int] = {}  # {user_id: message_id}
        self.auto_delete_delay = auto_delete_delay
        self.delete_tasks: Dict[int, asyncio.Task] = {}  # {message_id: task}
    
    async def send_and_clean(self, bot: Bot, user_id: int, text: str, **kwargs) -> Optional[Message]:
        """
        Отправляет сообщение и удаляет предыдущее сообщение бота для этого пользователя
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            text: Текст сообщения
            **kwargs: Дополнительные параметры для send_message
        
        Returns:
            Отправленное сообщение или None при ошибке
        """
        try:
            # Удаляем предыдущее сообщение, если есть
            if user_id in self.last_messages:
                old_message_id = self.last_messages[user_id]
                try:
                    await bot.delete_message(chat_id=user_id, message_id=old_message_id)
                except Exception as e:
                    # Игнорируем ошибки удаления (сообщение может быть уже удалено)
                    pass
            
            # Отправляем новое сообщение
            message = await bot.send_message(chat_id=user_id, text=text, **kwargs)
            
            # Сохраняем ID нового сообщения
            self.last_messages[user_id] = message.message_id
            
            # Запускаем задачу автоудаления, если включено
            if self.auto_delete_delay > 0:
                task = asyncio.create_task(
                    self._auto_delete_message(bot, user_id, message.message_id)
                )
                self.delete_tasks[message.message_id] = task
            
            return message
            
        except Exception as e:
            logging.error(f"Ошибка отправки сообщения с автоочисткой: {e}")
            return None
    
    async def _auto_delete_message(self, bot: Bot, user_id: int, message_id: int):
        """Автоматически удаляет сообщение через заданное время"""
        try:
            await asyncio.sleep(self.auto_delete_delay)
            await bot.delete_message(chat_id=user_id, message_id=message_id)
            
            # Удаляем из кэша, если это было последнее сообщение
            if self.last_messages.get(user_id) == message_id:
                del self.last_messages[user_id]
            
            # Удаляем задачу из списка
            if message_id in self.delete_tasks:
                del self.delete_tasks[message_id]
                
        except Exception as e:
            # Игнорируем ошибки (сообщение может быть уже удалено)
            pass
    
    async def delete_user_message(self, bot: Bot, user_id: int, message_id: int):
        """Удаляет конкретное сообщение пользователя"""
        try:
            await bot.delete_message(chat_id=user_id, message_id=message_id)
            if self.last_messages.get(user_id) == message_id:
                del self.last_messages[user_id]
        except Exception:
            pass
    
    def clear_user_cache(self, user_id: int):
        """Очищает кэш сообщений для пользователя"""
        if user_id in self.last_messages:
            del self.last_messages[user_id]
    
    async def send_temp_message(self, bot: Bot, user_id: int, text: str, delete_after: int = 5, **kwargs) -> Optional[Message]:
        """
        Отправляет временное сообщение, которое будет удалено через указанное время
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            text: Текст сообщения
            delete_after: Время в секундах до удаления (по умолчанию 5)
            **kwargs: Дополнительные параметры для send_message
        
        Returns:
            Отправленное сообщение или None при ошибке
        """
        try:
            message = await bot.send_message(chat_id=user_id, text=text, **kwargs)
            
            # Запускаем задачу удаления
            asyncio.create_task(self._delete_after_delay(bot, user_id, message.message_id, delete_after))
            
            return message
        except Exception as e:
            logging.error(f"Ошибка отправки временного сообщения: {e}")
            return None
    
    async def _delete_after_delay(self, bot: Bot, user_id: int, message_id: int, delay: int):
        """Удаляет сообщение через указанное время"""
        try:
            await asyncio.sleep(delay)
            await bot.delete_message(chat_id=user_id, message_id=message_id)
        except Exception:
            pass
    
    async def delete_form_messages(self, bot: Bot, message: Message, instruction_message_id: int = None):
        """
        Удаляет предыдущие сообщения формы (инструкцию от бота и сообщение пользователя)
        
        Args:
            bot: Экземпляр бота
            message: Сообщение пользователя с данными формы
            instruction_message_id: ID сообщения с инструкцией (если сохранено в state)
        """
        try:
            # Удаляем сообщение с инструкцией (из state или reply_to_message)
            if instruction_message_id:
                try:
                    # Небольшая задержка для надежности
                    import asyncio
                    await asyncio.sleep(0.3)
                    await bot.delete_message(
                        chat_id=message.from_user.id,
                        message_id=instruction_message_id
                    )
                except Exception as e:
                    # Логируем для отладки
                    logging.debug(f"Не удалось удалить инструкцию {instruction_message_id}: {e}")
                    pass
            elif message.reply_to_message and message.reply_to_message.from_user.id == bot.id:
                try:
                    await bot.delete_message(
                        chat_id=message.from_user.id,
                        message_id=message.reply_to_message.message_id
                    )
                except Exception:
                    pass
            
            # Удаляем сообщение пользователя
            try:
                await bot.delete_message(
                    chat_id=message.from_user.id,
                    message_id=message.message_id
                )
            except Exception:
                pass
        except Exception:
            pass
    
    async def delete_command_message(self, bot: Bot, message: Message):
        """Удаляет сообщение с командой пользователя"""
        try:
            # Небольшая задержка, чтобы убедиться, что сообщение обработано
            import asyncio
            await asyncio.sleep(0.5)
            await bot.delete_message(
                chat_id=message.from_user.id,
                message_id=message.message_id
            )
        except Exception as e:
            # Игнорируем ошибки (сообщение может быть уже удалено или недоступно)
            pass
    
    async def delete_multiple_messages(self, bot: Bot, user_id: int, message_ids: list):
        """
        Удаляет несколько сообщений
        
        Args:
            bot: Экземпляр бота
            user_id: ID пользователя
            message_ids: Список message_id для удаления
        """
        for message_id in message_ids:
            try:
                await bot.delete_message(
                    chat_id=user_id,
                    message_id=message_id
                )
            except Exception:
                # Игнорируем ошибки (сообщение может быть уже удалено)
                pass


# Глобальный экземпляр (настраивается через config)
from config import config
message_cleaner = MessageCleaner(auto_delete_delay=config.AUTO_DELETE_DELAY)

