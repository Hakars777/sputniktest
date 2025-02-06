import time, threading, telebot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
ALLOWED_CHATS = {1032063058, 287714154}
URL, BASE_URL = "https://am.sputniknews.ru/search/?query=%D0%95%D0%90%D0%AD%D0%A1", "https://am.sputniknews.ru"
active_chats = {}
bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

def send_msg(cid, msg):
    if cid in ALLOWED_CHATS:
        bot.send_message(cid, msg)

def get_posts(driver):
    WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, ".list__item")))
    posts = []
    for item in driver.find_elements(By.CSS_SELECTOR, ".list__item"):
        title = item.find_element(By.CSS_SELECTOR, ".list__title").text.strip()
        href = item.find_element(By.CSS_SELECTOR, ".list__title").get_attribute("href")
        if href and not href.startswith("http"):
            href = BASE_URL + href
        date = item.find_element(By.CSS_SELECTOR, ".date").text.strip()
        posts.append((title, date, href))
    return posts

def monitor_news(cid):
    if cid not in ALLOWED_CHATS:
        return
    opts = Options()
    opts.add_argument("--headless")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=opts)
    driver.get(URL)
    try:
        posts = get_posts(driver)
        if not posts:
            driver.quit()
            active_chats.pop(cid, None)
            return
        baseline = posts[0]
        send_msg(cid, f"Исходный пост:\nЗаголовок: {baseline[0]}\nДата: {baseline[1]}\nСсылка: {baseline[2]}")
    except Exception:
        driver.quit()
        active_chats.pop(cid, None)
        return
    while cid in active_chats:
        time.sleep(1800)
        try:
            driver.refresh()
            posts = get_posts(driver)
            if not posts:
                continue
            new_posts = []
            for post in posts:
                if post[1] == baseline[1]:
                    break
                new_posts.append(post)
            if new_posts:
                for post in reversed(new_posts):
                    send_msg(cid, f"Новый пост:\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}")
                baseline = posts[0]
        except Exception:
            pass
    driver.quit()
    active_chats.pop(cid, None)

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
