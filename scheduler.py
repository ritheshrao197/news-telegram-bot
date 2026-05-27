import time
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from news_fetcher import NewsFetcher
from database import DatabaseManager
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class NewsScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.news_fetcher = NewsFetcher()
        self.db = DatabaseManager()
        self.is_running = False
    
    def fetch_and_store_news(self):
        """Fetch news from all sources and store in database"""
        logger.info("Starting scheduled news fetch...")
        start_time = time.time()
        
        categories = ['general', 'india', 'technology', 'business', 'sports', 'science', 'entertainment']
        total_fetched = 0
        
        for category in categories:
            try:
                logger.info(f"Fetching {category} news...")
                articles = self.news_fetcher.get_top_headlines(category=category, limit=15)
                
                if articles:
                    saved = self.db.save_articles_batch(articles)
                    total_fetched += saved
                    logger.info(f"Saved {saved} articles for {category}")
                else:
                    logger.warning(f"No articles fetched for {category}")
                
                # Small delay to avoid overwhelming sources
                time.sleep(2)
                
            except Exception as e:
                logger.error(f"Error fetching {category} news: {e}")
        
        # Fetch rural and local news
        try:
            rural_articles = self.news_fetcher.rss_manager.fetch_all_news(category='rural')
            if rural_articles:
                saved = self.db.save_articles_batch(rural_articles)
                total_fetched += saved
                logger.info(f"Saved {saved} rural news articles")
        except Exception as e:
            logger.error(f"Error fetching rural news: {e}")
        
        # Clean up old articles (older than 7 days)
        deleted = self.db.cleanup_old_articles(days=7)
        
        elapsed_time = time.time() - start_time
        logger.info(f"News fetch completed in {elapsed_time:.2f} seconds")
        logger.info(f"Total new articles: {total_fetched}, Old articles deleted: {deleted}")
        
        # Log the fetch
        self.log_fetch(total_fetched, elapsed_time)
    
    def log_fetch(self, articles_count: int, duration: float):
        """Log the fetch operation"""
        import sqlite3
        conn = sqlite3.connect(self.db.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO fetch_logs (fetch_time, source_name, articles_fetched, status)
            VALUES (?, ?, ?, ?)
        ''', (datetime.now().isoformat(), 'scheduled_fetch', articles_count, 'success'))
        
        conn.commit()
        conn.close()
    
    def start_scheduler(self):
        """Start the background scheduler"""
        if not self.is_running:
            # Fetch news every hour
            self.scheduler.add_job(
                func=self.fetch_and_store_news,
                trigger=IntervalTrigger(hours=1),
                id='hourly_news_fetch',
                name='Fetch news every hour',
                replace_existing=True
            )
            
            # Also fetch on startup immediately
            self.scheduler.add_job(
                func=self.fetch_and_store_news,
                trigger=IntervalTrigger(seconds=10),  # Small delay to let bot start
                id='startup_fetch',
                replace_existing=True
            )
            
            self.scheduler.start()
            self.is_running = True
            logger.info("News scheduler started - fetching news every hour")
            
            # Print next run time
            next_run = self.scheduler.get_job('hourly_news_fetch').next_run_time
            logger.info(f"Next scheduled fetch at: {next_run}")
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        if self.is_running:
            self.scheduler.shutdown()
            self.is_running = False
            logger.info("News scheduler stopped")
    
    def manual_fetch(self):
        """Manually trigger a news fetch"""
        logger.info("Manual news fetch triggered")
        self.fetch_and_store_news()
        return {"status": "success", "message": "News fetch completed"}