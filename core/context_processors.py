from django.conf import settings
from .models import Page
from orders.models import Table

def table_number(request):
    """
    Добавляет номер стола и объект стола в контекст шаблона
    """
    table_number = getattr(request, 'table_number', None)
    table = None
    
    if table_number:
        try:
            table = Table.objects.get(number=table_number, is_active=True)
        except Table.DoesNotExist:
            pass
    
    return {
        'table_number': table_number,
        'table': table,
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

def menu_pages(request):
    """
    Добавляет страницы, которые должны отображаться в меню, в контекст шаблона
    """
    pages = Page.objects.filter(is_published=True, show_in_menu=True).order_by('order')
    return {
        'menu_pages': pages,
    } 