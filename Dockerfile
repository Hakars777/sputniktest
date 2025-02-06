# Используем официальный python-образ (slim для компактности)
FROM python:3.9-slim

# Обновляем пакеты и устанавливаем необходимые зависимости, а также Chrome и Chromedriver
RUN apt-get update && apt-get install -y \
    chromium \
    chromium-driver \
    libnss3 \
    libgconf-2-4 \
    libasound2 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdbus-1-3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    xdg-utils \
    && rm -rf /var/lib/apt/lists/*

# Задаём переменную окружения для Chromium
ENV CHROME_BIN=/usr/bin/chromium

# Создадим рабочую папку внутри контейнера
WORKDIR /app

# Копируем список зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем сам скрипт
COPY script.py .

# Запускаем скрипт при старте контейнера
CMD ["python", "script.py"]
