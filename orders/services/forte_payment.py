import requests
from django.conf import settings
from ..models import Order

class ForteBankPaymentService:
    def __init__(self):
        self.api_url = settings.FORTEBANK_API_URL
        self.merchant_id = settings.FORTEBANK_MERCHANT_ID
        self.secret_key = settings.FORTEBANK_SECRET_KEY

    def create_payment(self, order: Order) -> dict:
        """
        Создает платеж в системе ForteBank
        """
        payload = {
            'merchant_id': self.merchant_id,
            'amount': str(order.total_amount),
            'currency': 'KZT',
            'order_id': str(order.id),
            'success_url': f'{settings.SITE_URL}/orders/success/',
            'failure_url': f'{settings.SITE_URL}/orders/failure/',
            'callback_url': f'{settings.SITE_URL}/orders/callback/',
        }

        # Добавляем подпись
        payload['signature'] = self._generate_signature(payload)

        response = requests.post(f'{self.api_url}/create-payment', json=payload)
        response.raise_for_status()
        
        return response.json()

    def check_payment_status(self, payment_id: str) -> dict:
        """
        Проверяет статус платежа
        """
        payload = {
            'merchant_id': self.merchant_id,
            'payment_id': payment_id,
        }
        payload['signature'] = self._generate_signature(payload)

        response = requests.post(f'{self.api_url}/check-payment', json=payload)
        response.raise_for_status()
        
        return response.json()

    def _generate_signature(self, data: dict) -> str:
        """
        Генерирует подпись для запросов к API
        """
        # Здесь должна быть реализация генерации подписи согласно документации ForteBank
        # Это пример, который нужно заменить на реальную реализацию
        import hashlib
        import hmac
        
        # Сортируем параметры по ключу
        sorted_params = sorted(data.items())
        # Формируем строку для подписи
        string_to_sign = '&'.join(f'{k}={v}' for k, v in sorted_params)
        # Создаем подпись
        signature = hmac.new(
            self.secret_key.encode(),
            string_to_sign.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return signature 