import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from database import DatabaseManager
from scheduler import NewsScheduler
from config import TELEGRAM_BOT_TOKEN
from datetime import datetime

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsBot:
    def __init__(self):
        self.db = DatabaseManager()
        self.scheduler = NewsScheduler()
    
    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        keyboard = [
            [InlineKeyboardButton("📰 Latest News", callback_data='latest')],
            [InlineKeyboardButton("🇮🇳 India News", callback_data='india')],
            [InlineKeyboardButton("🏘️ Local News", callback_data='local')],
            [InlineKeyboardButton("📊 Statistics", callback_data='stats')],
            [InlineKeyboardButton("📍 Set My Location", callback_data='set_location')],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Get user preference if exists
        user_pref = self.db.get_user_preference(update.effective_user.id)
        location_msg = ""
        if user_pref.get('district'):
            location_msg = f"\n📍 Your location: {user_pref['district'].title()}"
        
        target_msg = update.message if update.message else update.callback_query.message
        await target_msg.reply_text(
            f"📰 *Welcome to Smart News Bot!*{location_msg}\n\n"
            f"✅ News is updated *every hour* and served from database\n"
            f"📊 Response time: < 1 second\n"
            f"🗄️ Database status: {self.db.get_statistics()['total_articles']} articles stored\n\n"
            f"Select an option:",
            parse_mode='Markdown',
            reply_markup=reply_markup
        )
    
    async def get_latest_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("📡 Fetching latest news from database...")
        
        articles = self.db.get_latest_news(limit=10)
        
        if not articles:
            await query.message.reply_text(
                "No news available. The system is fetching news now. Please try again in a few minutes."
            )
            return
        
        # Store articles in context.user_data for detailed summary lookup
        context.user_data['articles'] = {}
        
        for idx, article in enumerate(articles[:8], 1):
            message = f"""
*{idx}. {article['title']}*

📌 *Source:* {article['source']}
📂 *Category:* {article['category'].title()}
📝 *Summary:* {article['description'][:150]}...

🔗 [Read full article]({article['url']})
            """
            
            context.user_data['articles'][idx] = article
            
            keyboard = [[InlineKeyboardButton("📖 Read More", callback_data=f'detail_{idx}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        
        # Update view count
        for article in articles[:8]:
            self.db.increment_views(article['url'])
        
        nav_keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='latest')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
        await query.message.reply_text("✅ That's all!", reply_markup=InlineKeyboardMarkup(nav_keyboard))
    
    async def get_india_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text("📡 Fetching India news from database...")
        
        articles = self.db.get_news_by_category('india', limit=10)
        
        if not articles:
            await query.message.reply_text("No India news available at the moment.")
            return
        
        # Store articles in context.user_data for detailed summary lookup
        context.user_data['articles'] = {}
        
        for idx, article in enumerate(articles[:8], 1):
            message = f"""
*{idx}. {article['title']}*

📌 *Source:* {article['source']}
📝 *Summary:* {article['description'][:150]}...

🔗 [Read full article]({article['url']})
            """
            
            context.user_data['articles'][idx] = article
            
            keyboard = [[InlineKeyboardButton("📖 Read More", callback_data=f'detail_{idx}')]]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await query.message.reply_text(
                message,
                parse_mode='Markdown',
                reply_markup=reply_markup,
                disable_web_page_preview=True
            )
        
        nav_keyboard = [[InlineKeyboardButton("🔄 Refresh", callback_data='india')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
        await query.message.reply_text("✅ That's all!", reply_markup=InlineKeyboardMarkup(nav_keyboard))
    
    async def get_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        stats = self.db.get_statistics()
        
        message = f"""
📊 *Database Statistics*

📰 Total Articles: {stats['total_articles']}
📡 News Sources: {stats['total_sources']}

📂 *Top Categories:*
"""
        for category, count in list(stats['top_categories'].items())[:5]:
            message += f"• {category.title()}: {count} articles\n"
        
        message += f"\n⏰ Last Updated: {stats['last_updated'][:19]}"
        message += f"\n\n🔄 News is updated every hour automatically"
        
        keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
        await query.edit_message_text(message, parse_mode='Markdown', reply_markup=InlineKeyboardMarkup(keyboard))
    
    async def set_location(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        await query.edit_message_text(
            "📍 *Set Your Location*\n\n"
            "Send your district name to get local news.\n\n"
            "Example: `Varanasi` or `Chennai`\n\n"
            "Just type the district name and send it.",
            parse_mode='Markdown'
        )
        
        # Set a flag to expect location input
        context.user_data['awaiting_location'] = True
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user text messages (for location setting)"""
        if context.user_data.get('awaiting_location'):
            location = update.message.text.strip()
            
            # Save user preference
            self.db.save_user_preference(update.effective_user.id, district=location)
            
            await update.message.reply_text(
                f"✅ Location saved: {location.title()}\n\n"
                f"Now use /start and select 'Local News' to get news from your area!"
            )
            
            context.user_data['awaiting_location'] = False
        else:
            await update.message.reply_text("Use /start to see available commands")
    
    async def button_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        
        if query.data == 'main_menu':
            await self.start_command(update, context)
        elif query.data == 'latest':
            await self.get_latest_news(update, context)
        elif query.data == 'india':
            await self.get_india_news(update, context)
        elif query.data == 'stats':
            await self.get_stats(update, context)
        elif query.data == 'set_location':
            await self.set_location(update, context)
        elif query.data.startswith('detail_'):
            await query.answer()
            idx = int(query.data.replace('detail_', ''))
            article = context.user_data.get('articles', {}).get(idx)
            
            if article:
                # Let user know we are generating it
                loading_msg = await query.message.reply_text(
                    f"📡 *Generating comprehensive summary for:*\n_{article['title']}_\n\n"
                    f"_Fetching full article body and running semantic summarizer... Please wait._",
                    parse_mode='Markdown'
                )
                
                from news_fetcher import generate_long_summary
                long_summary = generate_long_summary(article, target_words=120)
                
                detail_text = f"""
📰 *{article['title']}*

📌 *Source:* {article['source']}
📂 *Category:* {article.get('category', 'General').title()}

📝 *Comprehensive Summary:*
{long_summary}

🔗 *Read Full Article:* [Click Here]({article['url']})
                """
                
                keyboard = [[InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                # Delete the loading message
                try:
                    await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=loading_msg.message_id)
                except Exception:
                    pass
                
                await query.message.reply_text(
                    detail_text,
                    parse_mode='Markdown',
                    reply_markup=reply_markup,
                    disable_web_page_preview=True
                )
        else:
            await query.answer()
    
    def run(self):
        if not TELEGRAM_BOT_TOKEN:
            print("❌ Error: TELEGRAM_BOT_TOKEN not found")
            return
        
        # Start the background news scheduler
        self.scheduler.start_scheduler()
        
        # Create bot application
        app = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
        
        # Add handlers
        app.add_handler(CommandHandler("start", self.start_command))
        app.add_handler(CommandHandler("stats", self.get_stats))
        app.add_handler(CallbackQueryHandler(self.button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        print("🚀 News Bot is running with database and hourly updates!")
        print(f"📊 Database initialized")
        print(f"🔄 News will be fetched every hour")
        print(f"⏰ First fetch in a few seconds...")
        
        app.run_polling()

if __name__ == '__main__':
    bot = NewsBot()
    bot.run()