import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command, StateFilter
from aiogram.fsm.storage.memory import MemoryStorage
import requests
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from bs4 import BeautifulSoup
from urllib.parse import quote

# Замените токен на свой
TELEGRAM_BOT_TOKEN = "7816691902:AAGDGRYn9pILVyhlCTrE81HIaOITeHjXa1Y"
ALLOWED_CHATS = {1032063058, 1205943698, 287714154}

JSONBIN_API_KEY = "$2a$10$1tHNI4hiRsIHPLoD/REKHe53YIXpHRV59WoLcOM.MLfgZ3qZJtQZa"
JSONBIN_BIN_ID = "67a7c1ceacd3cb34a8dac9dd 	"
JSONBIN_BASE_URL = "https://api.jsonbin.io/v3/b"
HEADERS = {
    "Content-Type": "application/json",
    "X-Master-Key": JSONBIN_API_KEY,
}


def load_chat_settings():
    global chat_settings
    url = f"{JSONBIN_BASE_URL}/{JSONBIN_BIN_ID}/latest"
    try:
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            data = response.json()["record"]
            # Если ключи сохранены как строки, приводим их к int
            chat_settings = {int(k): v for k, v in data.items()} 
        else:
            chat_settings = {}
    except Exception as e:
        chat_settings = {}

def save_chat_settings():

    url = f"{JSONBIN_BASE_URL}/{JSONBIN_BIN_ID}"
    try:
        requests.put(url, headers=HEADERS, json=chat_settings)
    except Exception as e:
        return
    
# Определяем источники с дефолтными настройками
endpoints = [
    {
        "name": "AM",
        "base_url": "https://arm.sputniknews.ru",
        "default_keywords": "ԵԱՏՄ",  
        "recaptcha": "03AFcWeA50wqLUqgUdVF7mreRYaYg7n8FbaTB0N11E1I12gs2CV_Z_uum1_h76sycLPRAV1LHiuqjxnWpVTObeOPbFGaaOG6lHORUzKUG_UbHTC9m2M4lA6OXsUY_sHiMuM4hyFm2rXetrZcEBNJT7Ig2LCuD2W6KmSDvivcmD7kDdp-AkxXavoSLfnhaUNhi7sMXc8Pp2wM0IRwg81M8jmeTBOsVsTnRgzcFzQwDV1CX741IKIlC8nBqc4UT5QxRg-9Q_rzCCXTQa-6HnJCtAmwNbqGQzK4swPKu9i9qr9Afcz4vBlM83T4D6_5K_1Fr-UwZ9O6SzHuK9E5KM_TNL7QhlF_tuybT-XPjLgmOTxECe_8SP68VvVqwynUg-lplrwa5vj0Ztgk7L7YCWCDUQPz8_xq2rpITPbeZNC4LEx7-xR-1GAJ0Lbf1TKwdfXWUA0SgiGQ1zkV3pXM6x3JSImcOLND6V914Bptf3JELJTqSyfNkFKqJFj4wpZtXyDEpwV2JqqdSz9JhiIjuolM13CY3eFcIz2ZKMZsxyBlFlcgEC0abfYY4-b_2W7vWBxhuG7w7M6Q22F3lEj2VwX_KwOdYUEhxZrl9aomjebTF0u4r8i8Q19IzOp1KCgNyl8l5EnRCIVXnVOBUOL4IJfvgB8Psht6_DZxm78MDv-fz9W6ZtgZLZFrBKld5oYwzMDTnm0N9NTz79osm7T3-eAM7JlgMce9N6wSBNOZQu8LdXxfw_bQQzDSPw13HUn4D7nvHiX9R8u1llzO7GQVxl9mq83kbFhKuQYQJvwPAaObbZmSRDJVC5kiINvFZmUxSHcT5hcrd_KulvvegI-Nf65MIQ5jQi7mPALJK4hzbppxIuyTCKigFsaYd2JEVHnemqam6cwTVrS2tGMj6d_Zo5L3r8TRdlkQXFXeEEkg"
    },
    {
        "name": "RU",
        "base_url": "https://am.sputniknews.ru",
        "default_keywords": "ЕАЭС",  
        "recaptcha": "03AFcWeA4uIWjSWvJrDTjdBrYXEDnN4j7CqhUFODOGYNoHOI-srPs6Uw4YJrd2N4sEDyIkQnjF7auWUWdzi-6W7fndD90rwd5blIp-WU0CgpyixyaLcaO9XomeYzNy6b43vSwRsjq9LUVufrGsRFNM2n162r8pmLID7NilUUgeF_OFNnJ8xZ7huq4I7f3uZqsR7qJXRFAWG5rVfRDZPpQVU59n414ALMos9K2j1QdtC-Hp9Cf-RMJw7128cZkvZudKb-GdyQYtviquQGTuSVeGq8IpixoACvFTMUSnUY6jyfPzOVW25EpYogPEuJHc7J1zPQya0YHVEMaseU5-ZA3ueRhq1U9862rPIZ1bRS_DUuj-zxFAW99HLxGzeh2Gvfbhf3HqkUVkxhcuOz4FLpqb3JRfcK2Ak9FI6N9VTDDRqf8VN-mi591wYh0-fRvUS4PyCwEhr05vHgPmU1eyBmgYdmt_7G6i64tYlI6C9Z-0pdwd2UxSp64yePqJUJ005wRisnSPJD9UUB1KahR7kRvyEmYoHL4F5AVuhk7d7JquitmLWAxnTrS9h9mrwZ0CdtvyX0xdEEoAmLil3UV2NgUsiAN5w_1rOr0jdgiCTTYSsXHrVsrC4HxicGbcssdFViDPYXZU1hUUVuo2JatWQgvp4sPOO3583lpmOjDM4RXTzUoFlD7GxYX-3xXBHylH1c_QsFe_bLKLkpwNunR5RVn5hLXXw90jGzSdjW4rzxhUVXzZIJ7tMbchP111Y6QwVqF0D6RnNYgfOpyU-xmaiCc6UQaTJQUMTZHBahah_3_Vt7VMXHE5USvVzm8GtheMz2aTFwrxfVbdMI6g66_Rd2iUVxKRluoWespedjG0WuC2-VBfhx2adye8jfLILKTLubLgvsg_vtDCoCIYcx1wajA5FzWh8PiAGmunAJsJdtPsSWLJCoveDCTSsO4"
    }
]

# Настройки для каждого чата: { chat_id: { source: {"keywords": [список ключевых слов]}, ... } }
chat_settings = {}

# Активные задачи мониторинга: { chat_id: { source: asyncio.Task, ... } }
active_chats = {}

# Глобальная сессия для HTTP-запросов
http_session = None

# Инициализация бота и диспетчера с хранилищем состояний
bot = Bot(token=TELEGRAM_BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# ------------------------- Вспомогательные функции -------------------------

def build_api_url(endpoint, keyword):
    encoded = quote(keyword)
    return f"{endpoint['base_url']}/services/search/getmore/?query={encoded}&tags_limit=20&tags=0&g-recaptcha-response={endpoint['recaptcha']}"

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

async def fetch_news(api_url, base_url):
    headers = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/133.0.0.0 Safari/537.36"),
        "Referer": base_url
    }
    async with http_session.get(api_url, headers=headers) as response:
        response.raise_for_status()
        return await response.text()

async def send_msg(cid, msg):
    if cid in ALLOWED_CHATS:
        await bot.send_message(cid, msg)

# Функция для перезапуска мониторинга для конкретного источника
async def restart_monitoring(cid, source):
    # Находим данные endpoint по имени источника
    for ep in endpoints:
        if ep["name"] == source:
            # Если мониторинг для этого источника уже запущен – отменяем его
            if cid in active_chats and source in active_chats[cid]:
                old_task = active_chats[cid][source]
                old_task.cancel()
                try:
                    await old_task
                except asyncio.CancelledError:
                    pass
            # Запускаем новый мониторинг для источника
            task = asyncio.create_task(monitor_endpoint(cid, ep))
            if cid not in active_chats:
                active_chats[cid] = {}
            active_chats[cid][source] = task
            break

# ------------------------- Мониторинг источников -------------------------

async def monitor_endpoint(cid, endpoint):
    base_url = endpoint["base_url"]
    source_name = endpoint.get("name", base_url)
    # Получаем настройки для данного источника
    settings = {}
    if cid in chat_settings and source_name in chat_settings[cid]:
        settings = chat_settings[cid][source_name]
    if isinstance(settings.get("keywords"), list):
        keywords_list = settings.get("keywords")
    else:
        keywords_str = settings.get("keywords", endpoint["default_keywords"])
        keywords_list = keywords_str.split()
    interval = 1800  # интервал в секундах

    baseline_dict = {}
    try:
        for kw in keywords_list:
            api_url = build_api_url(endpoint, kw)
            html = await fetch_news(api_url, base_url)
            posts = parse_news(html, base_url)
            if not posts:
                raise Exception(f"Не найдены новости для ключевого слова '{kw}'.")
            baseline_dict[kw] = posts[0]
            await send_msg(
                cid,
                f"[Источник: {source_name}]\nИсходный пост для ключевого слова '{kw}':\nЗаголовок: {posts[0][0]}\nДата: {posts[0][1]}\nСсылка: {posts[0][2]}"
            )
    except Exception as e:
        await send_msg(cid, f"[Источник: {source_name}]\nОшибка при инициализации: {e}")
        return

    try:
        while True:
            await asyncio.sleep(interval)
            try:
                for kw in keywords_list:
                    api_url = build_api_url(endpoint, kw)
                    html = await fetch_news(api_url, base_url)
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
                            await send_msg(
                                cid,
                                f"[Источник: {source_name}]\nНовый пост для ключевого слова '{kw}':\nЗаголовок: {post[0]}\nДата: {post[1]}\nСсылка: {post[2]}"
                            )
                        baseline_dict[kw] = posts[0]
            except Exception as e:
                print(f"[Источник: {source_name}] Ошибка мониторинга: {e}")
    except asyncio.CancelledError:
        return

# ------------------------- FSM для /addkeywords -------------------------

class AddKeywords(StatesGroup):
    source = State()
    keyword = State()

@dp.message(Command("addkeywords"))
async def add_keywords_command(message, state: FSMContext):
    # Формируем список кнопок для каждого источника
    buttons = [types.KeyboardButton(text=ep["name"]) for ep in endpoints]
    markup = types.ReplyKeyboardMarkup(keyboard=[buttons], one_time_keyboard=True, resize_keyboard=True)
    await message.answer("Выберите источник для добавления нового ключевого слова:", reply_markup=markup)
    await state.set_state(AddKeywords.source)

@dp.message(StateFilter(AddKeywords.source))
async def add_keywords_source(message, state: FSMContext):
    source = message.text.strip()
    available = [ep["name"] for ep in endpoints]
    if source not in available:
        await message.answer(f"Источник '{source}' не найден. Доступные источники: {', '.join(available)}.")
        await state.clear()
        return
    await state.update_data(source=source)
    await message.answer(f"Введите новое ключевое слово для источника '{source}':")
    await state.set_state(AddKeywords.keyword)

@dp.message(StateFilter(AddKeywords.keyword))
async def add_keywords_keyword(message, state: FSMContext):
    cid = message.chat.id
    data = await state.get_data()
    source = data.get("source")
    new_kw = message.text.strip()
    if cid not in chat_settings:
        chat_settings[cid] = {}
    if source not in chat_settings[cid]:
        chat_settings[cid][source] = {"keywords": []}
    chat_settings[cid][source]["keywords"].append(new_kw)
    current_list = chat_settings[cid][source]["keywords"]
    await message.answer(
        f"Ключевое слово '{new_kw}' добавлено для источника '{source}'.\nТекущий список: {', '.join(current_list)}"
    )
    await state.clear()
    # Перезапускаем мониторинг для данного источника
    await restart_monitoring(cid, source)

# ------------------------- FSM для /cleankeywords -------------------------

class CleanKeywords(StatesGroup):
    source = State()

@dp.message(Command("cleankeywords"))
async def clean_keywords_command(message, state: FSMContext):
    buttons = [types.KeyboardButton(text=ep["name"]) for ep in endpoints]
    markup = types.ReplyKeyboardMarkup(keyboard=[buttons], one_time_keyboard=True, resize_keyboard=True)
    await message.answer("Выберите источник для сброса ключевых слов:", reply_markup=markup)
    await state.set_state(CleanKeywords.source)

@dp.message(StateFilter(CleanKeywords.source))
async def clean_keywords_source(message, state: FSMContext):
    cid = message.chat.id
    source = message.text.strip()
    available = [ep["name"] for ep in endpoints]
    if source not in available:
        await message.answer(f"Источник '{source}' не найден. Доступные источники: {', '.join(available)}.")
        await state.clear()
        return
    default_kw = None
    for ep in endpoints:
        if ep["name"] == source:
            default_kw = ep["default_keywords"].split()
            break
    if default_kw is None:
        await message.answer(f"Ключевые слова для источника '{source}' не найдены.")
        await state.clear()
        return
    if cid not in chat_settings:
        chat_settings[cid] = {}
    chat_settings[cid][source] = {"keywords": default_kw}
    await message.answer(
        f"Ключевые слова для источника '{source}' сброшены\nТекущий список: {', '.join(default_kw)}"
    )
    await state.clear()
    # Перезапускаем мониторинг для данного источника
    await restart_monitoring(cid, source)

# ------------------------- Обработчики команд /start и /stop -------------------------

@dp.message(Command("start"))
async def start_handler(message):
    cid = message.chat.id
    if cid not in ALLOWED_CHATS:
        return
    if cid in active_chats:
        await message.answer("Бот уже запущен! Мониторинг продолжается...")
        return
    active_chats[cid] = {}
    if cid not in chat_settings:
        chat_settings[cid] = {}
        for ep in endpoints:
            chat_settings[cid][ep["name"]] = {"keywords": ep["default_keywords"].split()}
    await message.answer(
        "Бот запущен! Мониторинг по обоим источникам начат.\n"
        "Команды:\n"
        "/addkeywords – добавить новое ключевое слово для источника\n"
        "/cleankeywords – сбросить все ключевые слова\n"
    )
    for ep in endpoints:
        active_chats[cid][ep["name"]] = asyncio.create_task(monitor_endpoint(cid, ep))

@dp.message(Command("stop"))
async def stop_handler(message):
    cid = message.chat.id
    if cid in active_chats:
        for task in active_chats[cid].values():
            task.cancel()
        del active_chats[cid]
        await message.answer("Мониторинг остановлен.")

# ------------------------- Стартап и завершение работы -------------------------

async def on_startup():
    global http_session
    http_session = aiohttp.ClientSession()
    load_chat_settings()

async def on_shutdown():
    await http_session.close()
    save_chat_settings()

async def main():
    await on_startup()
    try:
        await dp.start_polling(bot)
    finally:
        await on_shutdown()

if __name__ == "__main__":
    asyncio.run(main())
