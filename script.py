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
active_chats = {}

# Параметры сайтов в виде словаря
SITES = {
    "RU": {"url": "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1", "base": "https://am.sputniknews.ru"},
    "AM": {"url": "https://arm.sputniknews.ru/search/?query=%D4%B5%D4%B1%D5%8F%D5%84", "base": "https://arm.sputniknews.ru"}
}

def send_telegram_message(chat_id, message):
    if chat_id in ALLOWED_CHATS:
        bot.send_message(chat_id, message)

def get_all_posts(driver, base_url):
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item")))
    posts = []
    for item in driver.find_elements(By.CSS_SELECTOR, ".list__item"):
        title_el = item.find_element(By.CSS_SELECTOR, ".list__title")
        title = title_el.text.strip()
        href = title_el.get_attribute("href")
        if href and not href.startswith("http"):
            href = base_url + href
        date = item.find_element(By.CSS_SELECTOR, ".date").text.strip()
        posts.append((title, date, href))
    return posts

def init_site(driver, label, chat_id):
    url, base = SITES[label]["url"], SITES[label]["base"]
    driver.get(url)
    posts = get_all_posts(driver, base)
    if posts:
        baseline = posts[0]
        send_telegram_message(chat_id,
            f"[{label}] Исходный пост:\nЗаголовок: {baseline[0]}\nДата: {baseline[1]}\nСсылка: {baseline[2]}")
        return baseline
    return None

def check_site(driver, label, baseline, chat_id):
    url, base = SITES[label]["url"], SITES[label]["base"]
    driver.get(url)
    posts = get_all_posts(driver, base)
    if posts:
        new_posts = []
        for post in posts:
            if post[1] == baseline[1]:
                break
            new_posts.append(post)
        if new_posts:
            for post in reversed(new_posts):
                send_telegram_message(chat_id,
                    f"[{label}] Новый пост:\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}")
            baseline = posts[0]
    return baseline

def monitor_news_sites(chat_id):
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--log-level=3")
    chrome_options.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=chrome_options)

    baseline_ru = init_site(driver, "RU", chat_id)
    if not baseline_ru:
        driver.quit()
        return
    baseline_am = init_site(driver, "AM", chat_id)
    if not baseline_am:
        driver.quit()
        return

    while chat_id in active_chats:
        try:
            baseline_ru = check_site(driver, "RU", baseline_ru, chat_id)
        except Exception:
            pass
        try:
            baseline_am = check_site(driver, "AM", baseline_am, chat_id)
        except Exception:
            pass
        time.sleep(1800)  # Задержка между итерациями

    driver.quit()

@bot.message_handler(commands=['start'])
def start_command(message):
    chat_id = message.chat.id
    if chat_id not in ALLOWED_CHATS:
        return
    if chat_id in active_chats:
        bot.send_message(chat_id, "Мониторинг уже запущен!")
        return
    active_chats[chat_id] = True
    bot.send_message(chat_id, "Начинаю мониторинг...")
    threading.Thread(target=monitor_news_sites, args=(chat_id,), daemon=True).start()

@bot.message_handler(commands=['stop'])
def stop_command(message):
    chat_id = message.chat.id
    active_chats.pop(chat_id, None)
    bot.send_message(chat_id, "Мониторинг остановлен.")

if __name__ == "__main__":
    bot.polling(none_stop=True)