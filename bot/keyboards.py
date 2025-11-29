# keyboards.py
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from config import config


def main_menu(user_id: int = None, admin_ids: list = None):
    """Главное меню с проверкой админки"""
    keyboard = [
        [InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="💰 Продать под", callback_data="sell")],
        [InlineKeyboardButton(text="🆘 Помощь/Услуги", callback_data="help")]
    ]

    # Добавляем админ-панель только для админов
    if user_id and admin_ids and user_id in admin_ids:
        keyboard.append([InlineKeyboardButton(text="⚙️ Админ панель", callback_data="admin_main")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def help_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💎 Купить привилегию", callback_data="buy_privilege")],
            [InlineKeyboardButton(text="❓ Вопросы о боте", callback_data="faq")],
            [InlineKeyboardButton(text="📞 Другое", callback_data="other")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="main")]
        ]
    )


def privileges_menu():
    """Меню выбора привилегий для покупки"""
    keyboard = []
    for privilege, info in config.PRIVILEGES.items():
        if privilege != "user":
            button_text = f"{info['label']} - {info['price']} руб"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"buy_{privilege}")])

    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="help")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cancel_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def confirm_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Подтвердить", callback_data="confirm")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data="cancel")]
        ]
    )


def admin_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
            [InlineKeyboardButton(text="🎫 Управление тикетами", callback_data="admin_tickets")],
            [InlineKeyboardButton(text="⚙️ Настройки привилегий", callback_data="admin_privileges")],
            [InlineKeyboardButton(text="👥 Управление пользователями", callback_data="admin_users")],
            [InlineKeyboardButton(text="◀️ На главную", callback_data="main")]
        ]
    )


def ticket_status_keyboard():
    """Клавиатура для выбора статуса тикетов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🆕 Новые тикеты", callback_data="tickets_new")],
            [InlineKeyboardButton(text="🔄 Тикеты в работе", callback_data="tickets_in_progress")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
        ]
    )


def ticket_priority_keyboard():
    """Клавиатура для работы с приоритетами тикетов"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔴 Высокий приоритет", callback_data="priority_high")],
            [InlineKeyboardButton(text="🟡 Средний приоритет", callback_data="priority_medium")],
            [InlineKeyboardButton(text="🟢 Низкий приоритет", callback_data="priority_low")],
            [InlineKeyboardButton(text="🎫 Все тикеты", callback_data="admin_tickets")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
        ]
    )


def ticket_themes_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="❓ Вопросы о боте", callback_data="ticket_bot_help")],
            [InlineKeyboardButton(text="📢 Купить рекламу", callback_data="ticket_ads")],
            [InlineKeyboardButton(text="📞 Другое", callback_data="ticket_other")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="help")]
        ]
    )


def tickets_list_keyboard(tickets, is_admin=False, back_callback="help"):
    """Универсальная функция для списка тикетов"""
    keyboard = []
    for ticket in tickets:
        status_icon = "🆕" if ticket.status == "new" else "🔄" if ticket.status == "in_progress" else "✅"

        # ✅ ДОБАВЛЯЕМ ПРИОРИТЕТ К ТЕКСТУ КНОПКИ
        priority = get_ticket_priority(ticket.theme)
        priority_icon = get_priority_icon(priority)

        if is_admin:
            button_text = f"{priority_icon} {status_icon} #{ticket.id} - {ticket.theme}"
            callback_data = f"admin_view_ticket_{ticket.id}"
        else:
            button_text = f"{status_icon} {ticket.theme} (#{ticket.id})"
            callback_data = f"view_ticket_{ticket.id}"

        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    back_callback_data = "admin_main" if is_admin else back_callback
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback_data)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def my_tickets_keyboard(tickets):
    """Алиас для удобства"""
    return tickets_list_keyboard(tickets, is_admin=False, back_callback="help")


def admin_tickets_list_keyboard(tickets):
    """Клавиатура списка тикетов для админа"""
    keyboard = []
    for ticket in tickets:
        status_icon = "🆕" if ticket.status == "new" else "🔄" if ticket.status == "in_progress" else "✅"
        
        # Добавляем приоритет к тексту кнопки
        priority = get_ticket_priority(ticket.theme)
        priority_icon = get_priority_icon(priority)
        
        button_text = f"{priority_icon} {status_icon} #{ticket.id} - {ticket.theme}"
        callback_data = f"admin_view_ticket_{ticket.id}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])
    
    keyboard.append([InlineKeyboardButton(text="◀️ Назад к статусам", callback_data="admin_tickets")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def ticket_actions_keyboard(ticket_id, is_admin=False):
    keyboard = []
    if is_admin:
        keyboard.extend([
            [InlineKeyboardButton(text="🔄 Взять в работу", callback_data=f"admin_take_{ticket_id}")],
            [InlineKeyboardButton(text="💬 Ответить в чат", callback_data=f"reply_ticket_{ticket_id}")],
            [InlineKeyboardButton(text="✅ Закрыть тикет", callback_data=f"admin_close_{ticket_id}")],
        ])
    else:
        keyboard.append([InlineKeyboardButton(text="✅ Закрыть тикет", callback_data=f"close_ticket_{ticket_id}")])

    back_callback = "my_tickets" if not is_admin else "admin_tickets"
    keyboard.append([InlineKeyboardButton(text="◀️ Назад к тикетам", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def start_chat_keyboard(ticket_id):
    """Клавиатура для начала чата с админом"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Начать чат с админом", callback_data=f"start_chat_{ticket_id}")],
            [InlineKeyboardButton(text="❌ Отклонить", callback_data=f"decline_chat_{ticket_id}")]
        ]
    )


def active_chat_keyboard(ticket_id, is_admin=False):
    """Клавиатура для активного чата"""
    keyboard = []
    keyboard.append([InlineKeyboardButton(text="✅ Завершить чат", callback_data=f"end_chat_{ticket_id}")])
    keyboard.append([InlineKeyboardButton(text="❌ Отмена", callback_data=f"cancel_chat_{ticket_id}")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def admin_chat_invitation_keyboard(ticket_id):
    """Клавиатура для приглашения в чат от админа"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="💬 Ответить в чат", callback_data=f"admin_reply_chat_{ticket_id}")],
            [InlineKeyboardButton(text="❌ Отмена", callback_data=f"admin_cancel_chat_{ticket_id}")]
        ]
    )


def contact_seller_keyboard(seller_id: int, seller_username: str = None):
    """Кнопка для связи с продавцом - создает кнопку только если есть реальный username"""
    try:
        # Создаем кнопку ТОЛЬКО если есть валидный username (не "unknown", не None, не пустая строка)
        if seller_username and seller_username != "unknown" and seller_username != "без username" and len(
                seller_username) > 1:
            url = f"https://t.me/{seller_username}"
            button_text = f"👤 Написать (@{seller_username})"
            return InlineKeyboardMarkup(
                inline_keyboard=[
                    [InlineKeyboardButton(text=button_text, url=url)]
                ]
            )
        else:
            # Если нет валидного username - возвращаем None, чтобы использовать ID в тексте
            return None
    except Exception:
        # Если любая ошибка - возвращаем None
        return None


# ✅ КЛАВИАТУРЫ ДЛЯ УПРАВЛЕНИЯ ПРИВИЛЕГИЯМИ

def privileges_management_keyboard():
    """Главное меню управления привилегиями"""
    keyboard = []
    for privilege, info in config.PRIVILEGES.items():
        if privilege != "user":
            button_text = f"{info['label']} - {info['price']} руб"
            keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"edit_privilege_{privilege}")])

    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def privilege_edit_keyboard(privilege_type: str):
    """Клавиатура для редактирования конкретной привилегии"""
    privilege_info = config.PRIVILEGES[privilege_type]

    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"💰 Изменить цену ({privilege_info['price']} руб)",
                                  callback_data=f"set_price_{privilege_type}")],
            [InlineKeyboardButton(text=f"⏰ Изменить кулдаун ({privilege_info['cooldown']} мин)",
                                  callback_data=f"set_cooldown_{privilege_type}")],
            [InlineKeyboardButton(text="◀️ Назад к привилегиям", callback_data="admin_privileges")]
        ]
    )


def price_keyboard(privilege_type: str):
    """Клавиатура для выбора цены привилегии"""
    privilege_info = config.PRIVILEGES[privilege_type]
    current_price = privilege_info['price']

    # Предустановленные цены
    prices = [
        [50, 100, 150],
        [200, 300, 500],
        [1000, 1500, 2000]
    ]

    keyboard = []
    for row in prices:
        button_row = []
        for price in row:
            button_text = f"{price} руб"
            if price == current_price:
                button_text = f"✅ {button_text}"
            button_row.append(InlineKeyboardButton(text=button_text,
                                                   callback_data=f"apply_price_{privilege_type}_{price}"))
        keyboard.append(button_row)

    keyboard.append([InlineKeyboardButton(text="✏️ Ввести свою цену", callback_data=f"custom_price_{privilege_type}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_privilege_{privilege_type}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def cooldown_keyboard(privilege_type: str):
    """Клавиатура для выбора кулдауна привилегии"""
    privilege_info = config.PRIVILEGES[privilege_type]
    current_cooldown = privilege_info['cooldown']

    # Предустановленные кулдауны
    cooldowns = [
        [5, 10, 15],
        [20, 30, 40],
        [50, 60, 90]
    ]

    keyboard = []
    for row in cooldowns:
        button_row = []
        for cooldown in row:
            button_text = f"{cooldown} мин"
            if cooldown == current_cooldown:
                button_text = f"✅ {button_text}"
            button_row.append(InlineKeyboardButton(text=button_text,
                                                   callback_data=f"apply_cooldown_{privilege_type}_{cooldown}"))
        keyboard.append(button_row)

    keyboard.append(
        [InlineKeyboardButton(text="✏️ Ввести свой кулдаун", callback_data=f"custom_cooldown_{privilege_type}")])
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"edit_privilege_{privilege_type}")])

    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ✅ КЛАВИАТУРЫ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ

def user_management_keyboard():
    """Главное меню управления пользователями"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Найти пользователя", callback_data="find_user_menu")],
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data="ban_user_menu")],
            [InlineKeyboardButton(text="✅ Разблокировать", callback_data="unban_user_menu")],
            [InlineKeyboardButton(text="🔄 Обнулить аккаунт", callback_data="reset_user_menu")],
            [InlineKeyboardButton(text="⏰ Сбросить кулдаун", callback_data="reset_cooldown_menu")],
            [InlineKeyboardButton(text="⭐ Выдать привилегию", callback_data="grant_privilege_menu")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_main")]
        ]
    )


def user_search_keyboard():
    """Клавиатура для поиска пользователя"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔍 Поиск по ID", callback_data="search_by_id")],
            [InlineKeyboardButton(text="🔍 Поиск по username", callback_data="search_by_username")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")]
        ]
    )


def privilege_selection_keyboard(action: str, user_id: int = None):
    """Клавиатура для выбора привилегии"""
    keyboard = []
    for privilege, info in config.PRIVILEGES.items():
        button_text = f"{info['label']}"
        callback_data = f"{action}_{privilege}"
        if user_id:
            callback_data += f"_{user_id}"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=callback_data)])

    back_callback = "admin_users"
    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


# ✅ НЕДОСТАЮЩИЕ КЛАВИАТУРЫ ДЛЯ УПРАВЛЕНИЯ ПОЛЬЗОВАТЕЛЯМИ

def user_actions_keyboard(user_id: int):
    """Клавиатура действий с конкретным пользователем"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🚫 Заблокировать", callback_data=f"ban_{user_id}")],
            [InlineKeyboardButton(text="✅ Разблокировать", callback_data=f"unban_{user_id}")],
            [InlineKeyboardButton(text="🔄 Обнулить аккаунт", callback_data=f"reset_{user_id}")],
            [InlineKeyboardButton(text="⏰ Сбросить кулдаун", callback_data=f"reset_cd_{user_id}")],
            [InlineKeyboardButton(text="⭐ Изменить привилегию", callback_data=f"change_priv_{user_id}")],
            [InlineKeyboardButton(text="◀️ Назад к управлению", callback_data="admin_users")]
        ]
    )


def user_search_results_keyboard(users):
    """Клавиатура для результатов поиска пользователей"""
    keyboard = []
    for user in users:
        button_text = f"👤 @{user.username or 'без username'} (ID: {user.id})"
        keyboard.append([InlineKeyboardButton(text=button_text, callback_data=f"select_user_{user.id}")])

    keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="find_user_menu")])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)


def back_to_user_management_keyboard():
    """Клавиатура для возврата к управлению пользователями"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="◀️ Назад к управлению", callback_data="admin_users")]
        ]
    )


def user_quick_actions_keyboard(user_id: int):
    """Быстрая клавиатура действий с пользователем"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🚫 Бан", callback_data=f"ban_{user_id}"),
                InlineKeyboardButton(text="✅ Разбан", callback_data=f"unban_{user_id}")
            ],
            [
                InlineKeyboardButton(text="🔄 Обнулить", callback_data=f"reset_{user_id}"),
                InlineKeyboardButton(text="⏰ Сбросить КД", callback_data=f"reset_cd_{user_id}")
            ],
            [
                InlineKeyboardButton(text="⭐ Привилегия", callback_data=f"change_priv_{user_id}")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="admin_users")
            ]
        ]
    )


# ✅ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ ДЛЯ ПРИОРИТЕТОВ ТИКЕТОВ

def get_ticket_priority(theme):
    """Определяет приоритет тикета по теме"""
    theme_lower = theme.lower()
    if "покупка привилегии" in theme_lower or "реклам" in theme_lower or "купить" in theme_lower:
        return "high"
    elif "вопрос" in theme_lower or "бот" in theme_lower or "помощь" in theme_lower:
        return "low"
    else:
        return "medium"


def get_priority_icon(priority):
    """Возвращает иконку для приоритета"""
    icons = {
        "high": "🔴",
        "medium": "🟡",
        "low": "🟢"
    }
    return icons.get(priority, "⚪")