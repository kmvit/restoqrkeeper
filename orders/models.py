from django.db import models
from django.conf import settings
from menu.models import MenuItem

class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    table_number = models.IntegerField('Номер стола', null=True, blank=True)
    station_id = models.CharField('ID станции в R-Keeper', max_length=50, null=True, blank=True)
    total_amount = models.DecimalField('Общая сумма', max_digits=10, decimal_places=2)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    rkeeper_license_seq = models.IntegerField('SeqNumber лицензирования', default=0)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)
    payment_id = models.CharField('ID платежа', max_length=100, blank=True, null=True)
    rkeeper_order_id = models.CharField('ID заказа в R-Keeper', max_length=100, blank=True, null=True)
    comment = models.TextField('Комментарий', null=True, blank=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.id} - Стол {self.table_number}'

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items', verbose_name='Заказ')
    menu_item = models.ForeignKey(MenuItem, on_delete=models.PROTECT, verbose_name='Позиция меню')
    quantity = models.PositiveIntegerField('Количество')
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    total = models.DecimalField('Итого', max_digits=10, decimal_places=2)
    comment = models.TextField('Комментарий', null=True, blank=True)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.menu_item.name} x{self.quantity}'

    def save(self, *args, **kwargs):
        if not self.price:
            self.price = self.menu_item.price
        self.total = self.price * self.quantity
        super().save(*args, **kwargs)
