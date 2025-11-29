from .main import router as admin_main_router
from .users import router as admin_users_router
from .tickets import router as admin_tickets_router
from .privileges import router as admin_privileges_router
from .settings import router as admin_settings_router

# Объединяем все админ-роутеры
routers = [
    admin_main_router,
    admin_users_router,
    admin_tickets_router,
    admin_privileges_router,
    admin_settings_router
]

__all__ = ['routers']