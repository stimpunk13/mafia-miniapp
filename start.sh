#!/bin/bash

echo "========================================"
echo "  МАФИЯ - Telegram Mini App"
echo "========================================"
echo ""

echo "Проверка Python..."
if ! command -v python3 &> /dev/null; then
    echo "ОШИБКА: Python не установлен!"
    echo "Установите Python 3.8+"
    exit 1
fi

echo "Python найден!"
echo ""

cd backend

echo "Установка зависимостей..."
pip3 install -r requirements.txt

echo ""
echo "========================================"
echo "  Запуск сервера..."
echo "========================================"
echo ""
echo "Откройте в браузере:"
echo "http://localhost:8000/static/index.html"
echo ""
echo "Для остановки нажмите Ctrl+C"
echo "========================================"
echo ""

python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000
