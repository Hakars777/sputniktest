# Используем официальный python-образ (slim для компактности)
FROM python:3.9-slim

# Обновляем пакеты и ставим Chrome/Chromedriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    # чистим кэш apt
    && rm -rf /var/lib/apt/lists/*

# Создадим рабочую папку внутри контейнера
WORKDIR /app

# Скопируем список зависимостей и установим их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем сам скрипт
COPY main.py .

# Запускаем скрипт при старте контейнера
CMD ["python", "main.py"]