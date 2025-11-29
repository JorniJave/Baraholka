# handlers/ticket_handlers.py
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging
import asyncio

from config import config
from services import UserService, TicketService, AdminService
from keyboards import (help_menu, cancel_keyboard, main_menu, ticket_themes_keyboard,
                      my_tickets_keyboard, ticket_actions_keyboard, privileges_menu,
                      start_chat_keyboard, active_chat_keyboard)
from states import TicketStates
from database import AsyncSessionLocal

router = Router()
user_service = UserService()
ticket_service = TicketService()
admin_service = AdminService()


@router.callback_query(F.data == "help")
async def show_help(callback: CallbackQuery):
    try:
        # Сначала убедимся, что пользователь существует
        await user_service.get_or_create_user(callback.from_user.id, callback.from_user.username)

        ticket_count = await ticket_service.get_tickets_count_by_status()

        text = "🎯 Выберите раздел помощи:"
        if ticket_count > 0:
            text += f"\n\n📋 У вас {ticket_count} активных тикетов"

        keyboard = help_menu()
        if ticket_count > 0:
            keyboard.inline_keyboard.insert(0, [InlineKeyboardButton(text="📋 Мои тикеты", callback_data="my_tickets")])

        await callback.message.edit_text(text, reply_markup=keyboard)
    except Exception as e:
        logging.error(f"Ошибка показа помощи для пользователя {callback.from_user.id}: {e}")
        await callback.answer("❌ Ошибка загрузки меню", show_alert=True)


@router.callback_query(F.data == "buy_privilege")
async def show_privileges_menu(callback: CallbackQuery):
    """Показывает меню выбора привилегий для покупки"""
    try:
        text = "<b>💎 Выберите привилегию для покупки:</b>\n\n"
        for privilege, info in config.PRIVILEGES.items():
            if privilege != "user":
                text += f"<b>{info['label']}</b>\n"
                text += f"⏰ Кулдаун: {info['cooldown']} мин\n"
                text += f"💰 Цена: {info['price']} руб\n\n"

        text += "ℹ️ При нажатии на привилегию автоматически создастся тикет для покупки"

        await callback.message.edit_text(text, reply_markup=privileges_menu(), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка показа меню привилегий: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data == "buy_ads")
async def show_ads_info(callback: CallbackQuery):
    """Показывает информацию о рекламе и перенаправляет на создание тикета"""
    try:
        await callback.message.edit_text(
            "<b>📢 Реклама в канале:</b>\n\n"
            "• Закрепленный пост - 500 руб/день\n"
            "• Рекламный пост - 300 руб\n"
            "• Упоминание в посте - 150 руб\n\n"
            "Для заказа рекламы создайте тикет в разделе 'Другое'",
            reply_markup=help_menu(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.answer()


@router.callback_query(F.data.startswith("buy_"))
async def create_privilege_ticket(callback: CallbackQuery):
    """Создает тикет для покупки выбранной привилегии"""
    try:
        privilege_type = callback.data.replace("buy_", "")

        if privilege_type not in config.PRIVILEGES or privilege_type == "user":
            await callback.answer("❌ Неверный тип привилегии", show_alert=True)
            return

        privilege_info = config.PRIVILEGES[privilege_type]
        theme = f"💎 Покупка привилегии {privilege_info['label']}"

        # Создаем тикет с автоматическим сообщением
        ticket = await ticket_service.create_ticket(callback.from_user.id, theme)

        # Добавляем автоматическое сообщение с информацией о привилегии
        auto_message = (
            f"🛒 Запрос на покупку привилегии\n\n"
            f"Привилегия: {privilege_info['label']}\n"
            f"Цена: {privilege_info['price']} руб\n"
            f"Кулдаун: {privilege_info['cooldown']} мин\n\n"
            f"Пользователь: @{callback.from_user.username or 'без username'}\n"
            f"ID: {callback.from_user.id}\n\n"
            f"ℹ️ Пользователь ожидает инструкции по оплате"
        )

        await ticket_service.add_message_to_ticket(ticket.id, callback.from_user.id, auto_message)

        # Уведомляем админов
        for admin_id in config.ADMIN_IDS:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"🎫 Новый тикет на покупку привилегии #{ticket.id}\n"
                    f"Привилегия: {privilege_info['label']}\n"
                    f"Цена: {privilege_info['price']} руб\n"
                    f"Пользователь: @{callback.from_user.username or 'без username'}\n"
                    f"ID: {callback.from_user.id}"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа {admin_id}: {e}")

        await callback.message.edit_text(
            f"✅ Тикет на покупку создан! Номер: #{ticket.id}\n"
            f"Привилегия: {privilege_info['label']}\n"
            f"Цена: {privilege_info['price']} руб\n\n"
            f"Администратор свяжется с вами для оформления заказа.",
            reply_markup=main_menu(callback.from_user.id, config.ADMIN_IDS)
        )

        logging.info(f"Тикет на покупку привилегии создан: #{ticket.id}, Привилегия={privilege_type}, UserID={callback.from_user.id}")

    except Exception as e:
        logging.error(f"Ошибка создания тикета на покупку: {e}")
        await callback.answer("❌ Ошибка создания тикета", show_alert=True)


@router.callback_query(F.data == "faq")
async def show_faq(callback: CallbackQuery):
    try:
        text = "<b>❓ Часто задаваемые вопросы:</b>\n\n"
        text += "• Как продать товар? - Через кнопку '💰 Продать под'\n"
        text += "• Что такое кулдаун? - Время между публикациями\n"
        text += "• Как получить VIP? - 50 постов или 20 приглашений\n"
        text += "• Проблемы с ботом? - Создайте тикет в разделе 'Другое'"

        await callback.message.edit_text(text, reply_markup=help_menu(), parse_mode="HTML")
    except Exception:
        await callback.answer()




@router.callback_query(F.data == "other")
async def show_other(callback: CallbackQuery):
    try:
        await callback.message.edit_text(
            "<b>📞 Создание тикета:</b>\n\n"
            "Выберите тему обращения:",
            reply_markup=ticket_themes_keyboard(),
            parse_mode="HTML"
        )
    except Exception:
        await callback.answer()


@router.callback_query(F.data.startswith("ticket_"))
async def create_ticket_handler(callback: CallbackQuery, state: FSMContext):
    try:
        theme_map = {
            "ticket_bot_help": "❓ Вопросы о боте",
            "ticket_ads": "📢 Купить рекламу",
            "ticket_other": "📞 Другое"
        }

        theme = theme_map.get(callback.data)
        if theme:
            await state.update_data(ticket_theme=theme)
            instruction_msg = await callback.message.answer(
                f"📝 Опишите ваш вопрос по теме '{theme}':\n\n"
                "Опишите подробно вашу проблему или вопрос, и администратор скоро ответит.",
                reply_markup=cancel_keyboard()
            )
            # Сохраняем message_id инструкции в state для последующего удаления
            await state.update_data(instruction_message_id=instruction_msg.message_id)
            await state.set_state(TicketStates.waiting_for_message)
    except Exception as e:
        logging.error(f"Ошибка создания тикета: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(TicketStates.waiting_for_message)
async def process_ticket_message(message: Message, state: FSMContext):
    try:
        data = await state.get_data()
        theme = data.get('ticket_theme')

        # Удаляем предыдущие сообщения формы
        from message_cleaner import message_cleaner
        data = await state.get_data()
        instruction_message_id = data.get('instruction_message_id')
        await message_cleaner.delete_form_messages(message.bot, message, instruction_message_id)

        ticket = await ticket_service.create_ticket(message.from_user.id, theme)
        await ticket_service.add_message_to_ticket(ticket.id, message.from_user.id, message.text)

        logging.info(f"Тикет создан: #{ticket.id}, UserID={message.from_user.id}, Тема={theme}")

        for admin_id in config.ADMIN_IDS:
            try:
                await message.bot.send_message(
                    admin_id,
                    f"🎫 Новый тикет #{ticket.id}\n"
                    f"Тема: {theme}\n"
                    f"Пользователь: @{message.from_user.username or 'без username'}\n"
                    f"ID: {message.from_user.id}"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа {admin_id}: {e}")

        await message.answer(
            f"✅ Тикет создан! Номер: #{ticket.id}\n"
            f"Тема: {theme}\n\n"
            f"Администратор ответит вам в ближайшее время.",
            reply_markup=main_menu(message.from_user.id, config.ADMIN_IDS)
        )
        await state.clear()
    except Exception as e:
        logging.error(f"Ошибка обработки тикета: {e}")
        await message.answer("❌ Ошибка создания тикета")


@router.callback_query(F.data == "my_tickets")
async def show_my_tickets(callback: CallbackQuery):
    try:
        tickets = await ticket_service.get_user_tickets(callback.from_user.id)

        if not tickets:
            await callback.message.edit_text(
                "📭 У вас пока нет тикетов.\n\n"
                "Создайте тикет через раздел Помощь/Услуги",
                reply_markup=help_menu()
            )
            return

        await callback.message.edit_text(
            "📋 Ваши тикеты:\n\n"
            "🆕 - Новый\n"
            "🔄 - В работе\n"
            "✅ - Закрыт",
            reply_markup=my_tickets_keyboard(tickets)
        )
    except Exception as e:
        logging.error(f"Ошибка показа тикетов: {e}")
        await callback.answer("❌ Ошибка загрузки тикетов", show_alert=True)


@router.callback_query(F.data.startswith("view_ticket_"))
async def view_ticket(callback: CallbackQuery):
    try:
        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket or ticket.user_id != callback.from_user.id:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        messages = await ticket_service.get_ticket_messages(ticket_id)

        text = f"🎫 Тикет #{ticket.id}\n"
        text += f"Тема: {ticket.theme}\n"
        text += f"Статус: {ticket.status}\n"
        text += f"Создан: {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        text += "💬 История сообщений:\n\n"

        for msg in messages:
            sender = "👤 Вы" if not msg.is_admin else "🛠 Админ"
            text += f"{sender} ({msg.created_at.strftime('%H:%M')}):\n{msg.message_text}\n\n"

        await callback.message.edit_text(text[:4000], reply_markup=ticket_actions_keyboard(ticket_id))
    except Exception as e:
        logging.error(f"Ошибка просмотра тикета: {e}")
        await callback.answer("❌ Ошибка загрузки тикета", show_alert=True)


@router.callback_query(F.data.startswith("close_ticket_"))
async def user_close_ticket(callback: CallbackQuery):
    try:
        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket or ticket.user_id != callback.from_user.id:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # УДАЛЕНИЕ тикета вместо закрытия
        success = await ticket_service.delete_ticket(ticket_id)

        if success:
            await callback.answer("✅ Тикет удален")
            logging.info(f"Тикет удален пользователем: #{ticket_id}, UserID={callback.from_user.id}")
            await show_my_tickets(callback)
        else:
            await callback.answer("❌ Ошибка удаления тикета", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка удаления тикета пользователем: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("start_chat_"))
async def user_start_chat(callback: CallbackQuery, state: FSMContext):
    """Пользователь принимает приглашение в чат"""
    try:
        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket or ticket.user_id != callback.from_user.id:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # Обновляем статус тикета на "в работе" если он еще новый
        if ticket.status == "new":
            await ticket_service.update_ticket_status(ticket_id, "in_progress", ticket.admin_id)

        await state.update_data(
            active_chat_ticket_id=ticket_id,
            active_chat_admin_id=ticket.admin_id,
            chat_active=True
        )

        await callback.message.edit_text(
            f"💬 <b>Чат с администратором начат</b>\n"
            f"Тикет: #{ticket_id}\n"
            f"Тема: {ticket.theme}\n\n"
            f"<i>Отправляйте сообщения - они будут пересылаться администратору.</i>\n"
            f"Для завершения чата нажмите 'Завершить чат'",
            reply_markup=active_chat_keyboard(ticket_id, is_admin=False),
            parse_mode="HTML"
        )

        # Уведомляем админа, что пользователь принял приглашение
        if ticket.admin_id:
            try:
                await callback.bot.send_message(
                    ticket.admin_id,
                    f"✅ <b>Пользователь принял приглашение в чат</b>\n"
                    f"Тикет: #{ticket_id}\n"
                    f"Пользователь: @{callback.from_user.username or 'без username'}\n\n"
                    f"<i>Теперь вы можете общаться в реальном времени</i>",
                    reply_markup=active_chat_keyboard(ticket_id, is_admin=True),
                    parse_mode="HTML"
                )

            except Exception as e:
                logging.error(f"Не удалось уведомить админа: {e}")

        await state.set_state(TicketStates.user_chat_active)

    except Exception as e:
        logging.error(f"Ошибка начала чата пользователем: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("decline_chat_"))
async def user_decline_chat(callback: CallbackQuery):
    """Пользователь отклоняет приглашение в чат"""
    try:
        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket or ticket.user_id != callback.from_user.id:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # Уведомляем админа об отказе
        if ticket.admin_id:
            try:
                await callback.bot.send_message(
                    ticket.admin_id,
                    f"❌ Пользователь отклонил приглашение в чат\n"
                    f"Тикет: #{ticket_id}\n"
                    f"Пользователь: @{callback.from_user.username or 'без username'}"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа об отказе: {e}")

        await callback.message.edit_text(
            "❌ Вы отклонили приглашение в чат\n\n"
            "Для общения с администратором используйте обычные сообщения в тикете."
        )

    except Exception as e:
        logging.error(f"Ошибка отклонения чата: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(TicketStates.user_chat_active)
async def process_user_chat_message(message: Message, state: FSMContext):
    """Обработка сообщений пользователя в активном чате"""
    try:
        data = await state.get_data()
        ticket_id = data.get('active_chat_ticket_id')
        admin_id = data.get('active_chat_admin_id')

        if not ticket_id or not admin_id:
            from message_cleaner import message_cleaner
            await message_cleaner.send_temp_message(
                message.bot,
                message.from_user.id,
                "❌ Ошибка: чат не найден",
                delete_after=5
            )
            await state.clear()
            return

        # Отправляем сообщение админу
        try:
            await message.bot.send_message(
                admin_id,
                f"👤 <b>Пользователь</b> (@{message.from_user.username or 'без username'}):\n{message.text}",
                parse_mode="HTML"
            )

            # Сохраняем сообщение в истории тикета
            await ticket_service.add_message_to_ticket(
                ticket_id,
                message.from_user.id,
                message.text,
                is_admin=False
            )

            # Отправляем временное сообщение, которое удалится через 3 секунды
            from message_cleaner import message_cleaner
            await message_cleaner.send_temp_message(
                message.bot,
                message.from_user.id,
                "✅ Сообщение отправлено",
                delete_after=3
            )

        except Exception as e:
            logging.error(f"Не удалось отправить сообщение админу: {e}")
            from message_cleaner import message_cleaner
            await message_cleaner.send_temp_message(
                message.bot,
                message.from_user.id,
                "❌ Не удалось отправить сообщение. Администратор, возможно, недоступен.",
                delete_after=5
            )

    except Exception as e:
        logging.error(f"Ошибка обработки сообщения пользователя: {e}")
        from message_cleaner import message_cleaner
        await message_cleaner.send_temp_message(
            message.bot,
            message.from_user.id,
            "❌ Ошибка отправки сообщения",
            delete_after=5
        )


@router.callback_query(F.data.startswith("end_chat_"))
async def user_end_chat(callback: CallbackQuery, state: FSMContext):
    """Пользователь завершает чат"""
    try:
        ticket_id = int(callback.data.split("_")[2])

        # Уведомляем админа о завершении чата
        data = await state.get_data()
        admin_id = data.get('active_chat_admin_id')

        if admin_id:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"💬 <b>Пользователь завершил чат</b>\n"
                    f"Тикет: #{ticket_id}",
                    parse_mode="HTML"
                )

            except Exception as e:
                logging.error(f"Не удалось уведомить админа о завершении чата: {e}")

        await callback.message.edit_text(
            "💬 <b>Чат завершен</b>",
            parse_mode="HTML"
        )
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка завершения чата пользователем: {e}")
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("cancel_chat_"))
async def user_cancel_chat(callback: CallbackQuery, state: FSMContext):
    """Пользователь отменяет чат"""
    try:
        ticket_id = int(callback.data.split("_")[2])

        # Уведомляем админа об отмене чата
        data = await state.get_data()
        admin_id = data.get('active_chat_admin_id')

        if admin_id:
            try:
                await callback.bot.send_message(
                    admin_id,
                    f"❌ Пользователь отменил чат\n"
                    f"Тикет: #{ticket_id}"
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить админа об отмене чата: {e}")

        await callback.message.edit_text("❌ Чат отменен")
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка отмены чата: {e}")
        await callback.answer("❌ Ошибка")


@router.message(Command("/"))
async def show_commands(message: Message):
    """Показывает все доступные команды при вводе /"""
    is_admin = message.from_user.id in config.ADMIN_IDS

    commands_text = """
<b>📋 Доступные команды:</b>

<code>/start</code> - Запустить бота
<code>/myid</code> - Показать ваш ID и статус
<code>/ref</code> - Реферальная система
<code>/ref_top</code> - Топ рефереров"""

    if is_admin:
        commands_text += """
<code>/admin</code> - Админ-панель"""

    commands_text += """

<b>💡 Основные функции доступны через меню бота:</b>
• <b>👤 Профиль</b> - информация о вашем аккаунте
• <b>💰 Продать под</b> - разместить объявление
• <b>🆘 Помощь/Услуги</b> - поддержка и услуги
"""

    await message.answer(commands_text, parse_mode="HTML")