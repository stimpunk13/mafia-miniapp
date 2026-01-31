@echo off
echo ========================================
echo   МАФИЯ - Telegram Mini App
echo ========================================
echo.

echo Проверка Python...
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ОШИБКА: Python не установлен!
    echo Скачайте с https://www.python.org/downloads/
    pause
    exit /b 1
)

echo Python найден!
echo.

cd backend

echo Установка зависимостей...
pip install -r requirements.txt

echo.
echo ========================================
echo   Запуск сервера...
echo ========================================
echo.
echo Откройте в браузере:
echo http://localhost:8000/static/index.html
echo.
echo Для остановки нажмите Ctrl+C
echo ========================================
echo.

uvicorn main:app --reload --host 0.0.0.0 --port 8000

pause
