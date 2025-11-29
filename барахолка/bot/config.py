# config.py
import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")

    # Исправляем парсинг ADMIN_IDS
    ADMIN_IDS = []
    admin_ids_str = os.getenv("ADMIN_IDS", "")

    if admin_ids_str:
        try:
            ADMIN_IDS = [int(x.strip()) for x in admin_ids_str.split(",") if x.strip()]
        except ValueError as e:
            print(f"Ошибка парсинга ADMIN_IDS: {e}")

    CHANNEL_ID = os.getenv("CHANNEL_ID")

    # Привилегии и кулдауны
    PRIVILEGES = {
        "user": {"cooldown": 60, "price": 0, "label": "User"},
        "vip": {"cooldown": 40, "price": 50, "label": "VIP"},
        "premium": {"cooldown": 30, "price": 120, "label": "PREMIUM"},
        "god": {"cooldown": 20, "price": 500, "label": "GOD"},
        "ultra_seller": {"cooldown": 10, "price": 1500, "label": "ULTRA SELLER"}
    }


config = Config()


