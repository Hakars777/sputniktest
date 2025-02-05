import time
import requests
import datetime
import pytz
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# URL для проверки и базовый адрес для формирования полной ссылки
URL = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL = "https://am.sputniknews.ru"

# Данные для Telegram-бота
TELEGRAM_BOT_TOKEN = "7816691902:AAGDGRYn9pILVyhlCTrE81HIaOITeHjXa1Y"
TELEGRAM_CHAT_ID = "1032063058"

# Часовой пояс Армении (GMT+4)
ARMENIA_TZ = pytz.timezone("Asia/Yerevan")

# Очередь сообщений, которые нужно отправить после снятия ограничений
delayed_messages = []

def is_within_notification_hours():
    """
    Проверяет, находится ли текущее время в разрешённом диапазоне (08:00 - 21:00).
    """
    now = datetime.datetime.now(ARMENIA_TZ).time()
    start_time = datetime.time(8, 0, 0)  # 08:00
    end_time = datetime.time(21, 0, 0)   # 21:00
    return start_time <= now <= end_time

def send_telegram_message(message):
    """
    Отправляет сообщение в Telegram. Если текущее время не в разрешённом диапазоне,
    сохраняет сообщение в очередь для отправки в 08:00.
    """
    if is_within_notification_hours():
        # Если сейчас разрешённое время, отправляем все отложенные сообщения
        while delayed_messages:
            delayed_msg = delayed_messages.pop(0)
            send_telegram_request(delayed_msg)
        
        # Отправляем текущее сообщение
        send_telegram_request(message)
    else:
        # Если время запрещено, сохраняем сообщение для отправки позже
        delayed_messages.append(message)

def send_telegram_request(message):
    """
    Фактическая отправка сообщения через Telegram API.
    """
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    params = {"chat_id": TELEGRAM_CHAT_ID, "text": message}
    try:
        response = requests.get(url, params=params)
        if response.status_code != 200:
            requests.get(url, params=params)
    except Exception:
        pass  # Игнорируем ошибки

def get_first_post(driver):
    """
    Ожидает появления первого элемента с классом 'list__item' и извлекает:
      - заголовок,
      - дату,
      - ссылку.
    """
    list_item = WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item"))
    )
    
    list_title = list_item.find_element(By.CSS_SELECTOR, ".list__title")
    title_text = list_title.text.strip()
    href = list_title.get_attribute("href")
    if href and not href.startswith("http"):
        href = BASE_URL + href

    date_element = list_item.find_element(By.CSS_SELECTOR, ".date")
    date_text = date_element.text.strip()
    
    return title_text, date_text, href

def main():
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)
    
    try:
        send_telegram_message("Последний пост ЕАЭС")
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

    current_date = date_text

    while True:
        time.sleep(3600)  # Проверяем раз в час
        try:
            driver.refresh()
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
