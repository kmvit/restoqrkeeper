from django.db import models
from django.utils.translation import gettext_lazy as _
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError

class QRCode(models.Model):
    name = models.CharField(_('Название'), max_length=100)
    domain = models.CharField(_('Домен'), max_length=200, validators=[URLValidator()])
    station_id = models.CharField(_('ID станции'), max_length=50)
    table_number = models.PositiveIntegerField(_('Номер стола'))
    qr_code = models.ImageField(_('QR код'), upload_to='qr_codes/', blank=True, null=True)
    created_at = models.DateTimeField(_('Дата создания'), auto_now_add=True)
    updated_at = models.DateTimeField(_('Дата обновления'), auto_now=True)

    class Meta:
        verbose_name = _('QR код')
        verbose_name_plural = _('QR коды')
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.name} - Стол {self.table_number}"

    def get_full_url(self):
        """Генерирует полный URL для QR-кода"""
        return f"{self.domain}/ru/menu/?station_id={self.station_id}&table={self.table_number}"

    def clean(self):
        """Проверка валидности данных"""
        if not self.domain.startswith(('http://', 'https://')):
            raise ValidationError(_('Домен должен начинаться с http:// или https://'))
