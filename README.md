# RestoQRKeeper

Веб-приложение Django для ресторанов с QR-кодами на столах, интеграцией с R-Keeper и оплатой через ForteBank.

## Описание проекта

RestoQRKeeper - это веб-приложение для ресторанов, которое позволяет посетителям сканировать QR-код на столе, просматривать меню, добавлять блюда в корзину и оплачивать заказ через ForteBank. Приложение интегрируется с системой R-Keeper для передачи заказов на кухню.

### Основные возможности

- Отображение меню ресторана с категориями и детальной информацией о блюдах
- Корзина с возможностью добавления и удаления позиций
- Оплата заказа через ForteBank
- Интеграция с R-Keeper для передачи заказов и синхронизации меню
- Определение номера стола из QR-кода
- Административная панель для управления меню и заказами

## Требования

- Docker и Docker Compose
- Git

## Быстрый старт

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/restoqrkeeper.git
cd restoqrkeeper
```

2. Создайте файл .env на основе примера:
```bash
cp .env.example .env
```

3. Запустите проект с помощью Docker Compose:
```bash
docker-compose up -d
```

4. Загрузите тестовые данные:
```bash
docker-compose exec web bash scripts/load_fixtures.sh
```

5. Приложение будет доступно по адресу: http://localhost

## Структура проекта

- **menu/** - приложение для управления меню ресторана
- **orders/** - приложение для управления заказами и оплатой
- **core/** - общие функции и утилиты
- **restaurant_project/** - основной проект Django
- **templates/** - HTML шаблоны
- **static/** - статические файлы (CSS, JS, изображения)
- **media/** - загружаемые файлы (фотографии блюд)
- **scripts/** - вспомогательные скрипты
- **nginx/** - конфигурация Nginx

## Технологии

- Python 3.11
- Django 5.2
- PostgreSQL
- Gunicorn
- Nginx
- Docker
- Bootstrap 5
- ForteBank Payment API
- R-Keeper XML API

## Разработка

Для запуска проекта в режиме разработки:

```bash
# Запуск с отображением логов
docker-compose up

# Запуск в фоновом режиме
docker-compose up -d

# Остановка контейнеров
docker-compose down

# Просмотр логов
docker-compose logs -f

# Выполнение команд Django
docker-compose exec web python manage.py <command>
```

## Лицензия

MIT

## Авторы

- Ваше имя

## Интеграция с R-Keeper и ForteBank

Для настройки интеграции с R-Keeper и ForteBank необходимо указать соответствующие параметры в файле .env:

```
# Настройки для ForteBank
FORTEBANK_API_URL=https://api.fortebank.kz
FORTEBANK_MERCHANT_ID=your_merchant_id
FORTEBANK_SECRET_KEY=your_secret_key

# Настройки для R-Keeper
RKEEPER_API_URL=http://your-rkeeper-server/api
RKEEPER_USERNAME=your_username
RKEEPER_PASSWORD=your_password
```

## Настройка домена

Для настройки нового домена yourproject.website необходимо внести изменения в два файла:

1. В файле `.env` добавьте домен в список разрешенных хостов и обновите основной URL сайта:

```
# Обновите список разрешенных хостов
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1] yourproject.website

# Измените основной URL сайта
SITE_URL=http://yourproject.website
```

2. В файле `nginx/nginx.conf` добавьте домен в директиву `server_name`:

```nginx
server {
    listen 80;
    server_name localhost yourproject.website;
    # остальная конфигурация...
}
```

3. После внесения изменений перезапустите контейнеры:

```bash
docker-compose down
docker-compose up -d
```

### Пример полной конфигурации

Для примера, если у вас есть домен yourproject.website, конфигурация будет выглядеть так:

В `.env`:
```
DJANGO_ALLOWED_HOSTS=localhost 127.0.0.1 [::1] yourproject.website
SITE_URL=http://yourproject.website
```

В `nginx/nginx.conf`:
```nginx
server {
    listen 80;
    server_name localhost yourproject.website;
    # остальная конфигурация...
}
```

Такой подход позволяет быстро менять домены без редактирования кода приложения. 