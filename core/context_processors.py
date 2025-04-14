from django.conf import settings

def table_number(request):
    """
    Добавляет номер стола в контекст шаблона
    """
    return {
        'table_number': getattr(request, 'table_number', None),
    }

def site_settings(request):
    """
    Добавляет основные настройки сайта в контекст шаблона
    """
    return {
        'SITE_NAME': getattr(settings, 'SITE_NAME', 'Ресторан'),
        'SITE_URL': getattr(settings, 'SITE_URL', ''),
        'CURRENCY': getattr(settings, 'CURRENCY', 'KZT'),
        'CURRENCY_SYMBOL': getattr(settings, 'CURRENCY_SYMBOL', '₸'),
    } 