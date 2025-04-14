from django.db import models

# Create your models here.

class Category(models.Model):
    """Категория товара"""
    name = models.CharField(max_length=100, verbose_name='Название категории')

    class Meta:
        verbose_name = 'Категория'
        verbose_name_plural = 'Категории'

    def __str__(self):
        return self.name

class MenuItem(models.Model):
    """Товар"""
    name = models.CharField(max_length=200, verbose_name='Название блюда')
    photo = models.ImageField(upload_to='menu_photos/', verbose_name='Фото')
    description = models.TextField(verbose_name='Состав')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Цена', default=0)
    quantity = models.PositiveIntegerField(verbose_name='Количество')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name='Категория')

    class Meta:
        verbose_name = 'Позиция меню'
        verbose_name_plural = 'Позиции меню'

    def __str__(self):
        return self.name
