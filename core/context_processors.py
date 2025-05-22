from django.conf import settings
from .models import Page

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

def menu_pages(request):
    """
    Добавляет страницы, которые должны отображаться в меню, в контекст шаблона
    """
    pages = Page.objects.filter(is_published=True, show_in_menu=True).order_by('order')
    return {
        'menu_pages': pages,
    } 