from django.contrib import admin
from .models import Category, MenuItem, Station

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'station')
    search_fields = ('name', 'station__name')
    list_filter = ('station',)
@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'quantity','category__station')
    list_filter = ('category__station',)
    search_fields = ('name', 'description')

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'rkeeper_code', 'rkeeper_id', 'r_keeper_number', 'is_active')
    search_fields = ('name', 'rkeeper_code', 'rkeeper_id')
    list_filter = ('is_active',)


