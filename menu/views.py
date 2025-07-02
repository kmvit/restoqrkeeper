from django.shortcuts import render, get_object_or_404
from django.http import Http404
from django.utils.translation import get_language
from .models import MenuItem, Category, Station

def menu_list(request, station_id=None, table=None):
    """
    Отображение меню или списка станций
    
    Параметры:
    - station_id: код станции (из URL или GET-параметра)
    - table: номер стола (из URL или GET-параметра)
    """
    # Получаем параметры из URL, GET-запроса или сессии
    station_code = station_id or request.GET.get('station_id') or request.session.get('station_code')
    table_number = table or request.GET.get('table') or request.session.get('table_number')
    
    # Получаем текущий язык
    current_language = get_language()
    
    # Инициализируем контекст
    context = {
        'items': [],
        'categories': [],
        'station': None,
        'table_number': table_number,
        'stations': Station.objects.filter(is_active=True)
    }
    
    # Если указан код станции, показываем меню этой станции
    if station_code:
        station = get_object_or_404(Station, rkeeper_id=station_code, is_active=True)
        items = MenuItem.objects.filter(
            station=station,
            is_available=True
        ).select_related('category').order_by('category__name', 'name')
        
        # Если язык казахский, заменяем названия и описания на казахские
        if current_language == 'kk':
            for item in items:
                if item.name_kk:
                    item.name = item.name_kk
                if item.description_kk:
                    item.description = item.description_kk
        
        # Получаем только те категории, в которых есть доступные блюда
        categories_with_items = Category.objects.filter(
            station=station,
            menuitem__is_available=True
        ).distinct()
        
        context.update({
            'station': station,
            'categories': categories_with_items,
            'items': items
        })
        
        # Сохраняем параметры в сессии
        request.session['station_code'] = station_code
        if table_number:
            request.session['table_number'] = table_number
    
    return render(request, 'menu/menu_list.html', context)

def menu_detail(request, item_id):
    """
    Детальная информация о позиции меню
    
    Args:
        item_id (int): ID позиции меню
    """
    # Получаем параметры из сессии
    station_code = request.session.get('station_code')
    table_number = request.session.get('table_number')
    
    # Получаем позицию меню
    item = get_object_or_404(MenuItem, id=item_id, is_available=True)
    
    # Если станция указана, проверяем что элемент принадлежит этой станции
    if station_code:
        station = get_object_or_404(Station, rkeeper_code=station_code, is_active=True)
        if item.station != station:
            raise Http404("Item not found in this station")
    else:
        station = item.station
    
    # Получаем текущий язык
    current_language = get_language()
    
    # Если язык казахский и есть перевод, используем его
    if current_language == 'kk':
        if item.name_kk:
            item.name = item.name_kk
        if item.description_kk:
            item.description = item.description_kk
    
    context = {
        'item': item,
        'station': station,
        'table_number': table_number
    }
    
    return render(request, 'menu/menu_detail.html', context)
