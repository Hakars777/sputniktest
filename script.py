import asyncio
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread, Event

# Данные для Telegram-бота
TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Разрешённые чаты
ALLOWED_CHATS = {1032063058, 287714154}

# Параметры для сайтов
URL_AM = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL_AM = "https://am.sputniknews.ru"
URL_ARM = "https://arm.sputniknews.ru/search/?query=%D4%B5%D4%B1%D5%8F%D5%84"
BASE_URL_ARM = "https://arm.sputniknews.ru"

# Словарь для хранения запущенных потоков мониторинга по chat_id
monitor_threads = {}

# Отправка сообщения в Telegram
async def send_telegram_message(chat_id, message):
    """Отправляет сообщение в Telegram только для разрешённых chat_id."""
    if chat_id in ALLOWED_CHATS:
        await bot.send_message(chat_id, message)

# Получение всех постов на странице
async def get_all_posts(driver, base_url):
    """Получает список всех постов на странице."""
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

# Функция мониторинга для одного сайта
async def monitor_news_site(chat_id, url, base_url, site_label, stop_event: Event):
    """Функция мониторинга для одного сайта."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-software-rasterizer")
    chrome_options.add_argument("--disable-dev-shm-usage")

    driver = webdriver.Chrome(options=chrome_options)
    driver.get(url)

    try:
        posts = await get_all_posts(driver, base_url)
        if not posts:
            driver.quit()
            return
        baseline_post = posts[0]
        init_message = (
            f"[{site_label}] Исходный пост получен:\n"
            f"Заголовок: {baseline_post[0]}\n"
            f"Дата: {baseline_post[1]}\n"
            f"Ссылка: {baseline_post[2]}"
        )
        await send_telegram_message(chat_id, init_message)
    except Exception as e:
        driver.quit()
        return

    try:
        while not stop_event.is_set():
            await asyncio.sleep(1800)  # Проверяем раз в 30 минут
            try:
                driver.refresh()
                posts = await get_all_posts(driver, base_url)
                if not posts:
                    continue
                new_posts = []
                # Собираем новые посты до тех пор, пока не встретим базовый
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
                        await send_telegram_message(chat_id, message)
                    baseline_post = posts[0]
            except Exception as e:
                # При ошибке завершаем мониторинг для данного сайта
                break
    finally:
        driver.quit()

# Запуск мониторинга для двух сайтов одновременно с использованием asyncio
async def start_monitoring(chat_id, stop_event: Event):
    """Запуск мониторинга для двух сайтов одновременно."""
    tasks = [
        monitor_news_site(chat_id, URL_AM, BASE_URL_AM, "RU", stop_event),
        monitor_news_site(chat_id, URL_ARM, BASE_URL_ARM, "AM", stop_event)
    ]
    await asyncio.gather(*tasks)

# Обработчик команды /start
@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    if chat_id not in ALLOWED_CHATS:
        return

    if chat_id in monitor_threads:
        bot.send_message(chat_id, "Бот уже запущен! Мониторинг продолжается...")
    else:
        bot.send_message(chat_id, "Бот запущен! Начинаю мониторинг...")
        stop_event = Event()
        thread = Thread(target=lambda: asyncio.run(start_monitoring(chat_id, stop_event)))
        thread.start()
        monitor_threads[chat_id] = (thread, stop_event)

# Обработчик команды /stop
@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    if chat_id in monitor_threads:
        thread, stop_event = monitor_threads.pop(chat_id)
        stop_event.set()
        bot.send_message(chat_id, "Мониторинг остановлен.")
    else:
        bot.send_message(chat_id, "Мониторинг не запущен.")

if __name__ == "__main__":
    bot.polling(none_stop=True)
