from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
import requests
import sqlite3

# Твій токен
TOKEN = '8086724081:AAGbEy9hKGtLbG708BCsqMbD-B_yp15s7Dc'

# Створення бази даних
conn = sqlite3.connect('keywords.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''CREATE TABLE IF NOT EXISTS keywords (
    user_id INTEGER,
    keyword TEXT
)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS favorites (
    user_id INTEGER,
    news_title TEXT,
    news_url TEXT,
    summary TEXT
)''')
conn.commit()

# Додавання ключового слова
async def add_keyword(update: Update, context: CallbackContext) -> None:
    keyword = ' '.join(context.args)
    user_id = update.message.from_user.id
    if keyword:
        cursor.execute('INSERT INTO keywords (user_id, keyword) VALUES (?, ?)', (user_id, keyword))
        conn.commit()
        await update.message.reply_text(f"Ключове слово '{keyword}' додано.")
    else:
        await update.message.reply_text("Будь ласка, вкажи ключове слово після команди /add_keyword.")

# Перегляд ключових слів
async def list_keywords(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    cursor.execute('SELECT keyword FROM keywords WHERE user_id = ?', (user_id,))
    keywords = cursor.fetchall()
    if keywords:
        message = "Твої ключові слова:\n" + '\n'.join([kw[0] for kw in keywords])
    else:
        message = "Наразі у тебе немає доданих ключових слів."
    await update.message.reply_text(message)

# Видалення ключового слова
async def remove_keyword(update: Update, context: CallbackContext) -> None:
    keyword = ' '.join(context.args)
    user_id = update.message.from_user.id
    cursor.execute('DELETE FROM keywords WHERE user_id = ? AND keyword = ?', (user_id, keyword))
    conn.commit()
    await update.message.reply_text(f"Ключове слово '{keyword}' видалено.")

# Функція для старту бота
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text("Привіт! Я допоможу тобі моніторити новини. Використовуй команди:\n"
                                    "/add_keyword - додати ключове слово\n"
                                    "/list_keywords - переглянути ключові слова\n"
                                    "/remove_keyword - видалити ключове слово")

# Функція для відправки улюблених новин
async def list_favorites(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    cursor.execute('SELECT news_title, news_url FROM favorites WHERE user_id = ?', (user_id,))
    favorites = cursor.fetchall()
    if favorites:
        message = "Твої обрані новини:\n" + '\n'.join([f"{fav[0]}: {fav[1]}" for fav in favorites])
    else:
        message = "Наразі у тебе немає обраних новин."
    await update.message.reply_text(message)

# Налаштування бота
def main() -> None:
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("add_keyword", add_keyword))
    app.add_handler(CommandHandler("list_keywords", list_keywords))
    app.add_handler(CommandHandler("remove_keyword", remove_keyword))
    app.add_handler(CommandHandler("favorites", list_favorites))
    app.run_polling()

if __name__ == '__main__':
    main()
NEWS_API_KEY = 'your_news_api_key'  # Встав сюди API ключ для NewsAPI

def fetch_news(keyword: str) -> list:
    url = f"https://newsapi.org/v2/everything?q={keyword}&apiKey={NEWS_API_KEY}&language=uk"
    response = requests.get(url)
    data = response.json()
    articles = data.get('articles', [])
    return [
        {
            'title': article['title'],
            'url': article['url'],
            'summary': article['description'],
            'image': article['urlToImage']
        }
        for article in articles[:3]  # Беремо лише перші три статті для прикладу
    ]
import schedule
import time
from threading import Thread

async def check_news() -> None:
    cursor.execute('SELECT DISTINCT user_id, keyword FROM keywords')
    user_keywords = cursor.fetchall()
    for user_id, keyword in user_keywords:
        news = fetch_news(keyword)
        for article in news:
            message = f"{article['title']}\n{article['summary']}\n{article['url']}"
            context.bot.send_message(chat_id=user_id, text=message)

def run_scheduler():
    schedule.every(10).minutes.do(lambda: asyncio.run(check_news()))  # Перевірка кожні 10 хвилин
    while True:
        schedule.run_pending()
        time.sleep(1)

# Запуск планувальника в окремому потоці
Thread(target=run_scheduler, daemon=True).start()
async def send_news(update: Update, context: CallbackContext, news):
    keyboard = [
        [InlineKeyboardButton("Додати в обрані", callback_data=f"fav_{news['title']}_{news['url']}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"{news['title']}\n{news['summary']}\n{news['url']}",
        reply_markup=reply_markup
    )

async def button_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    data = query.data.split('_')
    if data[0] == 'fav':
        title = data[1]
        url = data[2]
        cursor.execute('INSERT INTO favorites (user_id, news_title, news_url, summary) VALUES (?, ?, ?, ?)', 
                       (user_id, title, url, ''))
        conn.commit()
        await query.answer('Новина додана в обрані.')
