#!/usr/bin/env python
import os
import requests
from pathlib import Path

def download_file(url, save_path):
    try:
        response = requests.get(url)
        if response.status_code == 200:
            # Создаем директорию, если она не существует
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            
            # Сохраняем файл
            with open(save_path, 'wb') as f:
                f.write(response.content)
            
            print(f"Успешно скачано: {url} -> {save_path}")
            return True
        else:
            print(f"Ошибка скачивания {url}, статус: {response.status_code}")
            return False
    except Exception as e:
        print(f"Ошибка при скачивании {url}: {e}")
        return False

def main():
    # Базовый путь для статических файлов
    base_dir = Path(__file__).resolve().parent.parent
    static_dir = base_dir / 'static'
    
    # Создаем директории
    os.makedirs(static_dir / 'css', exist_ok=True)
    os.makedirs(static_dir / 'js', exist_ok=True)
    os.makedirs(static_dir / 'icons', exist_ok=True)
    
    # URLs для скачивания
    bootstrap_css_url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
    bootstrap_js_url = "https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"
    bootstrap_icons_url = "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/bootstrap-icons.css"
    
    # Пути для сохранения
    bootstrap_css_path = static_dir / 'css' / 'bootstrap.min.css'
    bootstrap_js_path = static_dir / 'js' / 'bootstrap.bundle.min.js'
    bootstrap_icons_path = static_dir / 'css' / 'bootstrap-icons.css'
    
    # Скачиваем файлы
    print("Скачиваем Bootstrap CSS...")
    download_file(bootstrap_css_url, bootstrap_css_path)
    
    print("Скачиваем Bootstrap JS...")
    download_file(bootstrap_js_url, bootstrap_js_path)
    
    print("Скачиваем Bootstrap Icons CSS...")
    download_file(bootstrap_icons_url, bootstrap_icons_path)
    
    # Скачиваем иконки Bootstrap Icons (шрифты)
    fonts_urls = [
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/fonts/bootstrap-icons.woff",
        "https://cdn.jsdelivr.net/npm/bootstrap-icons@1.11.1/font/fonts/bootstrap-icons.woff2"
    ]
    
    print("Скачиваем шрифты Bootstrap Icons...")
    icons_dir = static_dir / 'icons' / 'fonts'
    os.makedirs(icons_dir, exist_ok=True)
    
    for url in fonts_urls:
        filename = url.split('/')[-1]
        download_file(url, icons_dir / filename)
    
    print("Обновляем пути в CSS файле Bootstrap Icons...")
    try:
        # Читаем CSS файл
        with open(bootstrap_icons_path, 'r') as f:
            css_content = f.read()
        
        # Заменяем пути к шрифтам
        css_content = css_content.replace('./fonts/', '/static/icons/fonts/')
        
        # Записываем обновленный CSS
        with open(bootstrap_icons_path, 'w') as f:
            f.write(css_content)
        
        print("Пути к шрифтам в CSS файле успешно обновлены.")
    except Exception as e:
        print(f"Ошибка при обновлении путей в CSS файле: {e}")
    
    print("Скачивание завершено!")

if __name__ == "__main__":
    main() 