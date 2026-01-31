# ⚡ БЫСТРЫЙ СТАРТ

## 1. Установите Python
https://www.python.org/downloads/
✅ Галочка "Add Python to PATH"

## 2. Откройте терминал в папке backend
```bash
cd mafia_miniapp/backend
```

## 3. Установите библиотеки
```bash
pip install -r requirements.txt
```

## 4. Запустите сервер
```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## 5. Откройте в браузере
```
http://localhost:8000/static/index.html
```

---

## Для Telegram:

1. Создайте бота у @BotFather
2. Используйте ngrok для HTTPS:
   ```bash
   ngrok http 8000
   ```
3. Обновите URL в @BotFather и в `frontend/index.html`

**Подробная инструкция в файле ИНСТРУКЦИЯ.md**
