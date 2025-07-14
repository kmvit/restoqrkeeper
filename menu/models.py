from django.db import models

# Create your models here.

class Station(models.Model):
    """Станция R-Keeper"""
    name = models.CharField(max_length=100, verbose_name='Название станции')
    rkeeper_code = models.CharField(max_length=10, verbose_name='Код станции в R-Keeper', unique=True)
    rkeeper_id = models.CharField(max_length=10, verbose_name='ID станции в R-Keeper', null=True, blank=True)
    r_keeper_number = models.IntegerField(verbose_name='Номер станции в R-Keeper', null=True, blank=True)
    is_active = models.BooleanField(default=True, verbose_name='Активна')

    class Meta:
        verbose_name = 'Станция'
        verbose_name_plural = 'Станции'

    def __str__(self):
        return self.name

class Category(models.Model):
    """Категория товара"""
    name = models.CharField(max_length=100, verbose_name='Название категории')
    station = models.ForeignKey(Station, on_delete=models.CASCADE, verbose_name='Станция', null=True, blank=True)
    rkeeper_id = models.CharField(max_length=50, verbose_name='ID в R-Keeper', null=True, blank=True)

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'
        unique_together = ['name', 'station']

    def __str__(self):
        return f"{self.name} ({self.station.name if self.station else 'Общая'})"

class MenuItem(models.Model):
    """Товар"""
    name = models.CharField(max_length=200, verbose_name='Название блюда')
    name_kk = models.CharField(max_length=200, verbose_name='Название блюда (казахский)', null=True, blank=True)
    photo = models.ImageField(upload_to='menu_photos/', verbose_name='Фото', null=True, blank=True)
    description = models.TextField(verbose_name='Состав', null=True, blank=True)
    description_kk = models.TextField(verbose_name='Состав (казахский)', null=True, blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=0, verbose_name='Цена', default=0)
    quantity = models.PositiveIntegerField(verbose_name='Количество', default=0)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория')
    station = models.ForeignKey(Station, on_delete=models.CASCADE, verbose_name='Станция', null=True, blank=True)
    rkeeper_id = models.CharField(max_length=50, verbose_name='ID в R-Keeper', null=True, blank=True)
    is_available = models.BooleanField(default=True, verbose_name='Доступно')
    stop_list = models.BooleanField(default=True, verbose_name='Выключено в меню вручную')
    last_updated = models.DateTimeField(auto_now=True, verbose_name='Последнее обновление')

    class Meta:
        verbose_name = 'Позиция меню'
        verbose_name_plural = 'Позиции меню'
        unique_together = ['rkeeper_id', 'station']

    def __str__(self):
        return f"{self.name} ({self.station.name if self.station else 'Без станции'})"
