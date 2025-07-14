from django.contrib import admin
from django.contrib import messages
from django.core.management import call_command
from .models import Category, MenuItem, Station
from .sync_utils import get_dish_names, sync_station_menu
from .tasks import manual_sync_menu_task

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'station')
    search_fields = ('name', 'station__name')
    list_filter = ('station',)

@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('name', 'name_kk', 'category', 'quantity', 'category__station', 'is_available', 'stop_list')
    list_filter = ('category__station', 'is_available', 'stop_list')
    search_fields = ('name', 'name_kk', 'description', 'description_kk')
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'name_kk', 'category', 'station', 'price', 'quantity', 'is_available', 'stop_list')
        }),
        ('Описание', {
            'fields': ('description', 'description_kk')
        }),
        ('Дополнительно', {
            'fields': ('photo', 'rkeeper_id', 'last_updated')
        }),
    )
    readonly_fields = ('last_updated',)

@admin.register(Station)
class StationAdmin(admin.ModelAdmin):
    list_display = ('name', 'rkeeper_code', 'rkeeper_id', 'r_keeper_number', 'is_active')
    search_fields = ('name', 'rkeeper_code', 'rkeeper_id')
    list_filter = ('is_active',)
    actions = ['sync_menu']

    def sync_menu(self, request, queryset):
        for station in queryset:
            try:
                call_command('sync_menu_from_stations', station_id=station.id)
                self.message_user(request, f"Меню для станции {station.name} успешно синхронизировано")
            except Exception as e:
                self.message_user(request, f"Ошибка при синхронизации меню для станции {station.name}: {str(e)}", level=messages.ERROR)
    
    sync_menu.short_description = "Синхронизировать меню с R-Keeper"


