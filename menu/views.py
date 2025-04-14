from django.shortcuts import render
from .models import MenuItem, Category

def menu_list(request):
    items = MenuItem.objects.all()
    categories = Category.objects.all()
    return render(request, 'menu/menu_list.html', {
        'items': items,
        'categories': categories
    })

def menu_detail(request, item_id):
    item = MenuItem.objects.get(id=item_id)
    return render(request, 'menu/menu_detail.html', {'item': item})
