# config.py
import os
import logging
from pathlib import Path
from dotenv import load_dotenv

# Определяем путь к директории, где находится config.py
BASE_DIR = Path(__file__).parent.resolve()
ENV_FILE = BASE_DIR / '.env'

# Настройка логирования для config
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Загружаем .env файл с явным указанием пути
if ENV_FILE.exists():
    result = load_dotenv(ENV_FILE, override=True, encoding='utf-8')
    logger.info(f"✅ Загружен .env файл из {ENV_FILE}, результат: {result}")
    # Отладочная информация
    import os
    test_token = os.getenv("BOT_TOKEN")
    if test_token:
        logger.info(f"✅ BOT_TOKEN успешно загружен (длина: {len(test_token)})")
    else:
        logger.warning(f"⚠️  BOT_TOKEN не найден после загрузки .env")
        # Пробуем прочитать напрямую из файла
        try:
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.startswith('BOT_TOKEN='):
                        token = line.split('=', 1)[1].strip()
                        os.environ['BOT_TOKEN'] = token
                        logger.info(f"✅ BOT_TOKEN установлен напрямую из файла")
                        break
        except Exception as e:
            logger.error(f"❌ Ошибка чтения .env файла: {e}")
else:
    # Пробуем загрузить из текущей директории (для обратной совместимости)
    logger.warning(f"⚠️  .env файл не найден по пути {ENV_FILE}, пробую загрузить из текущей директории")
    load_dotenv(override=True, encoding='utf-8')


class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    
    # Проверка наличия токена
    if not BOT_TOKEN:
        import sys
        print("❌ ОШИБКА: BOT_TOKEN не найден в переменных окружения!")
        print("📝 Создайте файл .env в папке с ботом и добавьте:")
        print("   BOT_TOKEN=your_bot_token_here")
        print("\n💡 Скопируйте .env.example в .env и заполните значения")
        sys.exit(1)

    # Исправляем парсинг ADMIN_IDS с улучшенным логированием
    ADMIN_IDS = []
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    
    # Умный парсер: читаем напрямую из файла и ищем все возможные варианты записи админов
    if ENV_FILE.exists():
        try:
            import re
            with open(ENV_FILE, 'r', encoding='utf-8') as f:
                file_content = f.read()
                lines = file_content.split('\n')
                
                # Ищем строку с ADMIN_IDS
                admin_line_idx = None
                for idx, line in enumerate(lines):
                    if line.strip().startswith('ADMIN_IDS='):
                        admin_line_idx = idx
                        break
                
                if admin_line_idx is not None:
                    # Извлекаем значение из строки ADMIN_IDS=
                    admin_line = lines[admin_line_idx].strip()
                    if '=' in admin_line:
                        value_part = admin_line.split('=', 1)[1].strip()
                        # Убираем кавычки если есть
                        if (value_part.startswith('"') and value_part.endswith('"')) or \
                           (value_part.startswith("'") and value_part.endswith("'")):
                            value_part = value_part[1:-1].strip()
                        
                        # Собираем все числовые ID из этой строки и следующих строк
                        all_admin_ids = []
                        
                        # Парсим текущую строку
                        current_ids = re.findall(r'\d+', value_part)
                        all_admin_ids.extend(current_ids)
                        
                        # Проверяем следующие 3 строки на наличие числовых ID
                        for next_idx in range(admin_line_idx + 1, min(admin_line_idx + 4, len(lines))):
                            next_line = lines[next_idx].strip()
                            # Если пустая строка - пропускаем, но продолжаем
                            if not next_line:
                                continue
                            # Если комментарий - останавливаемся
                            if next_line.startswith('#'):
                                break
                            # Если новая переменная (начинается с буквы и содержит =) - останавливаемся
                            if re.match(r'^[A-Za-z_][A-Za-z0-9_]*\s*=', next_line):
                                break
                            
                            # Ищем числовые ID в этой строке
                            found_ids = re.findall(r'\d{8,}', next_line)  # ID Telegram обычно 8+ цифр
                            if found_ids:
                                all_admin_ids.extend(found_ids)
                        
                        # Если нашли больше ID, чем через dotenv - используем их
                        if len(all_admin_ids) > len(admin_ids_str.split(',')):
                            admin_ids_str = ','.join(all_admin_ids)
                        elif len(all_admin_ids) > 0:
                            # Объединяем найденные ID
                            existing_ids = [x.strip() for x in admin_ids_str.split(',') if x.strip().isdigit()]
                            all_unique_ids = list(set(existing_ids + all_admin_ids))
                            if len(all_unique_ids) > len(existing_ids):
                                admin_ids_str = ','.join(all_unique_ids)
        except Exception as e:
            logger.warning(f"⚠️  Не удалось прочитать админов из файла: {e}", exc_info=True)
    
    if admin_ids_str:
        try:
            # Сначала очищаем строку от лишних пробелов и кавычек
            admin_ids_str = admin_ids_str.strip()
            # Убираем кавычки, если они есть (одинарные или двойные)
            if (admin_ids_str.startswith('"') and admin_ids_str.endswith('"')) or \
               (admin_ids_str.startswith("'") and admin_ids_str.endswith("'")):
                admin_ids_str = admin_ids_str[1:-1].strip()
            
            # Поддерживаем разные разделители: запятая, точка с запятой, пробел, перенос строки
            # Используем регулярное выражение для более гибкого парсинга
            import re
            
            # Разбиваем по любому из разделителей (запятая, точка с запятой, пробел, таб, перенос строки)
            # и фильтруем пустые строки
            admin_ids_list = re.split(r'[,;\s\n\r\t]+', admin_ids_str)
            admin_ids_list = [x.strip() for x in admin_ids_list if x.strip()]
            
            if not admin_ids_list:
                # Если разделителей нет, пробуем как одно число
                admin_ids_list = [admin_ids_str.strip()]
            
            ADMIN_IDS = []
            for admin_id_str in admin_ids_list:
                try:
                    admin_id = int(admin_id_str)
                    ADMIN_IDS.append(admin_id)
                except ValueError:
                    logger.warning(f"⚠️  Пропущен невалидный ID админа: '{admin_id_str}' (не является числом)")
            
            if ADMIN_IDS:
                logger.info(f"✅ Загружено админов: {len(ADMIN_IDS)} ({', '.join(map(str, ADMIN_IDS))})")
        except Exception as e:
            logger.error(f"❌ Ошибка парсинга ADMIN_IDS: {e}", exc_info=True)
    else:
        logger.warning("⚠️  ADMIN_IDS не указан в переменных окружения!")

    CHANNEL_ID = os.getenv("CHANNEL_ID")

    # Привилегии и кулдауны
    PRIVILEGES = {
        "user": {"cooldown": 60, "price": 0, "label": "User"},
        "vip": {"cooldown": 40, "price": 50, "label": "VIP"},
        "premium": {"cooldown": 30, "price": 120, "label": "PREMIUM"},
        "god": {"cooldown": 20, "price": 500, "label": "GOD"},
        "ultra_seller": {"cooldown": 10, "price": 1500, "label": "ULTRA SELLER"}
    }
    
    # Настройки автоочистки сообщений
    # AUTO_DELETE_DELAY: автоматическое удаление всех сообщений через N секунд (0 = отключено)
    # По умолчанию отключено, временные уведомления удаляются через 3-5 секунд
    AUTO_DELETE_DELAY = int(os.getenv("AUTO_DELETE_DELAY", "0"))  # 0 = отключено


config = Config()
