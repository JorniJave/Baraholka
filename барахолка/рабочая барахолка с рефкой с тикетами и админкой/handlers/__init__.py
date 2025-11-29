from .main_handlers import router as main_router
from .post_handlers import router as post_router
from .ticket_handlers import router as ticket_router
from .ban_handlers import router as ban_router  # ✅ ДОБАВИТЬ ИМПОРТ БАН-ХЭНДЛЕРОВ
from .admin import routers as admin_routers

# Объединяем все роутеры
all_routers = [
    ban_router,  # ✅ ДОБАВИТЬ ПЕРВЫМ для глобальной проверки банов
    main_router,
    post_router,
    ticket_router,
    *admin_routers
]

__all__ = ['all_routers']