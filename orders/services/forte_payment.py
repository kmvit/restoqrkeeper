import requests
import base64
import logging
from django.conf import settings
from ..models import Order

# Настройка логгера
logger = logging.getLogger(__name__)

class ForteBankPaymentService:
    """
    Сервис для работы с платежной системой ForteBank.
    
    Предоставляет методы для создания платежей, проверки их статуса,
    авторизации, списания средств, отмены и возврата платежей.
    
    Attributes:
        api_url (str): URL API ForteBank
        merchant_id (str): ID мерчанта в системе ForteBank
        username (str): Имя пользователя для авторизации
        password (str): Пароль для авторизации
        auth_header (dict): Заголовок авторизации для запросов
    """

    def __init__(self):
        """
        Инициализирует сервис платежей ForteBank.
        
        Загружает настройки из Django settings и создает заголовок авторизации.
        """
        self.api_url = settings.FORTEBANK_API_URL
        self.merchant_id = settings.FORTEBANK_MERCHANT_ID
        self.username = settings.FORTEBANK_USERNAME
        self.password = settings.FORTEBANK_PASSWORD
        self.auth_header = self._get_auth_header()
        logger.info("ForteBankPaymentService initialized")

    def _get_auth_header(self) -> dict:
        """
        Создает заголовок для Basic Authentication.
        
        Returns:
            dict: Заголовок с закодированными учетными данными в формате Basic Auth.
        """
        credentials = f"{self.username}:{self.password}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()
        return {'Authorization': f'Basic {encoded_credentials}'}

    def create_payment(self, order: Order) -> dict:
        """
        Создает новый платеж в системе ForteBank.
        
        Args:
            order (Order): Объект заказа Django, содержащий информацию о платеже.
            
        Returns:
            dict: Ответ от API ForteBank с данными созданного платежа.
                Содержит payment_id и другие параметры платежа.
                
        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            ValueError: При невалидных данных заказа.
        """
        logger.info(f"Creating payment for order #{order.id}")
        payload = {
            'merchant_id': self.merchant_id,
            'amount': str(order.total_amount),
            'currency': 'KZT',
            'order_id': str(order.id),
            'description': f'Оплата заказа #{order.id}',
            'success_url': f'{settings.SITE_URL}/orders/success/',
            'failure_url': f'{settings.SITE_URL}/orders/failure/',
            'callback_url': f'{settings.SITE_URL}/orders/callback/',
            'items': [
                {
                    'name': item.menu_item.name,
                    'price': str(item.price),
                    'quantity': item.quantity
                } for item in order.items.all()
            ]
        }

        headers = {
            'Content-Type': 'application/json',
            **self.auth_header
        }

        try:
            logger.debug(f"Sending payment request with payload: {payload}")
            response = requests.post(
                f'{self.api_url}/api/v3/transactions/payment',
                json=payload,
                headers=headers,
                verify=True
            )
            response.raise_for_status()
            logger.info(f"Payment created successfully for order #{order.id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error creating payment for order #{order.id}: {str(e)}", exc_info=True)
            raise

    def check_payment_status(self, payment_id: str) -> dict:
        """
        Проверяет текущий статус платежа в системе ForteBank.
        
        Args:
            payment_id (str): Уникальный идентификатор платежа в системе ForteBank.
            
        Returns:
            dict: Информация о статусе платежа, включая:
                - status: текущий статус платежа
                - amount: сумма платежа
                - currency: валюта платежа
                - created_at: время создания
                - updated_at: время последнего обновления
                
        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            ValueError: При невалидном payment_id.
        """
        logger.info(f"Checking payment status for payment_id: {payment_id}")
        headers = {
            'Content-Type': 'application/json',
            **self.auth_header
        }

        try:
            response = requests.get(
                f'{self.api_url}/api/v3/transactions/{payment_id}/status',
                headers=headers,
                verify=True
            )
            response.raise_for_status()
            logger.info(f"Successfully retrieved payment status for payment_id: {payment_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error checking payment status for payment_id {payment_id}: {str(e)}", exc_info=True)
            raise

    def authorize_payment(self, order: Order) -> dict:
        """
        Авторизует платеж (резервирует средства на карте клиента).
        
        Args:
            order (Order): Объект заказа Django с информацией о платеже.
            
        Returns:
            dict: Ответ от API с данными авторизации, включая:
                - auth_id: идентификатор авторизации
                - status: статус авторизации
                - amount: зарезервированная сумма
                
        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            ValueError: При невалидных данных заказа.
        """
        logger.info(f"Authorizing payment for order #{order.id}")
        payload = {
            'merchant_id': self.merchant_id,
            'amount': str(order.total_amount),
            'currency': 'KZT',
            'order_id': str(order.id),
            'description': f'Авторизация заказа #{order.id}'
        }

        headers = {
            'Content-Type': 'application/json',
            **self.auth_header
        }

        try:
            logger.debug(f"Sending authorization request with payload: {payload}")
            response = requests.post(
                f'{self.api_url}/api/v3/transactions/auth',
                json=payload,
                headers=headers,
                verify=True
            )
            response.raise_for_status()
            logger.info(f"Payment authorized successfully for order #{order.id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error authorizing payment for order #{order.id}: {str(e)}", exc_info=True)
            raise

    def capture_payment(self, auth_id: str, amount: str) -> dict:
        """
        Списывает средства после успешной авторизации.
        
        Args:
            auth_id (str): Идентификатор авторизации.
            amount (str): Сумма к списанию (может быть меньше или равна сумме авторизации).
            
        Returns:
            dict: Ответ от API с результатом списания, включая:
                - transaction_id: идентификатор транзакции
                - status: статус списания
                - amount: списанная сумма
                
        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            ValueError: При невалидных параметрах.
        """
        logger.info(f"Capturing payment for auth_id: {auth_id}, amount: {amount}")
        payload = {
            'merchant_id': self.merchant_id,
            'amount': amount,
            'auth_id': auth_id
        }

        headers = {
            'Content-Type': 'application/json',
            **self.auth_header
        }

        try:
            logger.debug(f"Sending capture request with payload: {payload}")
            response = requests.post(
                f'{self.api_url}/api/v3/transactions/capture',
                json=payload,
                headers=headers,
                verify=True
            )
            response.raise_for_status()
            logger.info(f"Payment captured successfully for auth_id: {auth_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error capturing payment for auth_id {auth_id}: {str(e)}", exc_info=True)
            raise

    def reverse_payment(self, auth_id: str) -> dict:
        """
        Отменяет ранее выполненную авторизацию платежа.
        
        Args:
            auth_id (str): Идентификатор авторизации для отмены.
            
        Returns:
            dict: Ответ от API с результатом отмены, включая:
                - status: статус отмены
                - reversed_amount: отмененная сумма
                
        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            ValueError: При невалидном auth_id.
        """
        logger.info(f"Reversing payment for auth_id: {auth_id}")
        payload = {
            'merchant_id': self.merchant_id,
            'auth_id': auth_id
        }

        headers = {
            'Content-Type': 'application/json',
            **self.auth_header
        }

        try:
            logger.debug(f"Sending reverse request with payload: {payload}")
            response = requests.post(
                f'{self.api_url}/api/v3/transactions/reverse',
                json=payload,
                headers=headers,
                verify=True
            )
            response.raise_for_status()
            logger.info(f"Payment reversed successfully for auth_id: {auth_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error reversing payment for auth_id {auth_id}: {str(e)}", exc_info=True)
            raise

    def refund_payment(self, payment_id: str, amount: str) -> dict:
        """
        Возвращает средства клиенту.
        
        Args:
            payment_id (str): Идентификатор платежа для возврата.
            amount (str): Сумма к возврату (может быть меньше или равна сумме платежа).
            
        Returns:
            dict: Ответ от API с результатом возврата, включая:
                - refund_id: идентификатор возврата
                - status: статус возврата
                - amount: сумма возврата
                
        Raises:
            requests.exceptions.RequestException: При ошибке HTTP-запроса.
            ValueError: При невалидных параметрах.
        """
        logger.info(f"Refunding payment for payment_id: {payment_id}, amount: {amount}")
        payload = {
            'merchant_id': self.merchant_id,
            'amount': amount,
            'payment_id': payment_id
        }

        headers = {
            'Content-Type': 'application/json',
            **self.auth_header
        }

        try:
            logger.debug(f"Sending refund request with payload: {payload}")
            response = requests.post(
                f'{self.api_url}/api/v3/transactions/refund',
                json=payload,
                headers=headers,
                verify=True
            )
            response.raise_for_status()
            logger.info(f"Payment refunded successfully for payment_id: {payment_id}")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Error refunding payment for payment_id {payment_id}: {str(e)}", exc_info=True)
            raise

    def _generate_signature(self, data: dict) -> str:
        """
        Генерирует подпись для запросов к API.
        
        Args:
            data (dict): Данные для подписи.
            
        Returns:
            str: Подпись в формате, требуемом API ForteBank.
            
        Note:
            Метод должен быть реализован согласно документации банка.
            В текущей реализации возвращает пустую строку.
        """
        # TODO: Реализовать согласно документации банка
        return "" 