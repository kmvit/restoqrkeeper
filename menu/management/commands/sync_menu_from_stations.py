from django.core.management.base import BaseCommand
import os
import sys
import django
import logging
from datetime import datetime
import requests
import xml.etree.ElementTree as ET
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import warnings
import ssl
from django.db import transaction
from django.utils import timezone
from django.conf import settings
from menu.models import Station, Category, MenuItem

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

# Отключаем предупреждения SSL
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

class CustomAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ssl_version=ssl.PROTOCOL_SSLv23)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('ALL:@SECLEVEL=0')
        kwargs['ssl_context'] = context
        return super(CustomAdapter, self).init_poolmanager(*args, **kwargs)

# Настройка сессии с retry-логикой
session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
adapter = CustomAdapter(max_retries=retry)
session.mount('http://', adapter)
session.mount('https://', adapter)

# Конфигурация из .env
base_url = os.environ.get('RKEEPER_API_URL')

def get_dish_names():
    """Получает справочник названий блюд"""
    logger.info("Получение справочника блюд из R-Keeper")
    xml_query = '''<?xml version="1.0" encoding="utf-8"?>
    <RK7Query>
        <RK7Command CMD="GetRefData" RefName="MenuItems" onlyActive="1">
            <PROPFILTER>
                <PROP name="ItemIdent"/>
                <PROP name="Code"/>
                <PROP name="Name"/>
                <PROP name="Status"/>
                <PROP name="MainParentIdent"/>
                <PROP name="Price"/>
                <PROP name="Quantity"/>
                <PROP name="Available"/>
                <PROP name="RecipeText"/>
                <PROP name="RecipeIngredients"/>
                <PROP name="CategPath"/>
            </PROPFILTER>
            <FILTER>
                <EQ FieldName="ItemKind" Value="1"/>
            </FILTER>
        </RK7Command>
    </RK7Query>'''
    
    try:
        response = session.post(
            base_url,
            data=xml_query.encode('utf-8'),
            verify=False,
            headers={'Content-Type': 'application/xml'}
        )
        response.raise_for_status()
        
        # Парсим ответ и создаем словарь {код: название}
        root = ET.fromstring(response.text)
        dish_names = {}
        for item in root.findall('.//Item'):
            if item.get('Status') == 'rsActive':
                category = item.get('CategPath', '').split('\\')[-1] if item.get('CategPath') else 'Без категории'
                dish_names[item.get('ItemIdent')] = {
                    'name': item.get('Name', 'Без названия'),
                    'code': item.get('Code', 'Н/Д'),
                    'recipe': item.get('RecipeText', ''),
                    'category': category
                }
        logger.info(f"Получен справочник из {len(dish_names)} позиций")
        return dish_names
    except Exception as e:
        logger.error(f"Ошибка при получении справочника блюд: {e}")
        return {}

def get_station_menu(station):
    """Получает меню для конкретной станции"""
    # Используем поле r_keeper_number из модели станции
    station_number = station.r_keeper_number
    if not station_number:
        logger.error(f"Не указан номер станции в R-Keeper для {station.name}")
        return []
    
    logger.info(f"Получение меню для станции {station.name} (номер: {station_number})")
    xml_query = f'''<?xml version="1.0" encoding="utf-8"?>
    <RK7Query>
        <RK7CMD CMD="GetOrderMenu">
            <Station code="{station_number}"/>
            <Order>
                <Table>
                    <Station code="{station_number}"/>
                </Table>
            </Order>
        </RK7CMD>
    </RK7Query>
    '''
    
    try:
        response = session.post(
            base_url,
            data=xml_query.encode('utf-8'),
            verify=False,
            headers={'Content-Type': 'application/xml'}
        )
        response.raise_for_status()
        
        # Парсим XML-ответ
        root = ET.fromstring(response.text)
        
        # Проверяем статус ответа
        status = root.get('Status')
        if status != "Ok":
            logger.error(f"Ошибка при получении меню для {station.name}: {root.get('ErrorText')}")
            return []
        
        # Получаем список блюд
        dishes = root.findall('.//Dishes/Item')
        logger.info(f"Получено {len(dishes)} позиций для станции {station.name}")
        return dishes
    except Exception as e:
        logger.error(f"Ошибка при получении меню для станции {station.name}: {e}")
        return []

def sync_station_menu(station, dish_names):
    """Синхронизирует меню для конкретной станции"""
    logger.info(f"Синхронизация меню для станции {station.name}")
    
    # Получаем меню станции
    dishes = get_station_menu(station)
    if not dishes:
        logger.warning(f"Для станции {station.name} не получено ни одной позиции меню")
        return False
    
    # Создаем словарь для хранения категорий
    categories = {}
    
    # Обрабатываем каждое блюдо
    for dish in dishes:
        ident = dish.get('Ident', 'Н/Д')
        price = float(dish.get('Price', 0)) / 100  # Конвертируем копейки в рубли
        quantity = dish.get('Quantity', 0)
        # Если количество равно 0, это означает неограниченное количество
        if quantity == 0:
            quantity = 2147483647  # Максимальное значение для IntegerField
        
        dish_info = dish_names.get(ident, {
            'name': 'Без названия',
            'code': 'Н/Д',
            'recipe': '',
            'category': 'Без категории'
        })
        
        # Получаем или создаем категорию
        category_name = dish_info['category']
        if category_name not in categories:
            category, created = Category.objects.get_or_create(
                name=category_name,
                station=station,
                defaults={'rkeeper_id': f"CAT_{category_name}"}
            )
            categories[category_name] = category
            if created:
                logger.info(f"Создана новая категория: {category_name} для станции {station.name}")
        
        # Создаем или обновляем позицию меню
        try:
            menu_item, created = MenuItem.objects.update_or_create(
                rkeeper_id=ident,
                station=station,
                defaults={
                    'name': dish_info['name'],
                    'description': dish_info['recipe'],
                    'price': price,
                    'quantity': quantity,
                    'category': categories[category_name],
                    'is_available': True,
                    'last_updated': timezone.now()
                }
            )
            if created:
                logger.info(f"Создана новая позиция меню: {dish_info['name']} для станции {station.name}")
            else:
                logger.info(f"Обновлена позиция меню: {dish_info['name']} для станции {station.name}")
        except Exception as e:
            logger.error(f"Ошибка при создании/обновлении позиции меню {dish_info['name']}: {e}")
    
    # Помечаем все позиции, которых нет в текущем меню, как недоступные
    MenuItem.objects.filter(station=station).exclude(
        rkeeper_id__in=[dish.get('Ident') for dish in dishes]
    ).update(is_available=False, last_updated=timezone.now())
    
    logger.info(f"Синхронизация меню для станции {station.name} завершена")
    return True

class Command(BaseCommand):
    help = 'Синхронизация меню из станций R-Keeper'

    def add_arguments(self, parser):
        parser.add_argument(
            '--station',
            type=str,
            help='Название станции для синхронизации (если не указано, синхронизируются все станции)'
        )

    def handle(self, *args, **options):
        # Импортируем модели после настройки Django
        from menu.models import Station, Category, MenuItem
        
        logger.info("Начало синхронизации меню")
        
        # Получаем справочник названий блюд
        dish_names = get_dish_names()
        if not dish_names:
            logger.error("Не удалось получить справочник блюд. Синхронизация прервана.")
            self.stdout.write(self.style.ERROR("Не удалось получить справочник блюд. Синхронизация прервана."))
            return
        
        # Получаем активные станции из базы данных
        if options['station']:
            stations = Station.objects.filter(name=options['station'], is_active=True)
            if not stations:
                logger.warning(f"Станция с названием {options['station']} не найдена или неактивна")
                self.stdout.write(self.style.WARNING(f"Станция с названием {options['station']} не найдена или неактивна"))
                return
        else:
            stations = Station.objects.filter(is_active=True)
            if not stations:
                logger.warning("Нет активных станций в базе данных")
                self.stdout.write(self.style.WARNING("Нет активных станций в базе данных"))
                return
        
        logger.info(f"Найдено {stations.count()} активных станций в базе данных")
        self.stdout.write(f"Найдено {stations.count()} активных станций в базе данных")
        
        # Синхронизируем меню для каждой станции
        for station in stations:
            try:
                with transaction.atomic():
                    success = sync_station_menu(station, dish_names)
                    if success:
                        self.stdout.write(self.style.SUCCESS(f"Меню станции {station.name} успешно синхронизировано"))
                    else:
                        self.stdout.write(self.style.WARNING(f"Не удалось синхронизировать меню станции {station.name}"))
            except Exception as e:
                logger.error(f"Ошибка при синхронизации меню для станции {station.name}: {e}")
                self.stdout.write(self.style.ERROR(f"Ошибка при синхронизации меню для станции {station.name}: {e}"))
        
        logger.info("Синхронизация меню завершена")
        self.stdout.write(self.style.SUCCESS("Синхронизация меню завершена")) 