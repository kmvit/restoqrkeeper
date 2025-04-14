#!/bin/bash

# Переходим в корневую директорию проекта
cd /app

# Сделаем скрипт Python исполняемым
chmod +x scripts/load_fixtures.py

# Устанавливаем необходимые пакеты, если их нет
pip install requests pillow

# Запустим загрузку фикстур
python scripts/load_fixtures.py 