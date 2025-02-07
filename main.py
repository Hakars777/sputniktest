import time
import threading
import telebot
from telebot import types
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote

# Замените токен на свой
TELEGRAM_BOT_TOKEN = "8054009340:AAFSdbb7C7xaQjaFOVgePNXCLFxdnNxgeYE"
ALLOWED_CHATS = {1032063058, 287714154, 1205943698}

# Определяем источники с дефолтными настройками
endpoints = [
    {
        "name": "AM",
        "base_url": "https://arm.sputniknews.ru",
        "default_keywords": "ԵԱՏՄ",  # дефолтное ключевое слово для AM
        "recaptcha": "03AFcWeA50wqLUqgUdVF7mreRYaYg7n8FbaTB0N11E1I12gs2CV_Z_uum1_h76sycLPRAV1LHiuqjxnWpVTObeOPbFGaaOG6lHORUzKUG_UbHTC9m2M4lA6OXsUY_sHiMuM4hyFm2rXetrZcEBNJT7Ig2LCuD2W6KmSDvivcmD7kDdp-AkxXavoSLfnhaUNhi7sMXc8Pp2wM0IRwg81M8jmeTBOsVsTnRgzcFzQwDV1CX741IKIlC8nBqc4UT5QxRg-9Q_rzCCXTQa-6HnJCtAmwNbqGQzK4swPKu9i9qr9Afcz4vBlM83T4D6_5K_1Fr-UwZ9O6SzHuK9E5KM_TNL7QhlF_tuybT-XPjLgmOTxECe_8SP68VvVqwynUg-lplrwa5vj0Ztgk7L7YCWCDUQPz8_xq2rpITPbeZNC4LEx7-xR-1GAJ0Lbf1TKwdfXWUA0SgiGQ1zkV3pXM6x3JSImcOLND6V914Bptf3JELJTqSyfNkFKqJFj4wpZtXyDEpwV2JqqdSz9JhiIjuolM13CY3eFcIz2ZKMZsxyBlFlcgEC0abfYY4-b_2W7vWBxhuG7w7M6Q22F3lEj2VwX_KwOdYUEhxZrl9aomjebTF0u4r8i8Q19IzOp1KCgNyl8l5EnRCIVXnVOBUOL4IJfvgB8Psht6_DZxm78MDv-fz9W6ZtgZLZFrBKld5oYwzMDTnm0N9NTz79osm7T3-eAM7JlgMce9N6wSBNOZQu8LdXxfw_bQQzDSPw13HUn4D7nvHiX9R8u1llzO7GQVxl9mq83kbFhKuQYQJvwPAaObbZmSRDJVC5kiINvFZmUxSHcT5hcrd_KulvvegI-Nf65MIQ5jQi7mPALJK4hzbppxIuyTCKigFsaYd2JEVHnemqam6cwTVrS2tGMj6d_Zo5L3r8TRdlkQXFXeEEkg"
    },
    {
        "name": "RU",
        "base_url": "https://am.sputniknews.ru",
        "default_keywords": "ЕАЭС",  # дефолтное ключевое слово для RU
        "recaptcha": "03AFcWeA4uIWjSWvJrDTjdBrYXEDnN4j7CqhUFODOGYNoHOI-srPs6Uw4YJrd2N4sEDyIkQnjF7auWUWdzi-6W7fndD90rwd5blIp-WU0CgpyixyaLcaO9XomeYzNy6b43vSwRsjq9LUVufrGsRFNM2n162r8pmLID7NilUUgeF_OFNnJ8xZ7huq4I7f3uZqsR7qJXRFAWG5rVfRDZPpQVU59n414ALMos9K2j1QdtC-Hp9Cf-RMJw7128cZkvZudKb-GdyQYtviquQGTuSVeGq8IpixoACvFTMUSnUY6jyfPzOVW25EpYogPEuJHc7J1zPQya0YHVEMaseU5-ZA3ueRhq1U9862rPIZ1bRS_DUuj-zxFAW99HLxGzeh2Gvfbhf3HqkUVkxhcuOz4FLpqb3JRfcK2Ak9FI6N9VTDDRqf8VN-mi591wYh0-fRvUS4PyCwEhr05vHgPmU1eyBmgYdmt_7G6i64tYlI6C9Z-0pdwd2UxSp64yePqJUJ005wRisnSPJD9UUB1KahR7kRvyEmYoHL4F5AVuhk7d7JquitmLWAxnTrS9h9mrwZ0CdtvyX0xdEEoAmLil3UV2NgUsiAN5w_1rOr0jdgiCTTYSsXHrVsrC4HxicGbcssdFViDPYXZU1hUUVuo2JatWQgvp4sPOO3583lpmOjDM4RXTzUoFlD7GxYX-3xXBHylH1c_QsFe_bLKLkpwNunR5RVn5hLXXw90jGzSdjW4rzxhUVXzZIJ7tMbchP111Y6QwVqF0D6RnNYgfOpyU-xmaiCc6UQaTJQUMTZHBahah_3_Vt7VMXHE5USvVzm8GtheMz2aTFwrxfVbdMI6g66_Rd2iUVxKRluoWespedjG0WuC2-VBfhx2adye8jfLILKTLubLgvsg_vtDCoCIYcx1wajA5FzWh8PiAGmunAJsJdtPsSWLJCoveDCTSsO4"
    }
]

# Настройки для каждого чата: { chat_id: { source: {"keywords": [список ключевых слов]}, ... } }
chat_settings = {}

# Активные чаты для мониторинга: { chat_id: True }
active_chats = {}

bot = telebot.TeleBot(TELEGRAM_BOT_TOKEN)

# Функция отправки сообщений
def send_msg(cid, msg):
    if cid in ALLOWED_CHATS:
        bot.send_message(cid, msg)

# Функция формирования URL запроса по ключевому слову
def build_api_url(endpoint, keyword):
    encoded = quote(keyword)
    return f"{endpoint['base_url']}/services/search/getmore/?query={encoded}&tags_limit=20&tags=0&g-recaptcha-response={endpoint['recaptcha']}"

# Функция получения HTML-ответа
def fetch_news(api_url, base_url):
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/133.0.0.0 Safari/537.36"),
        "Referer": base_url
    }
    response = requests.get(api_url, headers=headers)
    response.raise_for_status()
    return response.text

# Функция парсинга HTML и извлечения новостей
def parse_news(html, base_url):
    soup = BeautifulSoup(html, "html.parser")
    items = soup.select(".list__item")
    posts = []
    for item in items:
        title_elem = item.select_one(".list__title")
        if not title_elem:
            continue
        title = title_elem.get_text(strip=True)
        href = title_elem.get("href", "")
        if href and not href.startswith("http"):
            href = base_url + href
        date_elem = item.select_one(".date")
        if not date_elem:
            continue
        date = date_elem.get_text(strip=True)
        posts.append((title, date, href))
    return posts

# Функция мониторинга для каждого источника
def monitor_endpoint(cid, endpoint):
    base_url = endpoint["base_url"]
    source_name = endpoint.get("name", base_url)
    settings = {}
    if cid in chat_settings and source_name in chat_settings[cid]:
        settings = chat_settings[cid][source_name]
    if isinstance(settings.get("keywords"), list):
        keywords_list = settings.get("keywords")
    else:
        keywords_str = settings.get("keywords", endpoint["default_keywords"])
        keywords_list = keywords_str.split()
    interval = 1800

    baseline_dict = {}
    try:
        for kw in keywords_list:
            api_url = build_api_url(endpoint, kw)
            html = fetch_news(api_url, base_url)
            posts = parse_news(html, base_url)
            if not posts:
                raise Exception(f"Не найдены новости для ключевого слова '{kw}'.")
            baseline_dict[kw] = posts[0]
            send_msg(cid, f"[Источник: {source_name}]\nИсходный пост для ключевого слова '{kw}':\nЗаголовок: {posts[0][0]}\nДата: {posts[0][1]}\nСсылка: {posts[0][2]}")
    except Exception as e:
        send_msg(cid, f"[Источник: {source_name}]\nОшибка при инициализации: {e}")
        return

    while cid in active_chats:
        time.sleep(interval)
        try:
            for kw in keywords_list:
                api_url = build_api_url(endpoint, kw)
                html = fetch_news(api_url, base_url)
                posts = parse_news(html, base_url)
                if not posts:
                    continue
                new_posts = []
                for post in posts:
                    if post[2] == baseline_dict[kw][2]:
                        break
                    new_posts.append(post)
                if new_posts:
                    for post in reversed(new_posts):
                        send_msg(
                            cid,
                            f"[Источник: {source_name}]\nНовый пост для ключевого слова '{kw}':\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}"
                        )
                    baseline_dict[kw] = posts[0]
        except Exception as e:
            print(f"[Источник: {source_name}] Ошибка мониторинга: {e}")

# Команда /start – запускает мониторинг и инициализирует настройки с дефолтными ключевыми словами
@bot.message_handler(commands=['start'])
def start_handler(m):
    cid = m.chat.id
    if cid not in ALLOWED_CHATS:
        return
    if cid in active_chats:
        bot.send_message(cid, "Бот уже запущен! Мониторинг продолжается...")
        return
    active_chats[cid] = True
    if cid not in chat_settings:
        chat_settings[cid] = {}
        for ep in endpoints:
            chat_settings[cid][ep["name"]] = {"keywords": ep["default_keywords"].split()}
    bot.send_message(cid,
        "Бот запущен! Мониторинг по обоим источникам начат.\n"
        "Команды:\n"
        "/addkeywords – добавить новое ключевое слово для источника\n"
        "/cleankeywords – сбросить все ключевые слова\n"
    )
    for ep in endpoints:
        threading.Thread(target=monitor_endpoint, args=(cid, ep), daemon=True).start()

# Команда /stop – останавливает мониторинг
@bot.message_handler(commands=['stop'])
def stop_handler(m):
    cid = m.chat.id
    if cid in active_chats:
        active_chats.pop(cid, None)
        bot.send_message(cid, "Мониторинг остановлен.")

# Команда /addkeywords – интерактивно добавляет одно новое ключевое слово для выбранного источника.
@bot.message_handler(commands=['addkeywords'])
def add_keywords(m):
    cid = m.chat.id
    # Создадим клавиатуру для выбора источника
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for ep in endpoints:
        markup.add(types.KeyboardButton(ep["name"]))
    bot.send_message(cid, "Выберите источник для добавления нового ключевого слова:", reply_markup=markup)
    bot.register_next_step_handler(m, add_keywords_source)

def add_keywords_source(m):
    cid = m.chat.id
    source = m.text.strip()
    available = [ep["name"] for ep in endpoints]
    if source not in available:
        bot.send_message(cid, f"Источник '{source}' не найден. Доступные источники: {', '.join(available)}.")
        return
    if cid not in chat_settings:
        chat_settings[cid] = {}
    if source not in chat_settings[cid]:
        chat_settings[cid][source] = {"keywords": []}
    bot.send_message(cid, f"Введите новое ключевое слово для источника '{source}':")
    bot.register_next_step_handler(m, add_keywords_keyword, source)

def add_keywords_keyword(m, source):
    cid = m.chat.id
    new_kw = m.text.strip()
    # Добавляем новое ключевое слово (предполагается, что оно не пустое)
    chat_settings[cid][source]["keywords"].append(new_kw)
    current_list = chat_settings[cid][source]["keywords"]
    bot.send_message(cid, f"Ключевое слово '{new_kw}' добавлено для источника '{source}'.\nТекущий список: {', '.join(current_list)}")
    # Диалог завершается после одного добавления; для добавления другого слова вызовите команду /addkeywords снова.

# Команда /cleankeywords – интерактивно сбрасывает список ключевых слов для выбранного источника к дефолтным.
@bot.message_handler(commands=['cleankeywords'])
def clean_keywords(m):
    cid = m.chat.id
    markup = types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for ep in endpoints:
        markup.add(types.KeyboardButton(ep["name"]))
    bot.send_message(cid, "Выберите источник для сброса ключевых слов:", reply_markup=markup)
    bot.register_next_step_handler(m, clean_keywords_source)

def clean_keywords_source(m):
    cid = m.chat.id
    source = m.text.strip()
    available = [ep["name"] for ep in endpoints]
    if source not in available:
        bot.send_message(cid, f"Источник '{source}' не найден. Доступные источники: {', '.join(available)}.")
        return
    default_kw = None
    for ep in endpoints:
        if ep["name"] == source:
            default_kw = ep["default_keywords"].split()
            break
    if default_kw is None:
        bot.send_message(cid, f"Ключевые слова для источника '{source}' не найдены.")
        return
    if cid not in chat_settings:
        chat_settings[cid] = {}
    chat_settings[cid][source] = {"keywords": default_kw}
    bot.send_message(cid, f"Ключевые слова для источника '{source}' сброшены\nТекущий список: {', '.join(default_kw)}")

if __name__ == "__main__":
    bot.polling(none_stop=True)