from .main_handlers import router as main_router
from .post_handlers import router as post_router
from .ticket_handlers import router as ticket_router
from .ban_handlers import router as ban_router  # ✅ ДОБАВИТЬ ИМПОРТ БАН-ХЭНДЛЕРОВ
from .admin import routers as admin_routers

# Объединяем все роутеры
# ВАЖНО: Порядок имеет значение!
# 1. main_router - обрабатывает команды (/start, /myid и т.д.)
# 2. post_router, ticket_router, admin_routers - обрабатывают специфичные callback
# 3. ban_router - проверяет баны для всех остальных событий (должен быть последним)
all_routers = [
    main_router,      # Команды обрабатываются первыми
    post_router,      # Обработка продажи
    ticket_router,    # Обработка тикетов и помощи
    *admin_routers,   # Админ-панель
    ban_router,       # Проверка банов - ПОСЛЕДНИМ, чтобы не перехватывать обработанные callback
]

__all__ = ['all_routers']