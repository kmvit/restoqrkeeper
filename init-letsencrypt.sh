#!/bin/bash

# Проверка на наличие docker-compose
if ! [ -x "$(command -v docker-compose)" ]; then
  echo 'Ошибка: docker-compose не установлен.' >&2
  exit 1
fi

# Домен и email для Let's Encrypt
domains=(2a0aa2c90f37.vps.myjino.ru)
email="" # Добавьте свой email, он нужен для уведомлений о продлении сертификата
staging=0 # Для тестов используйте staging=1, для продакшена staging=0

# Пути к файлам сертификатов
data_path="./nginx/ssl"
mkdir -p "$data_path"
mkdir -p "./nginx/certbot/www"

if [ -d "$data_path/live/$domains" ]; then
  read -p "Найдены существующие сертификаты для $domains. Продолжить и заменить их? (y/N): " decision
  if [ "$decision" != "Y" ] && [ "$decision" != "y" ]; then
    exit
  fi
fi

# Генерируем временный самоподписанный сертификат
echo "### Создание временного самоподписанного сертификата для $domains ..."
path="/etc/letsencrypt/live/$domains"
mkdir -p "$data_path/live/$domains"

docker-compose run --rm --entrypoint "\
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '$path/privkey.pem' \
    -out '$path/fullchain.pem' \
    -subj '/CN=localhost'" certbot

echo "### Запуск nginx ..."
docker-compose up -d nginx

# Удаляем временный сертификат
echo "### Удаление временного сертификата ..."
docker-compose run --rm --entrypoint "\
  rm -Rf /etc/letsencrypt/live/$domains" certbot

# Запрашиваем реальный сертификат Let's Encrypt
echo "### Запрос сертификата Let's Encrypt для $domains ..."

# Подготовка аргументов
domain_args=""
for domain in "${domains[@]}"; do
  domain_args="$domain_args -d $domain"
done

case "$email" in
  "") email_arg="--register-unsafely-without-email" ;;
  *) email_arg="--email $email" ;;
esac

if [ $staging -eq 1 ]; then
  staging_arg="--staging"
else
  staging_arg=""
fi

# Запрос сертификата
docker-compose run --rm --entrypoint "\
  certbot certonly --webroot -w /var/www/certbot \
    $staging_arg \
    $email_arg \
    $domain_args \
    --rsa-key-size 4096 \
    --agree-tos \
    --force-renewal" certbot

# Перезапускаем nginx для применения новых сертификатов
echo "### Перезапуск nginx ..."
docker-compose exec nginx nginx -s reload 