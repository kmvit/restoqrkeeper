from django.contrib import admin
from django.utils.html import format_html
from .models import QRCode
import qrcode
from io import BytesIO
from django.core.files import File
from PIL import Image

@admin.register(QRCode)
class QRCodeAdmin(admin.ModelAdmin):
    list_display = ('name', 'station_id', 'table_number', 'created_at', 'qr_code_preview')
    list_filter = ('station_id', 'table_number', 'created_at')
    search_fields = ('name', 'station_id', 'table_number')
    readonly_fields = ('qr_code_preview',)
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'domain', 'station_id', 'table_number')
        }),
        ('QR код', {
            'fields': ('qr_code', 'qr_code_preview')
        }),
    )

    def save_model(self, request, obj, form, change):
        # Генерация QR-кода
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(obj.get_full_url())
        qr.make(fit=True)

        img = qr.make_image(fill_color="black", back_color="white")
        
        # Сохранение QR-кода
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        filename = f'qr_{obj.station_id}_{obj.table_number}.png'
        obj.qr_code.save(filename, File(buffer), save=False)
        
        super().save_model(request, obj, form, change)

    def qr_code_preview(self, obj):
        if obj.qr_code:
            return format_html('<img src="{}" width="150" height="150" />', obj.qr_code.url)
        return "QR код не сгенерирован"
    qr_code_preview.short_description = 'Предпросмотр QR кода'
