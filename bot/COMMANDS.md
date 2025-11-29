# 📋 Команды для управления ботом - Памятка

## 🔍 Просмотр логов

### Просмотр последних логов (50 строк)
```bash
sudo tail -n 50 /home/baraholka/Baraholka/bot/baraholka.log
```

### Просмотр логов в реальном времени (live)
```bash
sudo tail -f /home/baraholka/Baraholka/bot/baraholka.log
```

### Просмотр логов через systemd (последние 50 строк)
```bash
sudo journalctl -u baraholka-bot.service -n 50
```

### Просмотр логов через systemd в реальном времени
```bash
sudo journalctl -u baraholka-bot.service -f
```

### Просмотр всех логов с начала
```bash
sudo journalctl -u baraholka-bot.service
```

### Просмотр логов за сегодня
```bash
sudo journalctl -u baraholka-bot.service --since today
```

### Просмотр логов за последний час
```bash
sudo journalctl -u baraholka-bot.service --since "1 hour ago"
```

---

## 🎮 Управление ботом (systemd)

### Проверить статус бота
```bash
sudo systemctl status baraholka-bot.service
```

### Запустить бота
```bash
sudo systemctl start baraholka-bot.service
```

### Остановить бота
```bash
sudo systemctl stop baraholka-bot.service
```

### Перезапустить бота
```bash
sudo systemctl restart baraholka-bot.service
```

### Включить автозапуск при загрузке сервера
```bash
sudo systemctl enable baraholka-bot.service
```

### Отключить автозапуск
```bash
sudo systemctl disable baraholka-bot.service
```

### Перезагрузить конфигурацию systemd (после изменения .service файла)
```bash
sudo systemctl daemon-reload
```

---

## 📁 Работа с файлами

### Перейти в папку бота
```bash
cd /home/baraholka/Baraholka/bot
```

### Посмотреть содержимое папки
```bash
ls -la /home/baraholka/Baraholka/bot
```

### Редактировать файл .env
```bash
sudo nano /home/baraholka/Baraholka/bot/.env
```

### Посмотреть содержимое .env (без редактирования)
```bash
sudo cat /home/baraholka/Baraholka/bot/.env
```

### Посмотреть файл логов напрямую
```bash
sudo cat /home/baraholka/Baraholka/bot/baraholka.log
```

---

## 🔧 Обновление бота

### Остановить бота
```bash
sudo systemctl stop baraholka-bot.service
```

### Перейти в папку бота
```bash
cd /home/baraholka/Baraholka/bot
```

### Обновить код с GitHub
```bash
cd /home/baraholka/Baraholka
git pull origin main
```

### Активировать виртуальное окружение
```bash
cd /home/baraholka/Baraholka/bot
source venv/bin/activate
```

### Обновить зависимости (если изменился requirements.txt)
```bash
pip install -r requirements.txt
```

### Запустить бота обратно
```bash
sudo systemctl start baraholka-bot.service
```

---

## 🐛 Отладка и диагностика

### Проверить, запущен ли процесс бота
```bash
ps aux | grep bot.py
```

### Проверить использование ресурсов
```bash
sudo systemctl status baraholka-bot.service
```

### Проверить права доступа на файлы
```bash
ls -la /home/baraholka/Baraholka/bot/
```

### Проверить, работает ли база данных
```bash
sudo ls -lh /home/baraholka/Baraholka/bot/baraholka.db
```

### Поиск ошибок в логах
```bash
sudo grep -i error /home/baraholka/Baraholka/bot/baraholka.log | tail -20
```

### Поиск предупреждений в логах
```bash
sudo grep -i warning /home/baraholka/Baraholka/bot/baraholka.log | tail -20
```

---

## 🔐 Работа с пользователем baraholka

### Переключиться на пользователя baraholka
```bash
sudo su - baraholka
```

### Выполнить команду от имени baraholka
```bash
sudo -u baraholka команда
```

---

## 📊 Полезные команды

### Посмотреть размер файла логов
```bash
sudo du -h /home/baraholka/Baraholka/bot/baraholka.log
```

### Очистить логи (осторожно!)
```bash
sudo truncate -s 0 /home/baraholka/Baraholka/bot/baraholka.log
```

### Посмотреть последние 100 строк логов с временными метками
```bash
sudo tail -n 100 /home/baraholka/Baraholka/bot/baraholka.log
```

### Проверить, слушает ли бот обновления (должен быть активен)
```bash
sudo systemctl is-active baraholka-bot.service
```

### Проверить, включен ли автозапуск
```bash
sudo systemctl is-enabled baraholka-bot.service
```

---

## 🚨 Быстрая помощь при проблемах

### Бот не запускается
```bash
# 1. Проверить статус
sudo systemctl status baraholka-bot.service

# 2. Посмотреть логи
sudo journalctl -u baraholka-bot.service -n 50

# 3. Проверить .env файл
sudo cat /home/baraholka/Baraholka/bot/.env
```

### Бот упал и не перезапускается
```bash
# 1. Проверить логи на ошибки
sudo journalctl -u baraholka-bot.service -n 100 | grep -i error

# 2. Перезапустить вручную
sudo systemctl restart baraholka-bot.service

# 3. Проверить статус
sudo systemctl status baraholka-bot.service
```

### Нужно обновить конфигурацию
```bash
# 1. Остановить бота
sudo systemctl stop baraholka-bot.service

# 2. Отредактировать .env
sudo nano /home/baraholka/Baraholka/bot/.env

# 3. Запустить обратно
sudo systemctl start baraholka-bot.service
```

---

## 📝 Примечания

- Все команды с `sudo` требуют прав администратора
- Логи бота пишутся в `/home/baraholka/Baraholka/bot/baraholka.log`
- Бот работает от пользователя `baraholka`
- Сервис называется `baraholka-bot.service`
- После изменения `.env` нужно перезапустить бота

---

**Создано для удобного управления ботом Baraholka**

