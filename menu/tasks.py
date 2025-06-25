from celery import shared_task
from django.core.management import call_command
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)

@shared_task(bind=True, max_retries=3, default_retry_delay=300)
def sync_menu_from_stations_task(self):
    """
    Задача для периодической синхронизации меню из R-Keeper станций
    """
    try:
        logger.info("Запуск задачи синхронизации меню из станций R-Keeper")
        
        # Вызываем Django команду для синхронизации
        call_command('sync_menu_from_stations', '--verbosity=2')
        
        logger.info("Синхронизация меню завершена успешно")
        return {
            'status': 'success',
            'message': 'Синхронизация меню завершена успешно',
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Ошибка при синхронизации меню: {str(exc)}")
        
        # Повторяем задачу при ошибке
        try:
            self.retry(countdown=300, exc=exc)  # повтор через 5 минут
        except self.MaxRetriesExceededError:
            logger.error("Превышено максимальное количество попыток синхронизации меню")
            return {
                'status': 'error',
                'message': f'Ошибка синхронизации после {self.max_retries} попыток: {str(exc)}',
                'timestamp': timezone.now().isoformat()
            }

@shared_task
def manual_sync_menu_task(station_codes=None):
    """
    Задача для ручной синхронизации меню (запускается из админки)
    
    Args:
        station_codes (list): Список кодов станций для синхронизации.
                             Если None, синхронизируются все станции.
    """
    try:
        logger.info(f"Запуск ручной синхронизации меню для станций: {station_codes or 'все'}")
        
        # Формируем аргументы команды
        cmd_args = ['sync_menu_from_stations', '--verbosity=2']
        if station_codes:
            cmd_args.extend(['--stations'] + station_codes)
        
        # Вызываем Django команду
        call_command(*cmd_args)
        
        logger.info("Ручная синхронизация меню завершена успешно")
        return {
            'status': 'success',
            'message': f'Ручная синхронизация меню завершена для станций: {station_codes or "все"}',
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Ошибка при ручной синхронизации меню: {str(exc)}")
        return {
            'status': 'error',
            'message': f'Ошибка ручной синхронизации: {str(exc)}',
            'timestamp': timezone.now().isoformat()
        } 