import time
import datetime
import pytz
import threading
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Данные для Telegram-бота
TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
# ID чата (будет автоматически обновляться при /start)
CHAT_ID = "1032063058"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)


# Флаг работы мониторинга
is_running = False

# Часовой пояс Армении (GMT+4)
ARMENIA_TZ = pytz.timezone("Asia/Yerevan")

# Очередь сообщений, которые нужно отправить после снятия ограничений
delayed_messages = []
last_sent_message = None  # Храним последнее отправленное сообщение, чтобы не дублировать

# URL для проверки и базовый адрес для формирования полной ссылки
URL = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL = "https://am.sputniknews.ru"


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
    Отправляет сообщение в Telegram через telebot.
    Если сообщение уже отправлено ранее, не дублирует его.
    Если текущее время не в разрешённом диапазоне, сохраняет сообщение в очередь для отправки в 08:00.
    """
    global CHAT_ID, last_sent_message

    if CHAT_ID is None:
        return  # Не отправляем, если чат не установлен

    if is_within_notification_hours():
        # Отправляем отложенные сообщения, если они есть
        while delayed_messages:
            delayed_msg = delayed_messages.pop(0)
            if delayed_msg != last_sent_message:
                bot.send_message(CHAT_ID, delayed_msg)
                last_sent_message = delayed_msg

        # Отправляем текущее сообщение, если оно не дублируется
        if message != last_sent_message:
            bot.send_message(CHAT_ID, message)
            last_sent_message = message
    else:
        if message not in delayed_messages:
            delayed_messages.append(message)  # Добавляем в очередь только если сообщения ещё нет


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


def monitor_news():
    global is_running
    is_running = True

    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(URL)

    try:
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
        is_running = False
        return

    current_date = date_text

    while is_running:
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
        except Exception as e:
            send_telegram_message(f"Ошибка при проверке нового поста: {e}")

    driver.quit()


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    global is_running, CHAT_ID
    CHAT_ID = message.chat.id

    if is_running:
        return

    bot.send_message(CHAT_ID, "Бот запущен! Начинаю мониторинг...")
    thread = threading.Thread(target=monitor_news, daemon=True)
    thread.start()


# Обработчик команды /stop
@bot.message_handler(commands=['stop'])
def stop_command(message):
    global is_running
    if not is_running:
        bot.send_message(message.chat.id, "Мониторинг остановлен.")
        return

    is_running = False

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)