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

# Разрешённые чаты
ALLOWED_CHATS = {1032063058, 287714154}

# URL-адреса сайтов
SITES = {
    "RU": ("https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1", "https://am.sputniknews.ru"),
    "AM": ("https://arm.sputniknews.ru/search/?query=%D4%B5%D4%B1%D5%8F%D5%84", "https://arm.sputniknews.ru"),
}

# Словарь активных чатов
active_chats = {}

def send_telegram_message(chat_id, message):
    """Отправляет сообщение в Telegram только для разрешённых chat_id."""
    if chat_id in ALLOWED_CHATS:
        bot.send_message(chat_id, message)

def get_all_posts(driver, base_url):
    """Получает список всех постов со страницы."""
    WebDriverWait(driver, 20).until(
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
    """Создаёт экземпляр Chrome с параметрами, пригодными для Docker и облачных серверов."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")                   # Фоновый режим
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")        # Для предотвращения "tab crashed"
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-software-rasterizer")
    return webdriver.Chrome(options=chrome_options)

def check_site(driver, site_label, url, base_url, baseline):
    """
    Переходит по URL, получает посты и сравнивает с предыдущим baseline.
    Возвращает новый baseline и сообщение (если найден новый пост).
    """
    try:
        driver.get(url)
        posts = get_all_posts(driver, base_url)
        if posts:
            new_baseline = posts[0]
            if baseline and new_baseline[1] != baseline[1]:  # Если дата поста изменилась
                message = (f"[{site_label}] Новый пост!\n"
                           f"Заголовок: {new_baseline[0]}\n"
                           f"Дата: {new_baseline[1]}\n"
                           f"Ссылка: {new_baseline[2]}")
                return new_baseline, message
            return new_baseline, None
    except Exception as e:
        return

def monitor_news(chat_id):
    """Основная функция мониторинга: сначала отправляются исходные посты, затем — периодические проверки."""
    baseline_posts = {site: None for site in SITES}

    try:
        driver = create_driver()  # Инициализация драйвера
    except Exception as e:
        return

    # Получаем и отправляем исходные посты
    for site, (url, base_url) in SITES.items():
        try:
            driver.get(url)
            posts = get_all_posts(driver, base_url)
            if posts:
                baseline_posts[site] = posts[0]
                init_message = (f"[{site}] Исходный пост:\n"
                                f"Заголовок: {posts[0][0]}\n"
                                f"Дата: {posts[0][1]}\n"
                                f"Ссылка: {posts[0][2]}")
                send_telegram_message(chat_id, init_message)
        except Exception as e:
            return
    driver.quit()  # Закрытие драйвера после первичной проверки

    # Основной цикл мониторинга
    while chat_id in active_chats:
        try:
            driver = create_driver()  # Новый драйвер для следующего цикла мониторинга
            for site, (url, base_url) in SITES.items():
                new_baseline, msg = check_site(driver, site, url, base_url, baseline_posts[site])
                if msg:
                    send_telegram_message(chat_id, msg)
                baseline_posts[site] = new_baseline
            driver.quit()  # Закрытие драйвера после каждой итерации
        except Exception as e:
            return
        time.sleep(1800)  # Интервал проверки – 30 минут

@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    if chat_id not in ALLOWED_CHATS:
        return
    if chat_id in active_chats:
        bot.send_message(chat_id, "Бот уже запущен! Мониторинг продолжается...")
        return
    bot.send_message(chat_id, "Бот запущен! Начинаю мониторинг...")
    active_chats[chat_id] = True
    thread = threading.Thread(target=monitor_news, args=(chat_id,), daemon=True)
    thread.start()

@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    active_chats.pop(chat_id, None)
    bot.send_message(chat_id, "Мониторинг остановлен.")

if __name__ == "__main__":
    bot.polling(none_stop=True)