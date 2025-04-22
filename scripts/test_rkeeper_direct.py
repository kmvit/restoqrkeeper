import requests
import xml.etree.ElementTree as ET
from urllib3.util.retry import Retry
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context
import warnings
import ssl
import os

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

# Конфигурация
base_url = "https://picasso:01020304@109.248.156.50:12686/rk7api/v0/xmlinterface.xml"
stations = [
    {"name": "Кафе2", "code": 2},
    {"name": "Жираф", "code": 3},
    {"name": "Мюнхен", "code": 4},
    {"name": "Пиццерия", "code": 5},
]

def get_dish_names():
    """Получает справочник названий блюд"""
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
        return dish_names
    except Exception as e:
        print(f"Ошибка при получении справочника блюд: {e}")
        return {}

print("\nСтатистика меню по станциям:")
print("=" * 50)

# Получаем справочник названий блюд
dish_names = get_dish_names()

# Создаем директорию для меню, если её нет
menu_dir = "menu_data"
if not os.path.exists(menu_dir):
    os.makedirs(menu_dir)

for station in stations:
    try:
        # Формируем XML-запрос для получения меню станции
        xml_query = f'''<?xml version="1.0" encoding="utf-8"?>
        <RK7Query>
            <RK7CMD CMD="GetOrderMenu">
                <Station code="{station['code']}"/>
                <Order>
                    <Table>
                        <Station code="{station['code']}"/>
                    </Table>
                </Order>
            </RK7CMD>
        </RK7Query>
        '''
        
        # Отправляем запрос к серверу
        response = session.post(
            base_url,
            data=xml_query.encode('utf-8'),
            verify=False,
            headers={'Content-Type': 'application/xml'}
        )
        
        # Парсим XML-ответ
        root = ET.fromstring(response.text)
        
        # Проверяем статус ответа
        status = root.get('Status')
        if status != "Ok":
            print(f"Ошибка при получении меню для {station['name']}: {root.get('ErrorText')}")
            continue
        
        # Получаем список блюд
        dishes = root.findall('.//Dishes/Item')
        
        print(f"\nСтанция: {station['name']} (код: {station['code']})")
        print(f"Количество позиций в меню: {len(dishes)}")
        
        # Если это станция Мюнхен, сохраняем все позиции в файл
        if station['name'] == "Мюнхен":
            menu_file = os.path.join(menu_dir, "munchen_menu.txt")
            
            # Группируем блюда по категориям
            menu_by_category = {}
            for dish in dishes:
                ident = dish.get('Ident', 'Н/Д')
                price = float(dish.get('Price', 0)) / 100
                dish_info = dish_names.get(ident, {
                    'name': 'Без названия',
                    'code': 'Н/Д',
                    'recipe': '',
                    'category': 'Без категории'
                })
                
                category = dish_info['category']
                if category not in menu_by_category:
                    menu_by_category[category] = []
                
                menu_by_category[category].append({
                    'name': dish_info['name'],
                    'code': dish_info['code'],
                    'price': price,
                    'recipe': dish_info['recipe']
                })
            
            # Записываем в файл, сгруппированный по категориям
            with open(menu_file, 'w', encoding='utf-8') as f:
                f.write(f"Меню станции {station['name']} (код: {station['code']})\n")
                f.write("=" * 50 + "\n\n")
                f.write(f"Всего позиций в меню: {len(dishes)}\n")
                f.write(f"Количество категорий: {len(menu_by_category)}\n\n")
                
                # Сортируем категории по алфавиту
                for category in sorted(menu_by_category.keys()):
                    f.write(f"\n=== {category} ===\n\n")
                    
                    # Сортируем блюда в категории по названию
                    category_dishes = sorted(menu_by_category[category], key=lambda x: x['name'])
                    for i, dish in enumerate(category_dishes, 1):
                        f.write(f"{i}. {dish['name']} (Код: {dish['code']}, Цена: {dish['price']:.0f} тенге.)\n")
                        if dish['recipe']:
                            f.write(f"   Состав: {dish['recipe']}\n")
                        f.write("\n")
                    
            print(f"Меню сохранено в файл: {menu_file}")
        
        # Выводим первые 3 позиции
        if len(dishes) > 0:
            print("Примеры позиций:")
            for i, dish in enumerate(dishes[:3], 1):
                ident = dish.get('Ident', 'Н/Д')
                price = float(dish.get('Price', 0)) / 100  # Конвертируем копейки в рубли
                dish_info = dish_names.get(ident, {
                    'name': 'Без названия',
                    'code': 'Н/Д',
                    'recipe': '',
                    'category': 'Без категории'
                })
                print(f"  {i}. {dish_info['name']} (Код: {dish_info['code']}, Категория: {dish_info['category']}, Цена: {price:.2f} руб.)")
                if dish_info['recipe']:
                    print(f"     Состав: {dish_info['recipe']}")
        
        print("-" * 50)

    except requests.exceptions.RequestException as e:
        print(f"Ошибка соединения для {station['name']}: {e}")
    except ET.ParseError as e:
        print(f"Ошибка парсинга XML для {station['name']}: {e}")
    except Exception as e:
        print(f"Неизвестная ошибка для {station['name']}: {e}")


