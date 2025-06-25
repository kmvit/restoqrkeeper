import os
from celery import Celery
from django.conf import settings

# Устанавливаем модуль настроек Django для программы Celery
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'restaurant_project.settings')

app = Celery('restaurant_project')

# Используем строку конфигурации для настройки Celery из настроек Django
# с префиксом CELERY_ для всех настроек, связанных с Celery
app.config_from_object('django.conf:settings', namespace='CELERY')

# Автозагрузка задач из всех зарегистрированных приложений Django
app.autodiscover_tasks()

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}') 