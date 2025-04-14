from decimal import Decimal
from typing import List, Dict, Any
from django.conf import settings

def format_price(price: Decimal) -> str:
    """
    Форматирует цену с учетом валюты
    """
    currency_symbol = getattr(settings, 'CURRENCY_SYMBOL', '₸')
    return f'{price:,.2f} {currency_symbol}'.replace(',', ' ')

def calculate_order_total(items: List[Dict[str, Any]]) -> Decimal:
    """
    Рассчитывает общую сумму заказа
    """
    return sum(Decimal(str(item['price'])) * item['quantity'] for item in items)

def validate_table_number(table_number: int) -> bool:
    """
    Проверяет корректность номера стола
    """
    min_table = getattr(settings, 'MIN_TABLE_NUMBER', 1)
    max_table = getattr(settings, 'MAX_TABLE_NUMBER', 100)
    return min_table <= table_number <= max_table

def get_order_status_display(status: str) -> str:
    """
    Возвращает отображаемое название статуса заказа
    """
    status_map = {
        'pending': 'Ожидает оплаты',
        'paid': 'Оплачен',
        'processing': 'В обработке',
        'completed': 'Завершен',
        'cancelled': 'Отменен',
    }
    return status_map.get(status, status) 