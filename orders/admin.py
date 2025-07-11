from django.contrib import admin
from .models import Order, OrderItem, Waiter, Table

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price', 'total')
    fields = ('menu_item', 'quantity', 'price', 'total')

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
    list_display = ('name','number', 'station_id', 'waiter', 'is_active')
    list_filter = ('is_active', 'station_id')
    search_fields = ('number', 'station_id', 'waiter__name')
    ordering = ('number',)
    autocomplete_fields = ['waiter']
    fieldsets = (
        ('Основная информация', {
            'fields': ('number', 'name', 'station_id', 'waiter')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'station_id', 'table', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'table__number', 'payment_id', 'rkeeper_order_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('station_id', 'table', 'total_amount', 'status')
        }),
        ('Платежная информация', {
            'fields': ('payment_id', 'rkeeper_order_id')
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )

@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ('id', 'order', 'menu_item', 'quantity', 'price', 'total')
    list_filter = ('order__status', 'menu_item__category')
    search_fields = ('order__id', 'menu_item__name')
    readonly_fields = ('total',)
    
    def get_readonly_fields(self, request, obj=None):
        if obj:  # Редактирование существующего объекта
            return self.readonly_fields + ('price',)
        return self.readonly_fields

@admin.register(Waiter)
class WaiterAdmin(admin.ModelAdmin):
    list_display = ('name', 'code', 'guid', 'is_active', 'created_at')
    list_filter = ('is_active',)
    search_fields = ('name', 'code', 'guid')
    ordering = ('name',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'code', 'guid')
        }),
        ('Статус', {
            'fields': ('is_active',)
        }),
        ('Временные метки', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ('created_at', 'updated_at')
