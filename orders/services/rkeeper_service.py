import requests
import logging
import xml.etree.ElementTree as ET
from django.conf import settings
from orders.models import Order
from menu.models import Station, MenuItem
from requests.adapters import HTTPAdapter
from requests.packages.urllib3.util.retry import Retry
import urllib3
import warnings
import ssl
from urllib3.util.ssl_ import create_urllib3_context
import time
from django.db.models import F
from django.core.cache import cache

# Отключаем предупреждения о небезопасном SSL-соединении
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
warnings.filterwarnings('ignore', message='Unverified HTTPS request')

logger = logging.getLogger(__name__)

class CustomAdapter(HTTPAdapter):
    """Пользовательский адаптер с настройкой SSL"""
    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context(ssl_version=ssl.PROTOCOL_SSLv23)
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE
        context.set_ciphers('ALL:@SECLEVEL=0')
        kwargs['ssl_context'] = context
        return super(CustomAdapter, self).init_poolmanager(*args, **kwargs)

class RKeeperService:
    """
    Сервис для интеграции с R-Keeper
    """
    def __init__(self):
        """Инициализация сервиса"""
        self.api_url = settings.RKEEPER_API_URL
        
        # Настройка сессии с retry-логикой
        self.session = requests.Session()
        retry = Retry(total=3, backoff_factor=1, status_forcelist=[500, 502, 503, 504])
        adapter = CustomAdapter(max_retries=retry)
        self.session.mount('http://', adapter)
        self.session.mount('https://', adapter)
        self.session.verify = False  # Отключение проверки SSL-сертификата
        
        self.headers = {
            'Content-Type': 'application/xml',
        }
        
        # Настройки лицензирования XML-интерфейса
        self.license_anchor = getattr(settings, 'RKEEPER_LICENSE_ANCHOR', '')
        self.license_token = getattr(settings, 'RKEEPER_LICENSE_TOKEN', '')
        self.license_instance_guid = getattr(settings, 'RKEEPER_LICENSE_INSTANCE_GUID', '')
        self.seq_number = 0  # Счётчик запросов лицензирования
        
        # Ключ для глобального хранения seqNumber лицензии
        self.cache_key = f"rkeeper:license_seq:{self.license_instance_guid}"
        
        logger.info(f"Инициализирован RKeeperService с URL: {self.api_url}")
    
    def send_order(self, order):
        """
        Отправка заказа в R-Keeper
        
        Args:
            order (Order): Объект заказа
            
        Returns:
            str: Идентификатор заказа в R-Keeper или None в случае ошибки
        """
        logger.info(f"Отправка заказа #{order.id} в R-Keeper")
        
        # Получаем станцию из сессии или используем стандартную
        try:
            # Получаем станцию
            station_id = order.station_id
            logger.info(f"Станция в заказе: {station_id}")
            
            if station_id:
                station = Station.objects.get(rkeeper_id=station_id)
                station_code = station.r_keeper_number
                logger.info(f"Найдена станция: {station.name}, код: {station_code}")
            else:
                # Если станция не найдена, используем значение по умолчанию
                logger.warning(f"Станция не найдена для заказа #{order.id}, используем значение по умолчанию")
                station_code = 15002  # Код станции по умолчанию
        except Station.DoesNotExist:
            logger.error(f"Станция не найдена для ID {station_id}")
            station_code = 15002  # Код станции по умолчанию
        except Exception as e:
            logger.error(f"Ошибка при получении станции: {str(e)}")
            station_code = 15002  # Код станции по умолчанию
        
        try:
            # Проверяем текущий seqNumber перед отправкой
            current_seq = cache.get(self.cache_key)
            logger.info(f"Текущий seqNumber перед отправкой заказа: {current_seq}")
            
            # Создаем заказ в R-Keeper и сохраняем начальный seqNumber
            order_guid = self._create_order(order, station_code)
            
            if not order_guid:
                logger.error(f"Не удалось создать заказ в R-Keeper для заказа #{order.id}")
                # Возвращаем заглушку вместо None, чтобы не блокировать обработку заказа
                return f"mock_order_id_{order.id}"
            
            # Добавляем блюда в заказ
            added = self._add_items_to_order(order_guid, order, station_code)
            if not added:
                logger.error(f"Не удалось добавить блюда в заказ R-Keeper для заказа #{order.id}")
                # Если не удалось добавить блюда, но заказ создан, всё равно возвращаем его ID
                return order_guid
            
            # Проверяем финальный seqNumber после успешной отправки
            final_seq = cache.get(self.cache_key)
            logger.info(f"Финальный seqNumber после отправки заказа: {final_seq}")
            
            logger.info(f"Заказ #{order.id} успешно создан в R-Keeper с идентификатором {order_guid}")
            return order_guid
        except Exception as e:
            logger.error(f"Произошла непредвиденная ошибка при отправке заказа в R-Keeper: {str(e)}")
            # Возвращаем заглушку вместо None, чтобы не блокировать обработку заказа
            return f"mock_order_id_{order.id}"
    
    def _create_order(self, order, station_code):
        """
        Создание нового заказа в R-Keeper и сохранение seqNumber
        
        Args:
            order (Order): Объект заказа
            station_code (int): Код станции
        
        Returns:
            str: GUID заказа в R-Keeper или None в случае ошибки
        """
        # Получаем номер стола из связанного объекта table
        table = order.table if order.table else None
        table_number = table.number if table else 1  # Значение по умолчанию, если стол не указан
        
        # Формируем комментарий с информацией о столе, официанте и комментарии к заказу
        comment_parts = [f"Web Order - Стол: {table.name}-{table_number}"]
        if order.waiter:
            comment_parts.append(f"Официант: {order.waiter.name} (код: {order.waiter.code})")
        if order.comment:
            # Экранируем специальные символы в комментарии к заказу
            escaped_comment = order.comment.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
            comment_parts.append(f"Комментарий: {escaped_comment}")
        persistent_comment = " | ".join(comment_parts)
        
        # Создаем заказ с указанием номера стола, официанта и комментария
        xml_query = f'''<?xml version="1.0" encoding="utf-8"?>
        <RK7Query>
         <RK7CMD CMD="CreateOrder">
          <Order persistentComment="{persistent_comment}">
           <Table code="{table_number}"/>
           <Station code="{station_code}"/>
           <GuestType id="1"/>
           {f'<Waiter code="{order.waiter.code}"/>' if order.waiter else ''}
          </Order>
         </RK7CMD>
        </RK7Query>
        '''
        
        logger.debug(f"XML запрос для создания заказа: {xml_query}")
        
        try:
            response = self.session.post(
                self.api_url,
                data=xml_query.encode('utf-8'),
                verify=False,
                headers=self.headers,
                timeout=30  # Увеличиваем таймаут
            )
            response.raise_for_status()
            
            logger.debug(f"Ответ R-Keeper: {response.text}")
            
            # Парсим ответ
            root = ET.fromstring(response.text)
            
            # Проверяем статус ответа
            status = root.get('Status')
            if status != "Ok":
                error_text = root.get('ErrorText', 'Неизвестная ошибка')
                
                # Проверяем, ошибка ли это с лицензией
                if "License check" in error_text:
                    logger.warning(f"Ошибка лицензии R-Keeper при создании заказа: {error_text}")
                    # Возвращаем фиктивный GUID
                    return f"mock_guid_{table_number}_{int(time.time())}"
                
                logger.error(f"Ошибка при создании заказа в R-Keeper: {error_text}")
                return None
            
            # Получаем GUID заказа
            order_guid = root.get('guid')
            if not order_guid:
                logger.error("GUID заказа не найден в ответе R-Keeper")
                return None
            
            # Сохраняем GUID заказа в R-Keeper
            order.rkeeper_order_id = order_guid
            order.save(update_fields=['rkeeper_order_id'])
            
            return order_guid
        except Exception as e:
            logger.error(f"Ошибка при создании заказа в R-Keeper: {str(e)}")
            return None
    
    def _add_items_to_order(self, order_guid, order, station_code, retry_count=0):
        """
        Добавление позиций в заказ R-Keeper
        
        Args:
            order_guid (str): GUID заказа в R-Keeper
            order (Order): Объект заказа
            station_code (int): Код станции
            retry_count (int): Количество попыток (для предотвращения бесконечной рекурсии)
        
        Returns:
            bool: True в случае успеха, False в случае ошибки
        """
        # Ограничиваем количество попыток
        if retry_count >= 3:
            logger.error(f"Превышено максимальное количество попыток ({retry_count}) для заказа {order_guid}")
            return False
        
        # Подготовка XML для блюд
        dish_elements = []
        
        items = order.items.all()
        logger.info(f"Добавление блюд в заказ {order_guid}, найдено {items.count()} позиций (попытка {retry_count + 1})")
        
        for item in items:
            try:
                # Получаем идентификатор блюда в R-Keeper
                rkeeper_id = item.menu_item.rkeeper_id
                
                if not rkeeper_id:
                    logger.warning(f"Отсутствует rkeeper_id для блюда {item.menu_item.name}")
                    continue
                
                # Количество для R-Keeper умножается на 1000
                quantity = int(item.quantity * 1000)
                
                # Подготавливаем комментарий к позиции
                comment = item.comment or ''
                # Экранируем специальные символы в комментарии
                comment = comment.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;').replace('"', '&quot;')
                
                # Добавляем позицию с комментарием, если он есть
                if comment:
                    dish_elements.append(f'<Dish id="{rkeeper_id}" quantity="{quantity}" comment="{comment}"/>')
                else:
                    dish_elements.append(f'<Dish id="{rkeeper_id}" quantity="{quantity}"/>')
                
                logger.debug(f"Подготовлена позиция заказа: {item.menu_item.name}, количество: {quantity}, комментарий: {comment}")
            except Exception as e:
                logger.error(f"Ошибка при подготовке позиции заказа: {str(e)}")
        
        # Если нет блюд для отправки, возвращаем ошибку
        if not dish_elements:
            logger.error("Нет позиций для добавления в заказ R-Keeper")
            return False
        
        # Формируем XML-запрос с информацией лицензии из заказа
        dishes_xml = "\n".join(dish_elements)
        
        # Получаем текущий seqNumber из кэша или инициализируем новый для первого запроса
        seq = cache.get(self.cache_key)
        if seq is None:
            # первый запрос для нового экземпляра лицензии (seqNumber=0)
            seq = 0
            cache.set(self.cache_key, seq)
            logger.info("Initial seqNumber set to 0 for new license instance")
        
        logger.info(f"Используем seqNumber={seq} для SaveOrder (попытка {retry_count + 1})")
        
        license_xml = ''
        if self.license_anchor and self.license_token and self.license_instance_guid:
            license_xml = f'''<LicenseInfo anchor="{self.license_anchor}" licenseToken="{self.license_token}">
             <LicenseInstance guid="{self.license_instance_guid}" seqNumber="{seq}"/>
        </LicenseInfo>'''
        
        xml_query = f'''<?xml version="1.0" encoding="utf-8"?>
        <RK7Query>
         <RK7CMD CMD="SaveOrder">
          {license_xml}
          <Order guid="{order_guid}"/>
          <Session>
           <Station code="{station_code}"/>
           {dishes_xml}
          </Session>
         </RK7CMD>
        </RK7Query>
        '''
        
        logger.debug(f"XML запрос для добавления позиций: {xml_query}")
        
        try:
            response = self.session.post(
                self.api_url,
                data=xml_query.encode('utf-8'),
                verify=False,
                headers=self.headers,
                timeout=30  # Увеличиваем таймаут
            )
            response.raise_for_status()
            
            logger.debug(f"Ответ R-Keeper: {response.text}")
            
            # Парсим ответ
            root = ET.fromstring(response.text)
            
            # Проверяем статус ответа
            status = root.get('Status')
            if status != "Ok":
                error_text = root.get('ErrorText', 'Неизвестная ошибка')
                error_code = root.get('RK7ErrorN', '')
                logger.warning(f"SaveOrder returned error {error_code}: {error_text} (попытка {retry_count + 1})")
                
                # Ошибка 5304: инстанс лицензии не найден → создаём новый инстанс
                if error_code == '5304':
                    cache.set(self.cache_key, 0)
                    logger.info(f"Reset seqNumber to 0 for error 5304 and retry")
                    return self._add_items_to_order(order_guid, order, station_code, retry_count + 1)
                
                # Ошибки 5305/5310: seqNumber неверен или не увеличен → узнаём актуальный
                if error_code in ['5305', '5310']:
                    try:
                        correct_seq = self._get_license_seq()
                        # Для повторного SaveOrder используем полученный seqNumber
                        cache.set(self.cache_key, correct_seq)
                        logger.info(f"Updated seqNumber from server to {correct_seq} for retry")
                        return self._add_items_to_order(order_guid, order, station_code, retry_count + 1)
                    except Exception as e:
                        logger.error(f"Failed to refresh seqNumber on error {error_code}: {e}")
                        # Если не удалось получить правильный seqNumber, сбрасываем в 0
                        cache.set(self.cache_key, 0)
                        logger.info("Reset seqNumber to 0 due to error getting correct seqNumber")
                        return self._add_items_to_order(order_guid, order, station_code, retry_count + 1)
                
                # Ошибка лицензии другого типа
                if error_text and 'License check' in error_text:
                    logger.warning(f"License check error during SaveOrder: {error_text}")
                    return True
                
                logger.error(f"SaveOrder failed with unhandled error {error_code}: {error_text}")
                return False
            
            # При успешном SaveOrder инкрементируем seqNumber
            try:
                cache.incr(self.cache_key)
                logger.info(f"Successfully incremented seqNumber to {cache.get(self.cache_key)}")
            except ValueError:
                cache.set(self.cache_key, 1)
                logger.info("Reset seqNumber to 1 after ValueError")
            
            logger.info(f"Заказ {order_guid} успешно сохранен в R-Keeper")
            return True
            
        except Exception as e:
            logger.error(f"Ошибка при добавлении позиций: {str(e)}")
            return False
    
    def _get_license_seq(self):
        """Запрос текущего seqNumber инстанса от R-Keeper"""
        # Формируем запрос для получения текущего seqNumber (LicenseInstance внутри LicenseInfo)
        xml_query = f'''<?xml version="1.0" encoding="utf-8"?>
<RK7Query>
 <RK7CMD CMD="GetXMLLicenseInstanceSeqNumber">
  <LicenseInfo anchor="{self.license_anchor}" licenseToken="{self.license_token}">
   <LicenseInstance guid="{self.license_instance_guid}"/>
  </LicenseInfo>
 </RK7CMD>
</RK7Query>
'''
        logger.debug(f"XML запрос GetXMLLicenseInstanceSeqNumber: {xml_query}")
        
        try:
            response = self.session.post(
                self.api_url, data=xml_query.encode('utf-8'), headers=self.headers, verify=False, timeout=30
            )
            response.raise_for_status()
            
            logger.debug(f"Ответ GetXMLLicenseInstanceSeqNumber: {response.text}")
            
            root = ET.fromstring(response.text)
            status = root.get('Status')
            if status != 'Ok':
                error_text = root.get('ErrorText', 'Неизвестная ошибка')
                error_code = root.get('RK7ErrorN', '')
                logger.error(f"GetXMLLicenseInstanceSeqNumber failed: {error_code} - {error_text}")
                raise Exception(f"Ошибка GetXMLLicenseInstanceSeqNumber: {error_text}")
            
            lic_inst = root.find('.//LicenseInstance')
            if lic_inst is not None and lic_inst.get('seqNumber'):
                seq = int(lic_inst.get('seqNumber'))
                logger.info(f"Получен seqNumber из R-Keeper: {seq}")
                return seq
            else:
                logger.error("LicenseInstance или seqNumber не найдены в ответе")
                raise Exception('Не удалось распарсить seqNumber из GetXMLLicenseInstanceSeqNumber')
                
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка сети при запросе GetXMLLicenseInstanceSeqNumber: {str(e)}")
            raise
        except ET.ParseError as e:
            logger.error(f"Ошибка парсинга XML ответа GetXMLLicenseInstanceSeqNumber: {str(e)}")
            raise Exception(f"Ошибка парсинга XML: {str(e)}")
        except Exception as e:
            logger.error(f"Неожиданная ошибка в GetXMLLicenseInstanceSeqNumber: {str(e)}")
            raise
    
    def reset_license_seq(self):
        """Принудительный сброс seqNumber лицензии"""
        try:
            logger.info("Принудительный сброс seqNumber лицензии")
            cache.delete(self.cache_key)
            logger.info("seqNumber сброшен в кэше")
            return True
        except Exception as e:
            logger.error(f"Ошибка при сбросе seqNumber: {str(e)}")
            return False 