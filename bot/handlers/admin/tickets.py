from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
import logging

from config import config
from services import AdminService, TicketService, UserService
from keyboards import (ticket_status_keyboard, admin_tickets_list_keyboard,
                       ticket_actions_keyboard, active_chat_keyboard, admin_chat_invitation_keyboard,
                       main_menu, start_chat_keyboard, ticket_priority_keyboard)
from states import AdminStates

router = Router()
admin_service = AdminService()
ticket_service = TicketService()
user_service = UserService()

# ✅ СЛОВАРЬ ПРИОРИТЕТОВ ТИКЕТОВ
TICKET_PRIORITIES = {
    "ticket_ads": "high",  # 📢 Купить рекламу - ВЫСОКИЙ
    "ticket_bot_help": "low",  # ❓ Вопросы о боте - НИЗКИЙ
    "ticket_other": "medium",  # 📞 Другое - СРЕДНИЙ
}


# ✅ ФУНКЦИЯ ДЛЯ ОПРЕДЕЛЕНИЯ ПРИОРИТЕТА
def get_ticket_priority(theme):
    """Определяет приоритет тикета по теме"""
    theme_lower = theme.lower()
    if "покупка привилегии" in theme_lower or "реклам" in theme_lower or "купить" in theme_lower:
        return "high"
    elif "вопрос" in theme_lower or "бот" in theme_lower or "помощь" in theme_lower:
        return "low"
    else:
        return "medium"


# ✅ ФУНКЦИЯ ДЛЯ СОРТИРОВКИ ТИКЕТОВ ПО ПРИОРИТЕТУ
async def get_tickets_by_priority(status="new"):
    """Получает тикеты отсортированные по приоритету"""
    tickets = await ticket_service.get_tickets_by_status(status)

    # Сортируем по приоритету: high -> medium -> low
    priority_order = {"high": 0, "medium": 1, "low": 2}
    tickets_sorted = sorted(tickets, key=lambda x: priority_order.get(get_ticket_priority(x.theme), 3))

    return tickets_sorted


# ✅ ФУНКЦИЯ ДЛЯ ПОЛУЧЕНИЯ ИКОНКИ ПРИОРИТЕТА
def get_priority_icon(priority):
    """Возвращает иконку для приоритета"""
    icons = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }
    return icons.get(priority, "⚪")


# ✅ ФУНКЦИЯ ДЛЯ ФОРМАТИРОВАНИЯ ОТОБРАЖЕНИЯ ПОЛЬЗОВАТЕЛЯ
def format_user_display(username: str, user_id: int) -> str:
    """Форматирует отображение пользователя (username или ID)"""
    if username and username != "без username" and username != "unknown":
        return f"@{username}"
    return f"ID: {user_id}"


@router.callback_query(F.data == "admin_tickets")
async def admin_tickets(callback: CallbackQuery):
    """Главное меню управления тикетами"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        # Получаем статистику тикетов
        new_tickets = await ticket_service.get_tickets_by_status("new")
        in_progress_tickets = await ticket_service.get_tickets_by_status("in_progress")
        
        new_count = len(new_tickets) if new_tickets else 0
        in_progress_count = len(in_progress_tickets) if in_progress_tickets else 0

        text = "🎫 <b>Управление тикетами</b>\n\n"
        text += f"🆕 <b>Новые тикеты:</b> {new_count}\n"
        text += f"🔄 <b>В работе:</b> {in_progress_count}\n\n"
        text += "💡 Выберите раздел:"

        keyboard = ticket_status_keyboard()
        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка админ тикетов: {e}")
        await callback.answer("❌ Ошибка загрузки тикетов", show_alert=True)


@router.callback_query(F.data.startswith("tickets_"))
async def admin_tickets_by_status(callback: CallbackQuery):
    """Показывает тикеты по статусу с приоритетами"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        status_map = {
            "tickets_new": "new",
            "tickets_in_progress": "in_progress"
        }

        status = status_map.get(callback.data)
        if not status:
            await callback.answer("❌ Неверный статус")
            return

        # ✅ ПОЛУЧАЕМ ОТСОРТИРОВАННЫЕ ТИКЕТЫ
        tickets = await get_tickets_by_priority(status)
        status_text = {
            "new": "🆕 Новые тикеты",
            "in_progress": "🔄 Тикеты в работе"
        }

        if not tickets:
            text = f"🎫 <b>{status_text[status]}</b>\n\n"
            text += f"Нет тикетов со статусом '{status_text[status]}'"
            keyboard = ticket_status_keyboard()
        else:
            text = f"🎫 <b>{status_text[status]}</b> ({len(tickets)}):\n\n"
            text += "🔴 <b>Высокий приоритет</b> - покупки, реклама\n"
            text += "🟡 <b>Средний приоритет</b> - другие вопросы\n"
            text += "🟢 <b>Низкий приоритет</b> - вопросы о боте\n\n"
            text += "💡 Тикеты отсортированы по приоритету"

            keyboard = admin_tickets_list_keyboard(tickets)

        await callback.message.edit_text(text, reply_markup=keyboard, parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка загрузки тикетов по статусу: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_view_ticket_"))
async def admin_view_ticket(callback: CallbackQuery):
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        # Безопасный парсинг ticket_id
        parts = callback.data.split("_")
        if len(parts) < 4:
            await callback.answer("❌ Неверный формат данных", show_alert=True)
            return
        ticket_id = int(parts[3])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        messages = await ticket_service.get_ticket_messages(ticket_id)

        # Безопасное получение username
        user_profile = await user_service.get_user_profile(ticket.user_id)
        username = user_profile.get('username', 'без username') if user_profile else "без username"

        # ✅ ОПРЕДЕЛЯЕМ ПРИОРИТЕТ ТИКЕТА
        priority = get_ticket_priority(ticket.theme)
        priority_icon = get_priority_icon(priority)
        priority_text = {
            "high": "🔴 ВЫСОКИЙ",
            "medium": "🟡 СРЕДНИЙ",
            "low": "🟢 НИЗКИЙ"
        }.get(priority, "⚪ НЕОПРЕДЕЛЕН")

        # Форматируем отображение пользователя
        user_display = format_user_display(username, ticket.user_id)
        
        text = f"🎫 <b>Тикет #{ticket.id}</b>\n\n"
        text += f"📌 <b>Приоритет:</b> {priority_icon} {priority_text}\n"
        text += f"📝 <b>Тема:</b> {ticket.theme}\n"
        text += f"📊 <b>Статус:</b> {ticket.status}\n"
        text += f"👤 <b>Пользователь:</b> {user_display}\n"
        if ticket.admin_id:
            text += f"🛠 <b>Администратор:</b> ID: {ticket.admin_id}\n"
        text += f"📅 <b>Создан:</b> {ticket.created_at.strftime('%d.%m.%Y %H:%M')}\n\n"
        text += "💬 <b>История сообщений:</b>\n\n"

        for msg in messages:
            sender = "👤 Пользователь" if not msg.is_admin else "🛠 Администратор"
            text += f"{sender} ({msg.created_at.strftime('%H:%M')}):\n{msg.message_text}\n\n"

        # Безопасное обрезание текста
        if len(text) > 4000:
            text = text[:3997] + "..."

        await callback.message.edit_text(text, reply_markup=ticket_actions_keyboard(ticket_id, is_admin=True), parse_mode="HTML")
    except Exception as e:
        logging.error(f"Ошибка админ просмотра тикета: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_take_"))
async def admin_take_ticket(callback: CallbackQuery):
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)
        
        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # Обновляем статус тикета и сохраняем admin_id
        success = await ticket_service.update_ticket_status(ticket_id, "in_progress", callback.from_user.id)

        if success:
            await callback.answer("✅ Тикет взят в работу")
            logging.info(f"Тикет взят в работу: #{ticket_id}, AdminID={callback.from_user.id}")

            # Уведомляем пользователя
            try:
                await callback.bot.send_message(
                    ticket.user_id,
                    f"🎫 Ваш тикет #{ticket_id} взят в работу администратором.\n"
                    f"Тема: {ticket.theme}\n\n"
                    f"Администратор скоро свяжется с вами."
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить пользователя {ticket.user_id}: {e}")

            # Обновляем сообщение с тикетом
            await admin_view_ticket(callback)
        else:
            await callback.answer("❌ Ошибка", show_alert=True)
    except Exception as e:
        logging.error(f"Ошибка взятия тикета: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_close_"))
async def admin_close_ticket(callback: CallbackQuery):
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # УДАЛЕНИЕ тикета вместо закрытия
        success = await ticket_service.delete_ticket(ticket_id)

        if success:
            # Уведомляем пользователя об удалении тикета
            try:
                await callback.bot.send_message(
                    ticket.user_id,
                    f"🎫 Ваш тикет #{ticket_id} был завершен и удален.\n"
                    f"Тема: {ticket.theme}\n\n"
                    f"Если у вас остались вопросы, создайте новый тикет.",
                    reply_markup=main_menu(ticket.user_id, config.ADMIN_IDS)
                )
            except Exception as e:
                logging.error(f"Не удалось уведомить пользователя {ticket.user_id}: {e}")

            await callback.answer("✅ Тикет удален")
            logging.info(f"Тикет удален админом: #{ticket_id}, AdminID={callback.from_user.id}")

            # Возвращаемся к списку тикетов
            await admin_tickets(callback)
        else:
            await callback.answer("❌ Ошибка удаления тикета", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка удаления тикета админом: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("reply_ticket_"))
async def start_ticket_reply(callback: CallbackQuery, state: FSMContext):
    """Начало ответа на тикет (для админов)"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # Убеждаемся, что тикет в работе и admin_id сохранен
        if ticket.status != "in_progress" or ticket.admin_id != callback.from_user.id:
            await ticket_service.update_ticket_status(ticket_id, "in_progress", callback.from_user.id)

        # Сохраняем данные чата в state ПЕРЕД отправкой приглашения
        await state.update_data(
            active_chat_ticket_id=ticket_id,
            active_chat_user_id=ticket.user_id,
            active_chat_admin_id=callback.from_user.id
        )

        # Отправляем приглашение пользователю начать чат
        try:
            await callback.bot.send_message(
                ticket.user_id,
                f"🎫 Администратор хочет начать чат с вами по тикету #{ticket_id}\n"
                f"Тема: {ticket.theme}\n\n"
                f"💬 Вы можете общаться в реальном времени с администратором",
                reply_markup=start_chat_keyboard(ticket_id)
            )

            # Получаем информацию о пользователе
            user_profile = await user_service.get_user_profile(ticket.user_id)
            username = user_profile.get('username', 'без username') if user_profile else 'без username'
            user_display = format_user_display(username, ticket.user_id)

            # Уведомляем админа и сразу переводим в состояние чата
            await callback.message.answer(
                f"💬 <b>Чат с пользователем начат</b>\n\n"
                f"🎫 Тикет: #{ticket_id}\n"
                f"📌 Тема: {ticket.theme}\n"
                f"👤 Пользователь: {user_display}\n\n"
                f"💬 <i>Ожидайте подтверждения от пользователя...</i>\n"
                f"Вы можете отправлять сообщения - они будут доставлены после принятия приглашения.",
                reply_markup=active_chat_keyboard(ticket_id, is_admin=True),
                parse_mode="HTML"
            )

            # Переводим админа в состояние активного чата
            await state.set_state(AdminStates.admin_chat_active)

        except Exception as e:
            logging.error(f"Не удалось отправить приглашение пользователю: {e}")
            await callback.answer("❌ Не удалось отправить приглашение", show_alert=True)

    except Exception as e:
        logging.error(f"Ошибка начала чата: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.callback_query(F.data.startswith("admin_reply_chat_"))
async def admin_start_chat(callback: CallbackQuery, state: FSMContext):
    """Админ начинает чат"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        ticket_id = int(callback.data.split("_")[3])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        if not ticket:
            await callback.answer("❌ Тикет не найден", show_alert=True)
            return

        # Убеждаемся, что тикет в работе и admin_id сохранен
        if ticket.status != "in_progress":
            await ticket_service.update_ticket_status(ticket_id, "in_progress", callback.from_user.id)

        # Сохраняем данные чата в state и обновляем тикет
        await state.update_data(
            active_chat_ticket_id=ticket_id,
            active_chat_user_id=ticket.user_id,
            active_chat_admin_id=callback.from_user.id
        )

        # Получаем информацию о пользователе
        user_profile = await user_service.get_user_profile(ticket.user_id)
        username = user_profile.get('username', 'без username') if user_profile else 'без username'
        user_display = format_user_display(username, ticket.user_id)

        await callback.message.answer(
            f"💬 <b>Чат с пользователем начат</b>\n\n"
            f"🎫 Тикет: #{ticket_id}\n"
            f"📌 Тема: {ticket.theme}\n"
            f"👤 Пользователь: {user_display}\n\n"
            f"💬 Отправляйте сообщения - они будут пересылаться пользователю.\n"
            f"Для завершения чата нажмите 'Завершить чат'",
            reply_markup=active_chat_keyboard(ticket_id, is_admin=True),
            parse_mode="HTML"
        )

        await state.set_state(AdminStates.admin_chat_active)
    except Exception as e:
        logging.error(f"Ошибка начала чата админом: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)


@router.message(AdminStates.admin_chat_active)
async def process_admin_chat_message(message: Message, state: FSMContext):
    """Обработка сообщений админа в активном чате"""
    try:
        data = await state.get_data()
        ticket_id = data.get('active_chat_ticket_id')
        user_id = data.get('active_chat_user_id')

        # Если данные отсутствуют в state, пытаемся восстановить из БД
        if not ticket_id or not user_id:
            # Ищем активный тикет, назначенный этому админу
            in_progress_tickets = await ticket_service.get_tickets_by_status("in_progress")
            admin_ticket = None
            for ticket in in_progress_tickets:
                if ticket.admin_id == message.from_user.id:
                    admin_ticket = ticket
                    break
            
            if admin_ticket:
                ticket_id = admin_ticket.id
                user_id = admin_ticket.user_id
                await state.update_data(
                    active_chat_ticket_id=ticket_id,
                    active_chat_user_id=user_id,
                    active_chat_admin_id=message.from_user.id
                )
                logging.info(f"Восстановлены данные чата из БД: TicketID={ticket_id}, UserID={user_id}")
            else:
                from message_cleaner import message_cleaner
                from keyboards import admin_menu
                await message_cleaner.send_temp_message(
                    message.bot,
                    message.from_user.id,
                    "❌ Чат был закрыт. Вы вернулись в админ-панель.",
                    delete_after=5
                )
                await message.bot.send_message(
                    message.from_user.id,
                    "⚙️ Админ-панель",
                    reply_markup=admin_menu()
                )
                await state.clear()
                return

        # Проверяем, что тикет все еще активен
        ticket = await ticket_service.get_ticket_by_id(ticket_id)
        if not ticket or ticket.status != "in_progress" or ticket.admin_id != message.from_user.id:
            from message_cleaner import message_cleaner
            from keyboards import admin_menu
            await message_cleaner.send_temp_message(
                message.bot,
                message.from_user.id,
                "❌ Чат был закрыт. Вы вернулись в админ-панель.",
                delete_after=5
            )
            await message.bot.send_message(
                message.from_user.id,
                "⚙️ Админ-панель",
                reply_markup=admin_menu()
            )
            await state.clear()
            return

        # Отправляем сообщение пользователю
        try:
            sent_message = await message.bot.send_message(
                user_id,
                f"🛠 <b>Администратор:</b>\n{message.text}",
                reply_markup=active_chat_keyboard(ticket_id, is_admin=False),
                parse_mode="HTML"
            )
            logging.info(f"✅ Сообщение от админа {message.from_user.id} отправлено пользователю {user_id}, TicketID={ticket_id}, MessageID={sent_message.message_id}")

            # Сохраняем сообщение в истории тикета
            await ticket_service.add_message_to_ticket(
                ticket_id,
                message.from_user.id,
                message.text,
                is_admin=True
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
            logging.error(f"Не удалось отправить сообщение пользователю: {e}")
            from message_cleaner import message_cleaner
            await message_cleaner.send_temp_message(
                message.bot,
                message.from_user.id,
                "❌ Не удалось отправить сообщение. Пользователь, возможно, заблокировал бота.",
                delete_after=5
            )

    except Exception as e:
        logging.error(f"Ошибка обработки сообщения админа: {e}")
        from message_cleaner import message_cleaner
        await message_cleaner.send_temp_message(
            message.bot,
            message.from_user.id,
            "❌ Ошибка отправки сообщения",
            delete_after=5
        )


@router.callback_query(F.data.startswith("end_chat_"))
async def admin_end_chat(callback: CallbackQuery, state: FSMContext):
    """Завершение чата админом"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        ticket_id = int(callback.data.split("_")[2])
        ticket = await ticket_service.get_ticket_by_id(ticket_id)

        # Получаем user_id из тикета или state
        data = await state.get_data()
        user_id = data.get('active_chat_user_id') or (ticket.user_id if ticket else None)

        # Уведомляем пользователя о завершении чата и возвращаем в главное меню
        if user_id:
            try:
                from keyboards import main_menu
                await callback.bot.send_message(
                    user_id,
                    f"💬 <b>Чат с администратором завершен</b>\n"
                    f"Тикет: #{ticket_id}\n\n"
                    f"Если у вас остались вопросы, создайте новый тикет.",
                    reply_markup=main_menu(user_id, config.ADMIN_IDS),
                    parse_mode="HTML"
                )
                logging.info(f"Пользователь {user_id} уведомлен о завершении чата админом {callback.from_user.id}")
            except Exception as e:
                logging.error(f"Не удалось уведомить пользователя о завершении чата: {e}")

        await callback.message.answer("💬 Чат завершен")
        await state.clear()

    except Exception as e:
        logging.error(f"Ошибка завершения чата: {e}")
        await callback.answer("❌ Ошибка")


@router.callback_query(F.data.startswith("admin_cancel_chat_"))
async def admin_cancel_chat(callback: CallbackQuery, state: FSMContext):
    """Отмена чата админом до начала"""
    await state.clear()
    await callback.message.answer("❌ Чат отменен")
    await callback.answer()


@router.callback_query(F.data == "tickets_by_priority")
async def tickets_by_priority(callback: CallbackQuery):
    """Показывает тикеты сгруппированные по приоритету"""
    try:
        if not await admin_service.is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        # ✅ ГРУППИРУЕМ ТИКЕТЫ ПО ПРИОРИТЕТАМ
        new_tickets = await ticket_service.get_tickets_by_status("new")

        high_priority = [t for t in new_tickets if get_ticket_priority(t.theme) == "high"]
        medium_priority = [t for t in new_tickets if get_ticket_priority(t.theme) == "medium"]
        low_priority = [t for t in new_tickets if get_ticket_priority(t.theme) == "low"]

        text = "🎫 <b>Тикеты по приоритетам</b>\n\n"
        text += f"🔴 <b>Высокий приоритет</b>: {len(high_priority)} тикетов\n"
        text += f"🟡 <b>Средний приоритет</b>: {len(medium_priority)} тикетов\n"
        text += f"🟢 <b>Низкий приоритет</b>: {len(low_priority)} тикетов\n\n"
        text += "💡 <i>Тикеты автоматически сортируются по важности</i>"

        await callback.message.edit_text(text, reply_markup=ticket_priority_keyboard(), parse_mode="HTML")

    except Exception as e:
        logging.error(f"Ошибка показа тикетов по приоритету: {e}")
        await callback.answer("❌ Ошибка", show_alert=True)