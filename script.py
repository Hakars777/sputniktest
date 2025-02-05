import time
import threading
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# Данные для Telegram-бота
TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Разрешённые чаты (только для указанных chat_id)
ALLOWED_CHATS = {1032063058, 287714154}  # Добавьте нужные chat_id

# Флаг работы мониторинга для каждого чата
active_chats = {}

# URL для проверки и базовый адрес для формирования полной ссылки
URL = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL = "https://am.sputniknews.ru"


def send_telegram_message(chat_id, message):
    """Отправляет сообщение в Telegram только для разрешённых chat_id."""
    if chat_id in ALLOWED_CHATS:
        bot.send_message(chat_id, message)


def get_first_post(driver):
    """Получает первый пост с сайта."""
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


def monitor_news(chat_id):
    """Функция мониторинга новостей, работающая в фоновом потоке для каждого чата."""
    if chat_id not in ALLOWED_CHATS:
        return  # Игнорируем чаты, которым не разрешено получать уведомления

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
        send_telegram_message(chat_id, init_message)
    except Exception as e:
        send_telegram_message(chat_id, f"Ошибка при получении начального поста: {e}")
        driver.quit()
        active_chats.pop(chat_id, None)  # Удаляем чат из активных при ошибке
        return

    current_date = date_text

    while chat_id in active_chats:
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
                send_telegram_message(chat_id, message)
                current_date = new_date
        except Exception as e:
            send_telegram_message(chat_id, f"Ошибка при проверке нового поста: {e}")

    driver.quit()
    active_chats.pop(chat_id, None)  # Удаляем чат из активных после завершения


# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id

    if chat_id not in ALLOWED_CHATS:
        return

    if chat_id in active_chats:
        bot.send_message(chat_id, "Бот запущен! Начинаю мониторинг...")
        return
    
    active_chats[chat_id] = True  # Чат сразу добавляется в активные

    thread = threading.Thread(target=monitor_news, args=(chat_id,), daemon=True)
    thread.start()


# Обработчик команды /stop
@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    active_chats.pop(chat_id, None)  # Полностью удаляем чат из списка активных


# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)