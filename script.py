import time
import asyncio
import telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from threading import Thread

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

# Состояние активных чатов
active_chats = {}

async def send_telegram_message(chat_id, message):
    """Отправляет сообщение в Telegram только для разрешённых chat_id."""
    if chat_id in ALLOWED_CHATS:
        await bot.send_message(chat_id, message)

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

async def monitor_news_site(chat_id, url, base_url, site_label):
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

    while chat_id in active_chats:
        await asyncio.sleep(1800)  # Проверяем раз в час
        try:
            driver.refresh()
            posts = await get_all_posts(driver, base_url)
            if not posts:
                continue
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
                    await send_telegram_message(chat_id, message)
                baseline_post = posts[0]
        except Exception as e:
            return

    driver.quit()

async def start_monitoring(chat_id):
    """Запуск мониторинга для двух сайтов одновременно с использованием asyncio."""
    tasks = [
        monitor_news_site(chat_id, URL_AM, BASE_URL_AM, "RU"),
        monitor_news_site(chat_id, URL_ARM, BASE_URL_ARM, "AM")
    ]
    await asyncio.gather(*tasks)

def start_bot_polling():
    """Функция для запуска бота и обработки команд с использованием asyncio."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Начать polling
    bot.polling(none_stop=True, interval=0)

@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    if chat_id in ALLOWED_CHATS:
        if chat_id in active_chats:
            bot.send_message(chat_id, "Бот уже запущен! Мониторинг продолжается...")
        else:
            bot.send_message(chat_id, "Бот запущен! Начинаю мониторинг...")
            active_chats[chat_id] = True  # Добавляем чат в активные чаты
            # Запуск мониторинга в отдельном потоке
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.create_task(start_monitoring(chat_id))
            loop.run_forever()

@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    active_chats.pop(chat_id, None)  # Удаляем чат из списка активных
    bot.send_message(chat_id, "Мониторинг остановлен.")

if __name__ == "__main__":
    # Запуск бота в отдельном потоке
    thread = Thread(target=start_bot_polling)
    thread.start()
