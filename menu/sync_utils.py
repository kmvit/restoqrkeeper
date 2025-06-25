import requests
import xml.etree.ElementTree as ET
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import warnings
import ssl
import os
import logging

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

# Конфигурация из переменных окружения
base_url = os.environ.get('RKEEPER_API_URL', 'https://example.com/rk7api/v0/xmlinterface.xml')

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
        
        root = ET.fromstring(response.text)
        
        status = root.get('Status')
        if status != "Ok":
            logger.error(f"Ошибка при получении меню для {station.name}: {root.get('ErrorText')}")
            return []
        
        dishes = root.findall('.//Dishes/Item')
        logger.info(f"Получено {len(dishes)} позиций для станции {station.name}")
        return dishes
    except Exception as e:
        logger.error(f"Ошибка при получении меню для станции {station.name}: {e}")
        return []

def sync_station_menu(station, dish_names):
    """Синхронизирует меню для конкретной станции"""
    from django.utils import timezone
    from .models import Category, MenuItem
    
    logger.info(f"Синхронизация меню для станции {station.name}")
    
    dishes = get_station_menu(station)
    if not dishes:
        logger.warning(f"Для станции {station.name} не получено ни одной позиции меню")
        return False
    
    categories = {}
    
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
                    'is_available': True,
                    'last_updated': timezone.now()
                }
            )
            # Если запись уже существует, обновляем только цену и количество
            if not created:
                menu_item.price = price
                menu_item.quantity = quantity
                menu_item.last_updated = timezone.now()
                menu_item.save(update_fields=['price', 'quantity', 'last_updated'])
                logger.info(f"Обновлена позиция меню: {dish_info['name']} для станции {station.name}")
            else:
                logger.info(f"Создана новая позиция меню: {dish_info['name']} для станции {station.name}")
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
    
    logger.info(f"Синхронизация меню для станции {station.name} завершена")
    return True 