# Baraholka

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.x-green.svg)](https://docs.aiogram.dev/)
[![Telegram](https://img.shields.io/badge/Telegram-Bot-26A5E4?logo=telegram&logoColor=white)](https://telegram.org/)
[![License](https://img.shields.io/badge/License-Private-red.svg)](#)

Telegram-бот для канала-барахолки: публикация объявлений, привилегии, тикеты поддержки и реферальная программа.

## Возможности

- 🛒 Пошаговые объявления (фото, название, цена, описание)  
- ⏰ Кулдауны между постами по уровню привилегии  
- 💎 Несколько уровней привилегий  
- 🎫 Тикет-система с приоритетами  
- 🔗 Рефералка (например VIP за N рефералов)  
- 👑 Админ-панель: пользователи, тикеты, привилегии, статистика  
- 🚫 Баны / разбаны  

## Быстрый старт

```bash
git clone https://github.com/JorniJave/Baraholka.git
cd Baraholka/bot
pip install -r requirements.txt
```

Создайте `bot/.env` (файл в gitignore):

```env
BOT_TOKEN=your_bot_token_here
ADMIN_IDS=123456789,987654321
CHANNEL_ID=-1001234567890
```

Запуск — см. скрипты в `bot/`:

```bash
# Windows
.\start_bot.ps1
# или
.\start_bot.bat

# проверка / остановка
.\check_bot.ps1
.\stop_bot.ps1
```

Инструкция по пересозданию на сервере: `bot/DEPLOY_SERVER.md`.

## Структура

```
bot/
  handlers/     # пользовательские и админ-хендлеры
  *.py          # конфиг, рефералка, cleaner
  start_bot.*   # удобный запуск
  DEPLOY_SERVER.md
```

## Безопасность

- Реальные токены и ID только в локальном `.env`  
- Не публикуйте дампы БД и логи чатов  

## Лицензия

Private / personal project
