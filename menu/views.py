from django.shortcuts import render, get_object_or_404
from django.http import Http404
from .models import MenuItem, Category, Station

def menu_list(request):
    """
    Отображение меню или списка станций
    
    Параметры:
    - station_code: код станции (опционально, можно передать через GET или сессию)
    - table_number: номер стола (опционально, можно передать через GET или сессию)
    """
    # Получаем параметры из GET-запроса или сессии
    station_code = request.GET.get('station_id')
    table_number = request.GET.get('table')
    
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
        context.update({
            'station': station,
            'categories': Category.objects.filter(station=station),
            'items': MenuItem.objects.filter(
                station=station,
                is_available=True
            ).select_related('category').order_by('category__name', 'name')
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
    
    context = {
        'item': item,
        'station': station,
        'table_number': table_number
    }
    
    return render(request, 'menu/menu_detail.html', context)
