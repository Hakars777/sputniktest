# Используем официальный Python-образ (slim для компактности)
FROM python:3.9-slim

# Отключаем запись .pyc-файлов и буферизацию вывода для корректного логирования
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей и устанавливаем их
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Копируем исходный код приложения
COPY main.py .

# Запускаем приложение при старте контейнера
CMD ["python", "main.py"]
