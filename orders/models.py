from django.db import models
from django.conf import settings
from menu.models import MenuItem

class Waiter(models.Model):
    """
    Модель для хранения информации об официантах
    """
    code = models.CharField('Код официанта', max_length=50, unique=True)
    name = models.CharField('Имя официанта', max_length=100)
    guid = models.CharField('GUID в R-Keeper', max_length=100, blank=True, null=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Официант'
        verbose_name_plural = 'Официанты'
        ordering = ['name']

    def __str__(self):
        return f'{self.name} ({self.code})'

class Table(models.Model):
    """
    Модель для хранения информации о столах
    """
    number = models.IntegerField('Номер стола', unique=True)
    station_id = models.CharField('ID станции в R-Keeper', max_length=50)
    waiter = models.ForeignKey(Waiter, on_delete=models.SET_NULL, verbose_name='Официант', null=True, blank=True)
    is_active = models.BooleanField('Активен', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)
    updated_at = models.DateTimeField('Обновлен', auto_now=True)

    class Meta:
        verbose_name = 'Стол'
        verbose_name_plural = 'Столы'
        ordering = ['number']

    def __str__(self):
        waiter_info = f' - {self.waiter.name}' if self.waiter else ''
        return f'Стол {self.number}{waiter_info}'

class Order(models.Model):
    """
    Модель для хранения информации о заказах
    """
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('pending', 'Ожидает оплаты'),
        ('paid', 'Оплачен'),
        ('processing', 'В обработке'),
        ('completed', 'Завершен'),
        ('cancelled', 'Отменен'),
    ]

    table = models.ForeignKey(Table, on_delete=models.PROTECT, verbose_name='Стол', null=True, blank=True)
    station_id = models.CharField('ID станции в R-Keeper', max_length=50, null=True, blank=True)
    waiter = models.ForeignKey(Waiter, on_delete=models.PROTECT, verbose_name='Официант', null=True, blank=True)
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
        table_info = f' - Стол {self.table.number}' if self.table else ''
        return f'Заказ #{self.id}{table_info}'

class OrderItem(models.Model):
    """
    Модель для хранения информации о позициях заказа
    """
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
