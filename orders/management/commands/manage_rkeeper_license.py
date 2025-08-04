from django.core.management.base import BaseCommand
from orders.services.rkeeper_service import RKeeperService
from django.core.cache import cache
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Управление состоянием лицензии R-Keeper'

    def add_arguments(self, parser):
        parser.add_argument(
            '--action',
            type=str,
            choices=['status', 'reset', 'sync'],
            help='Действие: status (показать статус), reset (сбросить), sync (синхронизировать)'
        )

    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.stdout.write(
                self.style.ERROR('Необходимо указать действие: --action status|reset|sync')
            )
            return

        rkeeper_service = RKeeperService()
        cache_key = rkeeper_service.cache_key

        if action == 'status':
            self._show_status(cache_key)
        elif action == 'reset':
            self._reset_license(rkeeper_service)
        elif action == 'sync':
            self._sync_license(rkeeper_service)

    def _show_status(self, cache_key):
        """Показать текущий статус лицензии"""
        try:
            current_seq = cache.get(cache_key)
            if current_seq is not None:
                self.stdout.write(
                    self.style.SUCCESS(f'Текущий seqNumber в кэше: {current_seq}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('seqNumber не установлен в кэше')
                )
                
            # Попытаемся получить seqNumber с сервера
            rkeeper_service = RKeeperService()
            try:
                server_seq = rkeeper_service._get_license_seq()
                self.stdout.write(
                    self.style.SUCCESS(f'seqNumber на сервере R-Keeper: {server_seq}')
                )
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'Ошибка получения seqNumber с сервера: {e}')
                )
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при проверке статуса: {e}')
            )

    def _reset_license(self, rkeeper_service):
        """Сбросить состояние лицензии"""
        try:
            result = rkeeper_service.reset_license_seq()
            if result:
                self.stdout.write(
                    self.style.SUCCESS('seqNumber лицензии успешно сброшен')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Ошибка при сбросе seqNumber лицензии')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при сбросе лицензии: {e}')
            )

    def _sync_license(self, rkeeper_service):
        """Синхронизировать состояние лицензии с сервером"""
        try:
            result = rkeeper_service.sync_license_seq()
            if result:
                self.stdout.write(
                    self.style.SUCCESS('seqNumber лицензии успешно синхронизирован с сервером')
                )
            else:
                self.stdout.write(
                    self.style.ERROR('Ошибка при синхронизации seqNumber лицензии')
                )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Ошибка при синхронизации лицензии: {e}')
            )