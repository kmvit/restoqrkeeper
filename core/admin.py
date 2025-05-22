from django.contrib import admin
from .models import Page

@admin.register(Page)
class PageAdmin(admin.ModelAdmin):
    list_display = ('title', 'slug', 'is_published', 'show_in_menu', 'order', 'created_at', 'updated_at')
    list_filter = ('is_published', 'show_in_menu')
    search_fields = ('title', 'content')
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ('is_published', 'show_in_menu', 'order')
    fieldsets = (
        (None, {
            'fields': ('title', 'slug', 'content')
        }),
        ('Настройки публикации', {
            'fields': ('is_published', 'show_in_menu', 'order')
        }),
    )
