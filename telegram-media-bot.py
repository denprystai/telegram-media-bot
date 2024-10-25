import logging
import requests
import os
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ParseMode, WebAppInfo
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from flask import Flask, render_template, request

# Завантаження змінних середовища
load_dotenv()

# Установка логування
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Ваш API токен від BotFather
TELEGRAM_API_TOKEN = "8086724081:AAGbEy9hKGtLbG708BCsqMbD-B_yp15s7Dc"

# Збереження ключових слів у базі даних
conn = sqlite3.connect('keywords.db', check_same_thread=False)
c = conn.cursor()
c.execute('''CREATE TABLE IF NOT EXISTS keywords (keyword TEXT UNIQUE)''')
conn.commit()

# Flask додаток для Web App
app = Flask(__name__)

@app.route('/')
def home():
    keywords = get_keywords()
    return render_template('index.html', keywords=keywords)

@app.route('/add_keyword', methods=['POST'])
def add_keyword_web():
    keyword = request.form['keyword']
    try:
        c.execute('INSERT INTO keywords (keyword) VALUES (?)', (keyword,))
        conn.commit()
        return 'Ключове слово додано!', 200
    except sqlite3.IntegrityError:
        return 'Ключове слово вже існує!', 400

@app.route('/remove_keyword', methods=['POST'])
def remove_keyword_web():
    keyword = request.form['keyword']
    c.execute('DELETE FROM keywords WHERE keyword = ?', (keyword,))
    conn.commit()
    return 'Ключове слово видалено!', 200

@app.route('/search', methods=['GET'])
def search_news_web():
    keyword = request.args.get('keyword')
    articles = search_news(keyword)
    return {'articles': articles}, 200

# Функція для отримання ключових слів з бази даних
def get_keywords():
    c.execute('SELECT keyword FROM keywords')
    return [row[0] for row in c.fetchall()]

# Функція старту для запуску бота
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    web_app = WebAppInfo(url="https://your-server-address")  # Заміни на свій URL
    keyboard = [[InlineKeyboardButton("Відкрити Web App", web_app=web_app)]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        'Привіт! Я допоможу тобі моніторити новини. Дай мені ключові слова, щоб почати! Використовуй Web App для керування ключовими словами та пошуку новин.',
        reply_markup=reply_markup
    )

# Функція для пошуку новин
# Ключові слова надаються через команду /search keyword
# Бот шукатиме новини та надсилатиме зведення з лінком

def search_news(keyword):
    url = f'https://news.google.com/search?q={keyword}'  # приклад, де використовуємо пошук Google News
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    articles = []

    for item in soup.find_all('h3')[:5]:  # знайдемо перші 5 новинних заголовків
        title = item.get_text()
        link = item.a['href']
        if link.startswith('/'):
            link = f'https://news.google.com{link}'
        articles.append((title, link))
    
    return articles

# Автоматичний моніторинг новин
async def periodic_search(context: ContextTypes.DEFAULT_TYPE) -> None:
    keywords = get_keywords()
    if not keywords:
        return

    for keyword in keywords:
        articles = search_news(keyword)
        if articles:
            chat_id = context.job.chat_id
            await context.bot.send_message(chat_id=chat_id, text=f'*Результати для ключового слова:* "{keyword}":', parse_mode=ParseMode.MARKDOWN)
            for title, link in articles:
                await context.bot.send_message(chat_id=chat_id, text=f'[{title}]({link})', parse_mode=ParseMode.MARKDOWN)

# Основна функція для запуску бота
async def main():
    application = ApplicationBuilder().token(TELEGRAM_API_TOKEN).build()

    # Команди бота
    application.add_handler(CommandHandler("start", start))

    # Планувальник для автоматичного моніторингу новин
    scheduler = AsyncIOScheduler()
    scheduler.add_job(periodic_search, 'interval', minutes=30, args=[application])
    scheduler.start()

    # Запуск бота
    await application.run_polling()

if __name__ == '__main__':
    import threading
    import asyncio

    # Запуск Flask додатку в окремому потоці
    threading.Thread(target=lambda: app.run(host='0.0.0.0', port=5000)).start()

    # Запуск Telegram бота
    asyncio.run(main())
