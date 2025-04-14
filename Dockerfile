FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Установка зависимостей
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    postgresql-client \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Копирование requirements.txt
COPY requirements.txt .

# Установка зависимостей Python
RUN pip install --no-cache-dir -r requirements.txt

# Создание директорий для статических файлов и установка прав
RUN mkdir -p /app/staticfiles /app/media && \
    chmod -R 755 /app/staticfiles /app/media

# Копирование проекта
COPY . .

# Создание директорий для статических файлов в корне проекта
RUN mkdir -p /app/static/css /app/static/js /app/static/icons/fonts && \
    chmod -R 755 /app/static

# Скачивание Bootstrap и других статических файлов
RUN pip install requests && \
    python scripts/download_bootstrap.py

# Сборка статических файлов
RUN python manage.py collectstatic --noinput --clear

# Запуск приложения
CMD ["gunicorn", "restaurant_project.wsgi:application", "--bind", "0.0.0.0:8000"] 