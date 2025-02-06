import time, threading, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)
ALLOWED_CHATS = {1032063058, 287714154}

# Формат: "Метка": (URL, базовый URL)
SITES = {
    "AM": ("https://arm.sputniknews.ru/search/?query=%D4%B5%D4%B1%D5%8F%D5%84", "https://arm.sputniknews.ru"),
    "RU": ("https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1", "https://am.sputniknews.ru")
}
active_chats = {}

def send_msg(chat_id, msg):
    if chat_id in ALLOWED_CHATS:
        bot.send_message(chat_id, msg)

def get_posts(driver, base):
    WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item")))
    posts = []
    for item in driver.find_elements(By.CSS_SELECTOR, ".list__item"):
        title_el = item.find_element(By.CSS_SELECTOR, ".list__title")
        title = title_el.text.strip()
        href = title_el.get_attribute("href")
        if href and not href.startswith("http"):
            href = base + href
        date = item.find_element(By.CSS_SELECTOR, ".date").text.strip()
        posts.append((title, date, href))
    return posts

def create_driver():
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--log-level=3")
    opts.add_argument("--disable-software-rasterizer")
    return webdriver.Chrome(options=opts)

def monitor_news(chat_id):
    baseline = {}
    try:
        driver = create_driver()  # Драйвер создаётся один раз
    except Exception as e:
        send_msg(chat_id, f"Ошибка создания браузера: {e}")
        return

    # Первоначальная загрузка и отправка исходных постов для каждого сайта
    for label, (url, base) in SITES.items():
        driver.get(url)
        posts = get_posts(driver, base)
        if posts:
            baseline[label] = posts[0]
            send_msg(chat_id, f"[{label}] Исходный пост:\nЗаголовок: {posts[0][0]}\nДата: {posts[0][1]}\nСсылка: {posts[0][2]}")
        else:
            send_msg(chat_id, f"[{label}] Нет постов на странице.")

    # Цикл мониторинга: последовательно проверяем сначала один URL, затем другой, используя один и тот же драйвер
    while chat_id in active_chats:
        for label, (url, base) in SITES.items():
            # Если драйвер уже на нужном URL, обновляем страницу, иначе переходим по новому URL
            if driver.current_url != url:
                driver.get(url)
            else:
                driver.refresh()
            time.sleep(1)
            posts = get_posts(driver, base)
            if posts and posts[0][1] != baseline[label][1]:
                send_msg(chat_id,
                    f"[{label}] Новый пост:\nЗаголовок: {posts[0][0]}\nДата: {posts[0][1]}\nСсылка: {posts[0][2]}")
                baseline[label] = posts[0]
        time.sleep(1800)  # Проверка каждые 30 минут

    driver.quit()

@bot.message_handler(commands=['start'])
def start_cmd(m):
    cid = m.chat.id
    if cid not in ALLOWED_CHATS:
        return
    if cid in active_chats:
        bot.send_message(cid, "Бот уже запущен! Мониторинг продолжается...")
        return
    active_chats[cid] = True
    bot.send_message(cid, "Бот запущен! Начинаю мониторинг...")
    threading.Thread(target=monitor_news, args=(cid,), daemon=True).start()

@bot.message_handler(commands=['stop'])
def stop_cmd(m):
    cid = m.chat.id
    active_chats.pop(cid, None)
    bot.send_message(cid, "Мониторинг остановлен.")

if __name__ == "__main__":
    bot.polling(none_stop=True)