#!/usr/bin/env python
import os
import sys
import django
import random
from PIL import Image, ImageDraw, ImageFont

# Добавляем корневую директорию проекта в sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Настройка окружения Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "restaurant_project.settings")
django.setup()

from django.conf import settings
from django.core.management import call_command
from menu.models import MenuItem

# Цвета для заглушек изображений
COLORS = [
    (255, 99, 71),    # Томатный
    (255, 165, 0),    # Оранжевый
    (255, 215, 0),    # Золотой
    (154, 205, 50),   # Желто-зеленый
    (0, 128, 0),      # Зеленый
    (32, 178, 170),   # Морская волна
    (100, 149, 237),  # Синий
    (138, 43, 226),   # Фиолетовый
    (255, 20, 147),   # Розовый
    (139, 69, 19),    # Коричневый
]

# Функция для создания изображения-заглушки
def create_placeholder_image(food_name, save_path):
    try:
        # Создаем цветное изображение-заглушку
        width, height = 800, 600
        color = random.choice(COLORS)
        
        # Создаем новое изображение с заливкой цветом
        img = Image.new('RGB', (width, height), color)
        draw = ImageDraw.Draw(img)
        
        # Добавляем текст с названием блюда
        try:
            # Пробуем найти подходящий шрифт (может не работать в контейнере)
            font = ImageFont.truetype("Arial", 36)
        except IOError:
            font = None
        
        # Определяем координаты для центрирования текста
        text = food_name
        if font:
            text_width = draw.textlength(text, font)
            text_position = ((width - text_width) // 2, height // 2 - 18)
        else:
            text_position = (width // 4, height // 2 - 18)
        
        # Рисуем текст белым цветом
        draw.text(text_position, text, fill=(255, 255, 255), font=font)
        
        # Сохраняем изображение
        full_path = os.path.join(settings.MEDIA_ROOT, save_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        img.save(full_path)
        print(f"Создано изображение-заглушка для {food_name}: {save_path}")
        return True
    except Exception as e:
        print(f"Ошибка при создании изображения для {food_name}: {e}")
        return False

# Создаем каталог для изображений, если его нет
os.makedirs(os.path.join(settings.MEDIA_ROOT, 'menu_photos'), exist_ok=True)

# Загружаем фикстуры для категорий
print("Загружаем категории меню...")
call_command('loaddata', 'menu/fixtures/categories.json')

# Словарь соответствия имен блюд и подходящих запросов к API для изображений
food_images = {
    'Бефстроганов': 'beef_stroganoff.jpg',
    'Стейк из говядины': 'beef_steak.jpg',
    'Куриная грудка на гриле': 'grilled_chicken.jpg',
    'Борщ': 'borsch.jpg',
    'Грибной суп': 'mushroom_soup.jpg',
    'Цезарь с курицей': 'caesar_salad.jpg',
    'Греческий салат': 'greek_salad.jpg',
    'Закуска из баклажанов': 'eggplant_appetizer.jpg',
    'Сырная тарелка': 'cheese_plate.jpg',
    'Тирамису': 'tiramisu.jpg',
    'Чизкейк': 'cheesecake.jpg',
    'Латте': 'latte.jpg',
    'Фреш апельсиновый': 'orange_juice.jpg',
    'Чай зеленый': 'green_tea.jpg'
}

# Создаем изображения-заглушки для блюд
print("Создаем изображения для блюд...")
for food_name, image_name in food_images.items():
    image_path = f"menu_photos/{image_name}"
    create_placeholder_image(food_name, image_path)

# Загружаем фикстуры для позиций меню
print("Загружаем позиции меню...")
call_command('loaddata', 'menu/fixtures/menu_items.json')

print("Загрузка данных завершена!") 