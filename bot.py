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
        
        keyboard = [
            [InlineKeyboardButton("💛❤️ Karnataka", callback_data='state_karnataka')],
            [InlineKeyboardButton("🌍 Other State", callback_data='state_other')],
            [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]
        ]
        
        await query.edit_message_text(
            "📍 *Set Your Location*\n\n"
            "Please select your state from the options below:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        
    async def show_karnataka_districts_p1(self, query):
        keyboard = [
            [InlineKeyboardButton("Bangalore Urban", callback_data='sel_dist_bangalore'),
             InlineKeyboardButton("Bangalore Rural", callback_data='sel_dist_bangalore rural')],
            [InlineKeyboardButton("Mysuru", callback_data='sel_dist_mysore'),
             InlineKeyboardButton("Belagavi", callback_data='sel_dist_belgaum')],
            [InlineKeyboardButton("Mangaluru", callback_data='sel_dist_mangalore'),
             InlineKeyboardButton("Hubli-Dharwad", callback_data='sel_dist_dharwad')],
            [InlineKeyboardButton("Shivamogga", callback_data='sel_dist_shimoga'),
             InlineKeyboardButton("Hassan", callback_data='sel_dist_hassan')],
            [InlineKeyboardButton("Mandya", callback_data='sel_dist_mandya'),
             InlineKeyboardButton("Tumakuru", callback_data='sel_dist_tumkur')],
            [InlineKeyboardButton("Udupi", callback_data='sel_dist_udupi'),
             InlineKeyboardButton("Chikkamagaluru", callback_data='sel_dist_chikkamagaluru')],
            [InlineKeyboardButton("➡️ Next Page", callback_data='dist_kar_page_2')],
            [InlineKeyboardButton("⬅️ Back to States", callback_data='set_location')]
        ]
        await query.edit_message_text(
            "📍 *Select Karnataka District (Page 1/2)*\n\nChoose your district:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

    async def show_karnataka_districts_p2(self, query):
        keyboard = [
            [InlineKeyboardButton("Bagalkote", callback_data='sel_dist_bagalkot'),
             InlineKeyboardButton("Ballari", callback_data='sel_dist_bellary')],
            [InlineKeyboardButton("Bidar", callback_data='sel_dist_bidar'),
             InlineKeyboardButton("Chamarajanagar", callback_data='sel_dist_chamarajanagar')],
            [InlineKeyboardButton("Chikkaballapur", callback_data='sel_dist_chikkaballapur'),
             InlineKeyboardButton("Chitradurga", callback_data='sel_dist_chitradurga')],
            [InlineKeyboardButton("Davanagere", callback_data='sel_dist_davanagere'),
             InlineKeyboardButton("Gadag", callback_data='sel_dist_gadag')],
            [InlineKeyboardButton("Haveri", callback_data='sel_dist_haveri'),
             InlineKeyboardButton("Kalaburagi", callback_data='sel_dist_kalaburagi')],
            [InlineKeyboardButton("Kodagu", callback_data='sel_dist_kodagu'),
             InlineKeyboardButton("Kolar", callback_data='sel_dist_kolar')],
            [InlineKeyboardButton("Koppal", callback_data='sel_dist_koppal'),
             InlineKeyboardButton("Raichur", callback_data='sel_dist_raichur')],
            [InlineKeyboardButton("Ramanagara", callback_data='sel_dist_ramanagara'),
             InlineKeyboardButton("Yadgir", callback_data='sel_dist_yadgir')],
            [InlineKeyboardButton("Vijayapura", callback_data='sel_dist_vijayapura'),
             InlineKeyboardButton("Uttara Kannada", callback_data='sel_dist_uttara kannada')],
            [InlineKeyboardButton("⬅️ Previous Page", callback_data='state_karnataka')]
        ]
        await query.edit_message_text(
            "📍 *Select Karnataka District (Page 2/2)*\n\nChoose your district:",
            parse_mode='Markdown',
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle user text messages (for location setting)"""
        user_id = update.effective_user.id
        
        if context.user_data.get('awaiting_other_location'):
            text = update.message.text.strip()
            parts = [p.strip() for p in text.split(',')]
            
            state = parts[0]
            district = parts[1] if len(parts) > 1 else None
            
            self.db.save_user_preference(user_id, state=state, district=district)
            
            context.user_data['awaiting_other_location'] = False
            context.user_data['awaiting_taluk'] = True
            
            keyboard = [[InlineKeyboardButton("⏭️ Skip & Finish", callback_data='finish_location')]]
            
            await update.message.reply_text(
                f"✅ *Location saved!*\nState: *{state.title()}*\nDistrict: *{district.title() if district else 'None'}*\n\n"
                f"To refine your rural local news, please type your **Taluk** or **Village** name (e.g. your village/hobli name) and send it now, or click **Skip**:",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            
        elif context.user_data.get('awaiting_taluk'):
            taluk = update.message.text.strip()
            pref = self.db.get_user_preference(user_id)
            
            self.db.save_user_preference(
                user_id,
                state=pref.get('state'),
                district=pref.get('district'),
                taluk=taluk
            )
            
            context.user_data['awaiting_taluk'] = False
            
            await update.message.reply_text(
                f"✅ *Taluk/Village saved:* {taluk.title()}\n\n"
                f"All set! Click /start and select 'Local News' to get hyper-local news from your area!"
            )
            
        elif context.user_data.get('awaiting_location'):
            location = update.message.text.strip()
            self.db.save_user_preference(user_id, district=location)
            context.user_data['awaiting_location'] = False
            
            await update.message.reply_text(
                f"✅ Location saved: {location.title()}\n\n"
                f"Now use /start and select 'Local News' to get news from your area!"
            )
        else:
            await update.message.reply_text("Use /start to see available commands")

    async def get_local_news(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        
        user_id = update.effective_user.id
        pref = self.db.get_user_preference(user_id)
        
        district = pref.get('district')
        state = pref.get('state')
        taluk = pref.get('taluk')
        
        if not district and not state:
            keyboard = [[InlineKeyboardButton("📍 Set My Location", callback_data='set_location')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
            await query.edit_message_text(
                "📍 *No Location Set!*\n\n"
                "Please configure your location first to get hyper-local district, taluk, and village news.",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return
            
        await query.edit_message_text(
            f"📡 *Scanning database for hyper-local news...*\n"
            f"📍 Location: {taluk.title() + ', ' if taluk else ''}{district.title() if district else ''}{' (' + state.title() + ')' if state else ''}\n\n"
            f"_Running semantic keyword extraction... Please wait._",
            parse_mode='Markdown'
        )
        
        articles = self.db.get_local_news_by_location(
            district=district,
            state=state,
            taluk=taluk,
            village=taluk,
            limit=10
        )
        
        if not articles:
            # Fallback to broader state/national news
            articles = self.db.get_news_by_category('india', limit=8)
            if not articles:
                await query.message.reply_text("No local news is currently available. We are updating databases now. Please try again soon!")
                return
            await query.message.reply_text(
                f"ℹ️ _No custom taluk/village news found matching your specific keywords in the last 72 hours, but here is some regional/national news:_ \n"
            )
            
        # Store articles in context.user_data for detailed summary lookup
        context.user_data['articles'] = {}
        
        for idx, article in enumerate(articles[:8], 1):
            message = f"""
*{idx}. {article['title']}*

📌 *Source:* {article['source']}
📂 *Category:* {article.get('category', 'Local').title()}
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
            
        nav_keyboard = [[InlineKeyboardButton("🔄 Refresh Local News", callback_data='local')],
                        [InlineKeyboardButton("🏠 Main Menu", callback_data='main_menu')]]
        await query.message.reply_text("✅ That's all!", reply_markup=InlineKeyboardMarkup(nav_keyboard))
    
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
        elif query.data == 'local':
            await self.get_local_news(update, context)
        elif query.data == 'state_karnataka':
            await query.answer()
            await self.show_karnataka_districts_p1(query)
        elif query.data == 'dist_kar_page_2':
            await query.answer()
            await self.show_karnataka_districts_p2(query)
        elif query.data == 'state_other':
            await query.answer()
            context.user_data['awaiting_other_location'] = True
            await query.edit_message_text(
                "📍 *Set Other Location*\n\n"
                "Please type your State and District name separated by a comma.\n\n"
                "Example: `Maharashtra, Pune` or `Kerala, Kochi`",
                parse_mode='Markdown'
            )
        elif query.data.startswith('sel_dist_'):
            await query.answer()
            district_name = query.data.replace('sel_dist_', '')
            user_id = update.effective_user.id
            
            # Save state as Karnataka, and the district
            self.db.save_user_preference(user_id, state='karnataka', district=district_name)
            
            context.user_data['awaiting_taluk'] = True
            
            keyboard = [[InlineKeyboardButton("⏭️ Skip & Finish", callback_data='finish_location')]]
            await query.edit_message_text(
                f"✅ *District set to {district_name.title()}!*\n\n"
                f"To refine your local news further, would you like to add a specific **Taluk** or **Village**? (e.g. `Hunsur` or `Srirangapatna` or `Mandya Village`)\n\n"
                f"_Send your Taluk/Village name as a message now, or click **Skip & Finish** below:_ ",
                parse_mode='Markdown',
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        elif query.data == 'finish_location':
            await query.answer("Location preference saved successfully!")
            context.user_data['awaiting_taluk'] = False
            context.user_data['awaiting_other_location'] = False
            await self.start_command(update, context)
        elif query.data.startswith('detail_'):
            await query.answer()
            idx = int(query.data.replace('detail_', ''))
            article = context.user_data.get('articles', {}).get(idx)
            
            if article:
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