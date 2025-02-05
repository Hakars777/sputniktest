import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL для проверки и базовый адрес для формирования полной ссылки
URL = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL = "https://am.sputniknews.ru"

# Данные для Telegram-бота (замените на свои)
TELEGRAM_BOT_TOKEN = "7816691902:AAGDGRYn9pILVyhlCTrE81HIaOITeHjXa1Y"  # Ваш Telegram Bot Token
TELEGRAM_CHAT_ID = "1032063058"  # Ваш ID чата

def send_telegram_message(message):
    """
    Отправка сообщения в Telegram через Bot API с помощью requests.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            # Если произошла ошибка, попробуем отправить уведомление повторно
            requests.get(url, params=params)
    except Exception as e:
        # Если возникает ошибка отправки, её можно обработать или проигнорировать
        pass

def get_first_post(driver):
    """
    Ожидает появления первого элемента с классом 'list__item' и извлекает:
      - заголовок (текст из тега <a class="list__title">),
      - дату (текст из элемента с классом 'date'),
      - href (ссылка, при необходимости дополняется базовым адресом).
    """
    list_item = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item"))
    )
    
    # Элемент с классом 'list__title' является тегом <a>
    list_title = list_item.find_element(By.CSS_SELECTOR, ".list__title")
    title_text = list_title.text.strip()
    href = list_title.get_attribute("href")
    if href and not href.startswith("http"):
        href = BASE_URL + href

    date_element = list_item.find_element(By.CSS_SELECTOR, ".date")
    date_text = date_element.text.strip()
    
    return title_text, date_text, href

def main():
    # Настройка опций для браузера Chrome в headless-режиме
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)
    
    try:
        send_telegram_message("Получение начального поста...")
        title, date_text, href = get_first_post(driver)
        init_message = (
            f"Начальный пост получен:\n"
            f"Заголовок: {title}\n"
            f"Дата: {date_text}\n"
            f"Ссылка: {href}"
        )
        send_telegram_message(init_message)
    except Exception as e:
        send_telegram_message(f"Ошибка при получении начального поста: {e}")
        driver.quit()
        return

    # Фиксируем дату начального поста
    current_date = date_text

    # Бесконечный цикл проверки каждые 60 минут
    while True:
        time.sleep(3600)  # 3600 секунд = 1 час
        try:
            driver.refresh()  # обновляем страницу
            send_telegram_message("Проверка на наличие нового поста...")
            new_title, new_date, new_href = get_first_post(driver)
            if new_date != current_date:
                message = (
                    f"Новый пост!\n"
                    f"Заголовок: {new_title}\n"
                    f"Дата: {new_date}\n"
                    f"Ссылка: {new_href}"
                )
                send_telegram_message(message)
                current_date = new_date
                title = new_title
        except Exception as e:
            send_telegram_message(f"Ошибка при проверке нового поста: {e}")
    
    driver.quit()

if __name__ == "__main__":
    main()