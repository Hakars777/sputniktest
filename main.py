import time, threading, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
ALLOWED_CHATS = {1032063058, 1205943698}
URL = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1"
BASE_URL = "https://am.sputniknews.ru"
active_chats = {}
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def send_msg(cid, msg):
    if cid in ALLOWED_CHATS:
        bot.send_message(cid, msg)

def get_first_post(driver):
    WebDriverWait(driver, 30).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item"))
    )
    item = driver.find_element(By.CSS_SELECTOR, ".list__item")
    title = item.find_element(By.CSS_SELECTOR, ".list__title").text.strip()
    href = item.find_element(By.CSS_SELECTOR, ".list__title").get_attribute("href")
    if href and not href.startswith("http"):
        href = BASE_URL + href
    date = item.find_element(By.CSS_SELECTOR, ".date").text.strip()
    return (title, date, href)

def get_new_posts(driver, baseline, limit=10):

    items = driver.find_elements(By.CSS_SELECTOR, ".list__item")[:limit]
    new_posts = []
    for item in items:
        title = item.find_element(By.CSS_SELECTOR, ".list__title").text.strip()
        href = item.find_element(By.CSS_SELECTOR, ".list__title").get_attribute("href")
        if href and not href.startswith("http"):
            href = BASE_URL + href
        date = item.find_element(By.CSS_SELECTOR, ".date").text.strip()
        post = (title, date, href)
        if post[2] == baseline[2]:
            break
        new_posts.append(post)
    return new_posts

def monitor_news(cid):
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=opts)
    driver.get(URL)
    try:
        baseline = get_first_post(driver)
        send_msg(cid, f"Исходный пост:\nЗаголовок: {baseline[0]}\nДата: {baseline[1]}\nСсылка: {baseline[2]}")
    except Exception:
        driver.quit()
        active_chats.pop(cid, None)
        return

    while cid in active_chats:
        time.sleep(1800)  # Интервал проверки – 30 минут
        try:
            driver.refresh()
            new_posts = get_new_posts(driver, baseline, limit=10)
            if new_posts:
                # Отправляем новые посты от старых к новым
                for post in reversed(new_posts):
                    send_msg(cid, f"Новый пост:\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}")
                # Обновляем baseline до первого поста, извлеченного после refresh
                baseline = get_first_post(driver)
        except Exception:
            pass
    driver.quit()
    active_chats.pop(cid, None)

@bot.message_handler(commands=['start'])
def start(m):
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
def stop(m):
    cid = m.chat.id
    active_chats.pop(cid, None)
    bot.send_message(cid, "Мониторинг остановлен.")

if __name__ == "__main__":
    bot.polling(none_stop=True)