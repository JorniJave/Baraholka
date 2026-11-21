@echo off
echo 🚀 Запуск бота Baraholka...
echo.

REM Проверка виртуального окружения
if not exist "venv\Scripts\activate.bat" (
    echo ❌ Виртуальное окружение не найдено!
    echo 💡 Создайте виртуальное окружение: python -m venv venv
    pause
    exit /b 1
)

REM Проверка файла .env
if not exist ".env" (
    echo ❌ Файл .env не найден!
    echo 💡 Создайте файл .env с BOT_TOKEN, ADMIN_IDS, CHANNEL_ID
    pause
    exit /b 1
)

REM Активация виртуального окружения и запуск бота
echo ✅ Активация виртуального окружения...
call venv\Scripts\activate.bat
python bot.py
pause


