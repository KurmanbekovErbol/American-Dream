#!/bin/bash
set -e

PROJECT_DIR="/var/www/american-dream"
VENV_DIR="$PROJECT_DIR/venv"

echo ">>> Переходим в проект"
cd $PROJECT_DIR

echo ">>> Активируем виртуальное окружение"
source $VENV_DIR/bin/activate

echo ">>> Обновляем pip и устанавливаем зависимости"
pip install --upgrade pip setuptools wheel
pip install -r requirements.txt

echo ">>> Делаем миграции"
python manage.py makemigrations --noinput
python manage.py migrate --noinput

echo ">>> Перезапускаем gunicorn"
sudo systemctl restart gunicorn

echo ">>> Перезапускаем nginx"
sudo systemctl reload nginx

echo ">>> ✅ Деплой завершён!"
