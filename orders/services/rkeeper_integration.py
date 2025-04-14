import xml.etree.ElementTree as ET
from django.conf import settings
from ..models import Order

class RKeeperIntegrationService:
    def __init__(self):
        self.api_url = settings.RKEEPER_API_URL
        self.username = settings.RKEEPER_USERNAME
        self.password = settings.RKEEPER_PASSWORD

    def send_order(self, order: Order) -> str:
        """
        Отправляет заказ в систему R-Keeper
        """
        xml_data = self._create_order_xml(order)
        
        # Здесь должен быть код для отправки XML в R-Keeper
        # Это пример, который нужно заменить на реальную реализацию
        response = self._send_xml_request(xml_data)
        
        # Парсим ответ и получаем ID заказа в R-Keeper
        order_id = self._parse_response(response)
        
        return order_id

    def _create_order_xml(self, order: Order) -> str:
        """
        Создает XML для отправки заказа в R-Keeper
        """
        root = ET.Element('RK7Query')
        command = ET.SubElement(root, 'RK7Command')
        command.set('CMD', 'SetOrder')
        
        # Создаем структуру заказа
        order_elem = ET.SubElement(command, 'Order')
        order_elem.set('TableNumber', str(order.table_number))
        
        # Добавляем позиции заказа
        for item in order.items.all():
            item_elem = ET.SubElement(order_elem, 'Item')
            item_elem.set('Quantity', str(item.quantity))
            item_elem.set('Price', str(item.price))
            item_elem.set('MenuItemID', str(item.menu_item.rkeeper_id))
        
        return ET.tostring(root, encoding='unicode')

    def _send_xml_request(self, xml_data: str) -> str:
        """
        Отправляет XML-запрос в R-Keeper
        """
        # Здесь должен быть код для отправки XML в R-Keeper
        # Это пример, который нужно заменить на реальную реализацию
        import requests
        
        headers = {
            'Content-Type': 'application/xml',
            'Authorization': f'Basic {self._get_auth_token()}'
        }
        
        response = requests.post(
            self.api_url,
            data=xml_data,
            headers=headers
        )
        response.raise_for_status()
        
        return response.text

    def _parse_response(self, xml_response: str) -> str:
        """
        Парсит ответ от R-Keeper и извлекает ID заказа
        """
        root = ET.fromstring(xml_response)
        # Здесь должен быть код для извлечения ID заказа из ответа
        # Это пример, который нужно заменить на реальную реализацию
        order_id = root.find('.//OrderID').text
        return order_id

    def _get_auth_token(self) -> str:
        """
        Получает токен авторизации для R-Keeper
        """
        import base64
        credentials = f'{self.username}:{self.password}'
        return base64.b64encode(credentials.encode()).decode() 