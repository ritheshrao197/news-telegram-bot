import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import feedparser
from config import TELEGRAM_BOT_TOKEN


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇮🇳 India News", callback_data='india')],
        [InlineKeyboardButton("🌍 World News", callback_data='world')],
    ]
    await update.message.reply_text("Welcome! Choose news:", reply_markup=InlineKeyboardMarkup(keyboard))

async def get_news(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text("Fetching news... Please wait.")
    
    # Test with a simple RSS feed
    if query.data == 'india':
        url = "https://timesofindia.indiatimes.com/rssfeedstopstories.cms"
    else:
        url = "http://rss.cnn.com/rss/edition.rss"
    
    feed = feedparser.parse(url)
    
    if not feed.entries:
        await query.message.reply_text("No news found. Please try again later.")
        return
    
    for entry in feed.entries[:5]:
        message = f"*{entry.title}*\n\n[Read more]({entry.link})"
        await query.message.reply_text(message, parse_mode='Markdown', disable_web_page_preview=True)
    
    await query.message.reply_text("✅ Done!")

app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
app.add_handler(CommandHandler("start", start))
app.add_handler(CallbackQueryHandler(get_news))

print("Test bot running...")
app.run_polling()