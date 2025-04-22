from django.core.management.base import BaseCommand
from menu.models import MenuItem, Category
from django.db import transaction

class Command(BaseCommand):
    help = 'Удаляет все позиции меню и категории из базы данных'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Принудительное удаление без подтверждения',
        )

    def handle(self, *args, **options):
        if not options['force']:
            confirm = input('Вы уверены, что хотите удалить все позиции меню и категории? [y/N]: ')
            if confirm.lower() != 'y':
                self.stdout.write(self.style.WARNING('Операция отменена'))
                return

        try:
            with transaction.atomic():
                # Сначала удаляем все позиции меню
                menu_items_count = MenuItem.objects.count()
                MenuItem.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'Удалено {menu_items_count} позиций меню'))

                # Затем удаляем все категории
                categories_count = Category.objects.count()
                Category.objects.all().delete()
                self.stdout.write(self.style.SUCCESS(f'Удалено {categories_count} категорий'))

        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Ошибка при удалении: {str(e)}')) 