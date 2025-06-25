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
from orders.models import Waiter

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
        return [], None, None
    
    logger.info(f"Получение меню для станции {station.name} (номер: {station_number})")
    
    # Запрос для получения списка официантов
    waiters_query = '''<?xml version="1.0" encoding="utf-8"?>
    <RK7Query>
        <RK7Command CMD="GetRefData" RefName="EMPLOYEES" OnlyActive="1">
            <PROPFILTER>
                <PROP name="Ident"/>
                <PROP name="Code"/>
                <PROP name="Name"/>
                <PROP name="Status"/>
                <PROP name="MainParentIdent"/>
                <PROP name="Flags"/>
            </PROPFILTER>
        </RK7Command>
    </RK7Query>'''
    
    try:
        # Получаем список официантов
        waiters_response = session.post(
            base_url,
            data=waiters_query.encode('utf-8'),
            verify=False,
            headers={'Content-Type': 'application/xml'}
        )
        waiters_response.raise_for_status()
        
        # Логируем ответ для отладки
        logger.info(f"Ответ от R-Keeper по запросу официантов: {waiters_response.text[:1000]}")
        
        # Парсим ответ со списком официантов
        waiters_root = ET.fromstring(waiters_response.text)
        
        # Проверяем статус ответа
        status = waiters_root.get('Status')
        if status != "Ok":
            logger.error(f"Ошибка при получении списка персонала: {waiters_root.get('ErrorText')}")
            waiter_info = None
        else:
            waiters = waiters_root.findall('.//Item')
            logger.info(f"Найдено {len(waiters)} сотрудников в ответе")
            
            # Сохраняем всех найденных сотрудников
            for waiter in waiters:
                waiter_info = {
                    'code': waiter.get('Code', ''),
                    'name': waiter.get('Name', ''),
                    'guid': waiter.get('Ident', ''),
                }
                logger.info(f"Начинаем синхронизацию сотрудника: {waiter_info}")
                try:
                    waiter_obj, created = Waiter.objects.update_or_create(
                        code=waiter_info['code'],
                        defaults={
                            'name': waiter_info['name'],
                            'guid': waiter_info['guid'],
                            'is_active': True
                        }
                    )
                    if created:
                        logger.info(f"Создан новый сотрудник: {waiter_obj.name}")
                    else:
                        logger.info(f"Обновлен сотрудник: {waiter_obj.name}")
                except Exception as e:
                    logger.error(f"Ошибка при создании/обновлении сотрудника {waiter_info['name']}: {e}")
                    logger.exception("Полный стек ошибки:")
    
        # Запрос для получения меню
        menu_query = f'''<?xml version="1.0" encoding="utf-8"?>
        <RK7Query>
            <RK7CMD CMD="GetOrderMenu" onlyActive="1">
                <Station code="{station_number}"/>
                <Order>
                    <Table>
                        <Station code="{station_number}"/>
                    </Table>
                    <Waiter code=""/>
                </Order>
            </RK7CMD>
        </RK7Query>'''
        
        response = session.post(
            base_url,
            data=menu_query.encode('utf-8'),
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
            return [], None, None
        
        # Получаем список блюд
        dishes = root.findall('.//Dishes/Item')
        logger.info(f"Получено {len(dishes)} позиций для станции {station.name}")
        return dishes, waiter_info, None
    except Exception as e:
        logger.error(f"Ошибка при получении меню для станции {station.name}: {e}")
        logger.exception("Полный стек ошибки:")
        return [], None, None

def sync_station_menu(station, dish_names):
    """Синхронизирует меню для конкретной станции"""
    logger.info(f"Синхронизация меню для станции {station.name}")
    
    # Получаем меню станции и информацию об официанте
    dishes, waiter_info, table_info = get_station_menu(station)
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
            menu_item, created = MenuItem.objects.get_or_create(
                rkeeper_id=ident,
                station=station,
                defaults={
                    'name': dish_info['name'],
                    'description': dish_info['recipe'],
                    'price': price,
                    'quantity': quantity,
                    'category': categories[category_name],
                    'last_updated': timezone.now()
                }
            )
            # Если запись уже существует, обновляем только цену и количество
            if not created:
                menu_item.price = price
                menu_item.quantity = quantity
                menu_item.last_updated = timezone.now()
                menu_item.save(update_fields=['price', 'quantity', 'last_updated'])
        except Exception as e:
            logger.error(f"Ошибка при создании/обновлении позиции меню {dish_info['name']}: {e}")
    
    # Удаляем позиции, которых больше нет в меню R-Keeper
    items_to_delete = MenuItem.objects.filter(station=station).exclude(
        rkeeper_id__in=[dish.get('Ident') for dish in dishes]
    )
    
    if items_to_delete.exists():
        deleted_items = list(items_to_delete.values_list('name', flat=True))
        deleted_count = items_to_delete.count()
        logger.info(f"Удаляем {deleted_count} позиций из меню станции {station.name}: {', '.join(deleted_items)}")
        items_to_delete.delete()
    else:
        logger.info(f"Нет позиций для удаления из меню станции {station.name}")
    
    # Синхронизируем информацию об официанте, если она есть
    if waiter_info:
        logger.info(f"Начинаем синхронизацию официанта: {waiter_info}")
        try:
            waiter_obj, created = Waiter.objects.update_or_create(
                code=waiter_info['code'],
                defaults={
                    'name': waiter_info['name'],
                    'guid': waiter_info['guid'],
                    'is_active': True
                }
            )
            if created:
                logger.info(f"Создан новый официант: {waiter_obj.name}")
            else:
                logger.info(f"Обновлен официант: {waiter_obj.name}")
        except Exception as e:
            logger.error(f"Ошибка при создании/обновлении официанта {waiter_info['name']}: {e}")
            logger.exception("Полный стек ошибки:")
    else:
        logger.warning("Информация об официанте отсутствует")
    
    logger.info(f"Синхронизация меню для станции {station.name} завершена")
    return True

class Command(BaseCommand):
    help = 'Синхронизация меню и официантов из станций R-Keeper'

    def add_arguments(self, parser):
        parser.add_argument(
            '--station_id',
            type=int,
            help='ID конкретной станции для синхронизации',
            required=False
        )

    def handle(self, *args, **options):
        station_id = options.get('station_id')
        
        # Получаем справочник названий блюд
        dish_names = get_dish_names()
        if not dish_names:
            self.stdout.write(self.style.ERROR("Не удалось получить справочник блюд. Синхронизация прервана."))
            return
        
        # Получаем станции для синхронизации
        if station_id:
            stations = Station.objects.filter(id=station_id, is_active=True)
            if not stations.exists():
                self.stdout.write(self.style.ERROR(f"Станция с ID {station_id} не найдена или неактивна"))
                return
        else:
            stations = Station.objects.filter(is_active=True)
            if not stations.exists():
                self.stdout.write(self.style.WARNING("Нет активных станций в базе данных"))
                return
        
        self.stdout.write(f"Найдено {stations.count()} активных станций для синхронизации")
        
        # Синхронизируем меню для каждой станции
        for station in stations:
            try:
                with transaction.atomic():
                    sync_station_menu(station, dish_names)
                self.stdout.write(self.style.SUCCESS(f"Меню для станции {station.name} успешно синхронизировано"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Ошибка при синхронизации меню для станции {station.name}: {e}"))
        
        self.stdout.write(self.style.SUCCESS("Синхронизация меню завершена")) 