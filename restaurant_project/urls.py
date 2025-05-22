"""
URL configuration for restaurant_project project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.views.generic import RedirectView
from django.conf.urls.i18n import i18n_patterns

# URL-адреса, не зависящие от языка
urlpatterns = [
    path('i18n/', include('django.conf.urls.i18n')),  # URL для переключения языков
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

# URL-адреса, зависящие от языка
urlpatterns += i18n_patterns(
    path('admin/', admin.site.urls),
    path('menu/', include('menu.urls', namespace='menu')),
    path('orders/', include('orders.urls')),
    path('', include('core.urls', namespace='core')),  # Добавляем URL-адреса core
    path('', RedirectView.as_view(url='/menu/', permanent=True), name='home'),
    prefix_default_language=True,  # Включаем префикс для языка по умолчанию
)

# Добавляем обслуживание статических файлов в режиме DEBUG
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATICFILES_DIRS[0])
    # Если вы настроили MEDIA_URL/MEDIA_ROOT и хотите обслуживать медиафайлы локально:
    # urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    # Закомментировал строку выше, т.к. обслуживание MEDIA уже добавлено ранее, но это стандартное место
