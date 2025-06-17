import os
import sys
import django
import logging
from django.db import transaction

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("menu_sync.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Настройка Django-окружения
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')
django.setup()

# Импорт моделей после настройки Django
from menu.models import Station
from menu.sync_utils import get_dish_names, sync_station_menu

def main():
    """Основная функция синхронизации"""
    logger.info("Начало синхронизации меню")
    
    # Получаем справочник названий блюд
    dish_names = get_dish_names()
    if not dish_names:
        logger.error("Не удалось получить справочник блюд. Синхронизация прервана.")
        return
    
    # Получаем активные станции из базы данных
    stations = Station.objects.filter(is_active=True)
    if not stations:
        logger.warning("Нет активных станций в базе данных")
        return
    
    logger.info(f"Найдено {stations.count()} активных станций в базе данных")
    
    # Синхронизируем меню для каждой станции
    for station in stations:
        try:
            with transaction.atomic():
                sync_station_menu(station, dish_names)
        except Exception as e:
            logger.error(f"Ошибка при синхронизации меню для станции {station.name}: {e}")
    
    logger.info("Синхронизация меню завершена")

if __name__ == "__main__":
    main() 