# 🚀 Инструкция по пересозданию бота на сервере

## 📋 Шаги для пересоздания бота

### 1. Подключитесь к серверу

```bash
ssh akeqq@your_server_ip
# или через MobaXterm
```

### 2. Остановите текущий бот (если запущен)

```bash
sudo systemctl stop baraholka-bot.service
```

### 3. Переключитесь на пользователя baraholka

```bash
sudo su - baraholka
```

### 4. Удалите старую версию (опционально, если нужно полностью пересоздать)

```bash
cd ~
rm -rf Baraholka
```

### 5. Клонируйте репозиторий с веткой v1.0

```bash
cd ~
git clone https://github.com/JorniJave/Baraholka.git
cd Baraholka
git checkout v1.0
cd bot
```

### 6. Создайте виртуальное окружение

```bash
python3 -m venv venv
source venv/bin/activate
```

### 7. Установите зависимости

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 8. Создайте файл .env

```bash
nano .env
```

Добавьте в файл (замените на ваши значения):

```env
# Токен бота от @BotFather
BOT_TOKEN=your_bot_token_here

# ID администраторов (через запятую, без пробелов)
ADMIN_IDS=7628533594

# ID канала для публикации объявлений (начинается с -100)
CHANNEL_ID=-1001234567890
```

Сохраните файл: `Ctrl+O`, `Enter`, `Ctrl+X`

Установите права доступа:

```bash
chmod 600 .env
```

### 9. Тестовый запуск

```bash
source venv/bin/activate
python3 bot.py
```

Если бот запустился успешно (видите логи), остановите его: `Ctrl+C`

### 10. Настройте systemd сервис

Выйдите из пользователя baraholka:

```bash
exit
```

Теперь вы под пользователем akeqq (с sudo правами).

Создайте/обновите файл сервиса:

```bash
sudo nano /etc/systemd/system/baraholka-bot.service
```

Добавьте содержимое (замените пути на ваши):

```ini
[Unit]
Description=Baraholka Telegram Bot
After=network.target

[Service]
Type=simple
User=baraholka
Group=baraholka
WorkingDirectory=/home/baraholka/Baraholka/bot
Environment="PATH=/home/baraholka/Baraholka/bot/venv/bin"
ExecStart=/home/baraholka/Baraholka/bot/venv/bin/python3 bot.py
Restart=always
RestartSec=10
StandardOutput=append:/home/baraholka/Baraholka/bot/baraholka.log
StandardError=append:/home/baraholka/Baraholka/bot/baraholka.log

[Install]
WantedBy=multi-user.target
```

### 11. Активируйте и запустите сервис

```bash
# Перезагрузить systemd
sudo systemctl daemon-reload

# Включить автозапуск при загрузке системы
sudo systemctl enable baraholka-bot.service

# Запустить сервис
sudo systemctl start baraholka-bot.service

# Проверить статус
sudo systemctl status baraholka-bot.service
```

### 12. Проверьте логи

```bash
# Просмотр логов в реальном времени
sudo journalctl -u baraholka-bot.service -f

# Или последние 50 строк
sudo journalctl -u baraholka-bot.service -n 50

# Или логи из файла
tail -f /home/baraholka/Baraholka/bot/baraholka.log
```

## 🔄 Обновление бота в будущем

Если нужно обновить бота до новой версии:

```bash
# Остановить бот
sudo systemctl stop baraholka-bot.service

# Переключиться на пользователя baraholka
sudo su - baraholka

# Перейти в директорию проекта
cd ~/Baraholka

# Обновить код
git fetch origin
git checkout v1.0  # или main, или другую ветку
git pull origin v1.0

# Обновить зависимости
cd bot
source venv/bin/activate
pip install -r requirements.txt

# Выйти из пользователя
exit

# Запустить бот
sudo systemctl start baraholka-bot.service

# Проверить статус
sudo systemctl status baraholka-bot.service
```

## 🐛 Решение проблем

### Бот не запускается

```bash
# Проверьте логи
sudo journalctl -u baraholka-bot.service -n 100

# Проверьте файл .env
cat /home/baraholka/Baraholka/bot/.env

# Проверьте права доступа
ls -la /home/baraholka/Baraholka/bot/
```

### Ошибка "Permission denied"

```bash
sudo chown -R baraholka:baraholka /home/baraholka/Baraholka
chmod 600 /home/baraholka/Baraholka/bot/.env
```

### Бот постоянно перезапускается

```bash
# Проверьте логи на ошибки
sudo journalctl -u baraholka-bot.service -f

# Проверьте, не запущено ли несколько экземпляров
ps aux | grep bot.py
```

### Проблемы с базой данных

```bash
# Проверьте права на файл БД
ls -la /home/baraholka/Baraholka/bot/baraholka.db

# Если нужно пересоздать БД (ВНИМАНИЕ: удалит все данные!)
sudo su - baraholka
cd ~/Baraholka/bot
rm baraholka.db
python3 bot.py  # БД создастся автоматически
exit
```

## 📝 Полезные команды

```bash
# Просмотр статуса
sudo systemctl status baraholka-bot.service

# Остановка
sudo systemctl stop baraholka-bot.service

# Запуск
sudo systemctl start baraholka-bot.service

# Перезапуск
sudo systemctl restart baraholka-bot.service

# Просмотр логов
sudo journalctl -u baraholka-bot.service -f

# Просмотр последних 100 строк логов
sudo journalctl -u baraholka-bot.service -n 100
```

## ✅ Проверка работоспособности

После запуска проверьте:

1. Бот отвечает на команду `/start`
2. Админ-панель доступна (команда `/admin`)
3. Тикеты работают
4. Чат между админом и пользователем работает
5. Публикация постов в канал работает

---

**Готово! Бот должен быть запущен и работать на сервере.**

