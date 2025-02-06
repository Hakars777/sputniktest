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
ALLOWED_CHATS = {1032063058, 287714154}

# Флаг работы мониторинга для каждого чата
active_chats = {}

# Параметры для сайта RU
URL_RU = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL_RU = "https://am.sputniknews.ru"

# Параметры для сайта AM
URL_AM = "https://arm.sputniknews.ru/search/?query=%D4%B5%D4%B1%D5%8F%D5%84"
BASE_URL_AM = "https://arm.sputniknews.ru"

def send_telegram_message(chat_id, message):
    """Отправляет сообщение в Telegram только для разрешённых chat_id."""
    if chat_id in ALLOWED_CHATS:
        bot.send_message(chat_id, message)

def get_all_posts(driver, base_url):
    """
    Получает список всех постов на странице.
    Каждый элемент списка – кортеж (title, date, href).
    """
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item"))
    )
    posts_elements = driver.find_elements(By.CSS_SELECTOR, ".list__item")
    posts = []
    for item in posts_elements:
        list_title = item.find_element(By.CSS_SELECTOR, ".list__title")
        title_text = list_title.text.strip()
        href = list_title.get_attribute("href")
        if href and not href.startswith("http"):
            href = base_url + href
        date_element = item.find_element(By.CSS_SELECTOR, ".date")
        date_text = date_element.text.strip()
        posts.append((title_text, date_text, href))
    return posts

def create_driver():
    """
    Создаёт экземпляр Chrome с нужными параметрами для работы в контейнере.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-shm-usage")
    # Дополнительные параметры для снижения нагрузки (опционально)
    chrome_options.add_argument("--single-process")
    chrome_options.add_argument("--no-zygote")
    return webdriver.Chrome(options=chrome_options)

def monitor_news(chat_id):
    """
    Функция мониторинга для обоих сайтов в одном потоке.
    Для каждого сайта создаётся свой драйвер и запоминается исходный (самый новый) пост.
    Затем в цикле с заданным интервалом производится последовательная проверка обновлений.
    """
    # Создаем драйверы для каждого сайта
    try:
        driver_ru = create_driver()
        driver_am = create_driver()
    except Exception as e:
        send_telegram_message(chat_id, f"Ошибка при создании драйверов: {e}")
        return

    # Переходим на нужные страницы
    try:
        driver_ru.get(URL_RU)
        driver_am.get(URL_AM)
    except Exception as e:
        send_telegram_message(chat_id, f"Ошибка при переходе на страницу: {e}")
        driver_ru.quit()
        driver_am.quit()
        return

    # Получаем исходные (самые новые) посты для каждого сайта
    try:
        posts_ru = get_all_posts(driver_ru, BASE_URL_RU)
        posts_am = get_all_posts(driver_am, BASE_URL_AM)
        if not posts_ru:
            send_telegram_message(chat_id, "[RU] Посты не найдены на странице.")
        if not posts_am:
            send_telegram_message(chat_id, "[AM] Посты не найдены на странице.")
    except Exception as e:
        send_telegram_message(chat_id, f"Ошибка при получении исходных постов: {e}")
        driver_ru.quit()
        driver_am.quit()
        return

    # Запоминаем базовые (исходные) посты для каждого сайта
    baseline_ru = posts_ru[0] if posts_ru else None
    baseline_am = posts_am[0] if posts_am else None

    if baseline_ru:
        send_telegram_message(chat_id, 
            f"[RU] Исходный пост получен:\nЗаголовок: {baseline_ru[0]}\nДата: {baseline_ru[1]}\nСсылка: {baseline_ru[2]}")
    if baseline_am:
        send_telegram_message(chat_id, 
            f"[AM] Исходный пост получен:\nЗаголовок: {baseline_am[0]}\nДата: {baseline_am[1]}\nСсылка: {baseline_am[2]}")

    # Цикл проверки новостей для обоих сайтов
    while chat_id in active_chats:
        time.sleep(1800)  # Пауза (30 минут) между проверками

        # Проверка для сайта RU
        try:
            driver_ru.refresh()
            posts_ru = get_all_posts(driver_ru, BASE_URL_RU)
            if posts_ru and baseline_ru:
                new_posts_ru = []
                for post in posts_ru:
                    if post[1] == baseline_ru[1]:
                        break
                    new_posts_ru.append(post)
                if new_posts_ru:
                    for post in reversed(new_posts_ru):
                        message = (f"[RU] Новый пост!\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}")
                        send_telegram_message(chat_id, message)
                    baseline_ru = posts_ru[0]
        except Exception as e:
            send_telegram_message(chat_id, f"[RU] Ошибка при проверке новых постов: {e}")

        # Проверка для сайта AM
        try:
            driver_am.refresh()
            posts_am = get_all_posts(driver_am, BASE_URL_AM)
            if posts_am and baseline_am:
                new_posts_am = []
                for post in posts_am:
                    if post[1] == baseline_am[1]:
                        break
                    new_posts_am.append(post)
                if new_posts_am:
                    for post in reversed(new_posts_am):
                        message = (f"[AM] Новый пост!\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}")
                        send_telegram_message(chat_id, message)
                    baseline_am = posts_am[0]
        except Exception as e:
            send_telegram_message(chat_id, f"[AM] Ошибка при проверке новых постов: {e}")

    driver_ru.quit()
    driver_am.quit()

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    if chat_id not in ALLOWED_CHATS:
        return

    if chat_id in active_chats:
        bot.send_message(chat_id, "Бот уже запущен! Мониторинг продолжается...")
        return

    bot.send_message(chat_id, "Бот запущен! Начинаю мониторинг...")
    active_chats[chat_id] = True  # Чат добавляется в активные
    thread = threading.Thread(target=monitor_news, args=(chat_id,), daemon=True)
    thread.start()

# Обработчик команды /stop
@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    active_chats.pop(chat_id, None)  # Удаляем чат из активных

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
