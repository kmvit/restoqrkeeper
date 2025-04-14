from django.contrib import admin
from .models import Order, OrderItem

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('price', 'total')
    fields = ('menu_item', 'quantity', 'price', 'total')

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'table_number', 'total_amount', 'status', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('id', 'table_number', 'payment_id', 'rkeeper_order_id')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('table_number', 'total_amount', 'status')
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
