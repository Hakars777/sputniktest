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

# Параметры для сайта AM
URL_AM = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL_AM = "https://am.sputniknews.ru"

# Параметры для сайта ARM
URL_ARM = "https://arm.sputniknews.ru/search/?query=%D4%B5%D4%B1%D5%8F%D5%84"
BASE_URL_ARM = "https://arm.sputniknews.ru"

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

def monitor_news_site(chat_id, url, base_url, site_label):
    """
    Функция мониторинга для одного сайта.
    Сначала определяется исходный (самый новый) пост, а затем раз в час проверяются все посты.
    Если находятся новые посты (до исходного поста), они отправляются в Telegram (с пометкой site_label),
    а исходный пост обновляется.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")  # Отключение GPU-ускорения
    chrome_options.add_argument("--no-sandbox")  # Отключение sandbox (нужен для некоторых серверных окружений)
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-shm-usage")  # Включение использования обычной памяти вместо shared memory
    chrome_options.add_argument("--remote-debugging-port=9222")  # Возможность отладки через порт
    chrome_options.add_argument("--disable-extensions")  # Отключение расширений
    chrome_options.add_argument("--disable-features=VizDisplayCompositor")  # Отключение некоторых функций, которые могут вызвать ошибки
    chrome_options.add_argument("--start-maximized")  # Запуск максимизированного окна (не обязательно для headless)
    chrome_options.add_argument("--no-zygote")  # Еще один флаг, помогающий избежать ошибок в некоторых средах
    chrome_options.add_argument("--single-process")  # Запуск в одном процессе (может помочь на облачных серверах)

    # Создание нового экземпляра драйвера для каждого потока
    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    try:
        posts = get_all_posts(driver, base_url)
        if not posts:
            driver.quit()
            return
        # Запоминаем исходный (самый новый) пост
        baseline_post = posts[0]
        init_message = (
            f"[{site_label}] Исходный пост получен:\n"
            f"Заголовок: {baseline_post[0]}\n"
            f"Дата: {baseline_post[1]}\n"
            f"Ссылка: {baseline_post[2]}"
        )
        send_telegram_message(chat_id, init_message)
    except Exception as e:
        driver.quit()
        return

    while chat_id in active_chats:
        time.sleep(1800)  # Проверяем раз в час
        try:
            driver.refresh()
            posts = get_all_posts(driver, base_url)
            if not posts:
                continue
            # Собираем новые посты, которые располагаются выше baseline_post
            new_posts = []
            for post in posts:
                if post[1] == baseline_post[1]:
                    break
                new_posts.append(post)
            if new_posts:
                # Отправляем новые посты в порядке появления (от старых к новым)
                for post in reversed(new_posts):
                    message = (
                        f"[{site_label}] Новый пост!\n"
                        f"Заголовок: {post[0]}\n"
                        f"Дата: {post[1]}\n"
                        f"Ссылка: {post[2]}"
                    )
                    send_telegram_message(chat_id, message)
                # Обновляем исходный пост на самый новый
                baseline_post = posts[0]
        except Exception as e:
            return

    driver.quit()

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

    # Запуск мониторинга для сайта AM
    thread_am = threading.Thread(
        target=monitor_news_site, 
        args=(chat_id, URL_AM, BASE_URL_AM, "RU"),
        daemon=True
    )
    thread_am.start()

    # Запуск мониторинга для сайта ARM
    thread_arm = threading.Thread(
        target=monitor_news_site, 
        args=(chat_id, URL_ARM, BASE_URL_ARM, "AM"),
        daemon=True
    )
    thread_arm.start()

# Обработчик команды /stop
@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    active_chats.pop(chat_id, None)  # Удаляем чат из списка активных
    bot.send_message(chat_id, "Мониторинг остановлен.")

# Запуск бота
if __name__ == "__main__":
    bot.polling(none_stop=True)
