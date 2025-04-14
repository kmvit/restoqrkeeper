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

# Копирование проекта
COPY . .

# Скачивание Bootstrap и других статических файлов
RUN pip install requests && \
    mkdir -p static/css static/js static/icons && \
    python scripts/download_bootstrap.py && \
    python manage.py collectstatic --noinput

# Запуск приложения
CMD ["gunicorn", "restaurant_project.wsgi:application", "--bind", "0.0.0.0:8000"] 