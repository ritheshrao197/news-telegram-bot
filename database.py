import sqlite3
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DatabaseManager:
    def __init__(self, db_file='news_bot.db'):
        self.db_file = db_file
        self.init_database()
    
    def init_database(self):
        """Initialize all database tables"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Table for storing news articles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS news_articles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                article_hash TEXT UNIQUE,
                title TEXT,
                description TEXT,
                content TEXT,
                url TEXT,
                source TEXT,
                category TEXT,
                region TEXT,
                state TEXT,
                district TEXT,
                taluk TEXT,
                published_at TIMESTAMP,
                fetched_at TIMESTAMP,
                image_url TEXT,
                views INTEGER DEFAULT 0
            )
        ''')
        
        # Table for categories
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_name TEXT UNIQUE,
                last_updated TIMESTAMP
            )
        ''')
        
        # Table for user preferences
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_preferences (
                user_id INTEGER PRIMARY KEY,
                preferred_district TEXT,
                preferred_state TEXT,
                preferred_taluk TEXT,
                daily_digest BOOLEAN DEFAULT 0,
                last_notified TIMESTAMP
            )
        ''')
        
        # Table for custom sources
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS custom_sources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source_name TEXT,
                source_url TEXT,
                category TEXT,
                region TEXT,
                added_by INTEGER,
                added_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Table for fetch logs
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS fetch_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                fetch_time TIMESTAMP,
                source_name TEXT,
                articles_fetched INTEGER,
                status TEXT
            )
        ''')
        
        # Create indexes for faster queries
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_category ON news_articles(category)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_region ON news_articles(region)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_published ON news_articles(published_at)')
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_hash ON news_articles(article_hash)')
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def save_article(self, article: Dict) -> bool:
        """Save or update an article in the database"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT OR REPLACE INTO news_articles 
                (article_hash, title, description, content, url, source, category, 
                 region, state, district, taluk, published_at, fetched_at, image_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                article.get('hash'),
                article.get('title'),
                article.get('description'),
                article.get('content', ''),
                article.get('url'),
                article.get('source'),
                article.get('category', 'general'),
                article.get('region', ''),
                article.get('state', ''),
                article.get('district', ''),
                article.get('taluk', ''),
                article.get('published_at', datetime.now().isoformat()),
                datetime.now().isoformat(),
                article.get('image_url', '')
            ))
            conn.commit()
            return True
        except Exception as e:
            logger.error(f"Error saving article: {e}")
            return False
        finally:
            conn.close()
    
    def save_articles_batch(self, articles: List[Dict]) -> int:
        """Save multiple articles in batch"""
        saved_count = 0
        for article in articles:
            if self.save_article(article):
                saved_count += 1
        return saved_count
    
    def get_news_by_category(self, category: str, limit: int = 10, hours: int = 24) -> List[Dict]:
        """Get news from database for a specific category within last X hours"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT title, description, url, source, published_at, image_url, views, category
            FROM news_articles 
            WHERE category = ? AND fetched_at >= ?
            ORDER BY published_at DESC, fetched_at DESC
            LIMIT ?
        ''', (category, cutoff_time, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        articles = []
        for row in rows:
            articles.append({
                'title': row[0],
                'description': row[1],
                'url': row[2],
                'source': row[3],
                'published_at': row[4],
                'image_url': row[5],
                'views': row[6],
                'category': row[7]
            })
        
        return articles
    
    def get_news_by_region(self, region: str, limit: int = 10, hours: int = 48) -> List[Dict]:
        """Get news for a specific region (district/state/taluk)"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT title, description, url, source, published_at, image_url, region, category
            FROM news_articles 
            WHERE (region = ? OR district = ? OR state = ? OR taluk = ?) 
            AND fetched_at >= ?
            ORDER BY published_at DESC, fetched_at DESC
            LIMIT ?
        ''', (region, region, region, region, cutoff_time, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        articles = []
        for row in rows:
            articles.append({
                'title': row[0],
                'description': row[1],
                'url': row[2],
                'source': row[3],
                'published_at': row[4],
                'image_url': row[5],
                'region': row[6],
                'category': row[7]
            })
        
        return articles
    
    def get_local_news_by_location(self, district: str = None, state: str = None, taluk: str = None, village: str = None, limit: int = 10, hours: int = 72) -> List[Dict]:
        """Get hyper-local news matching district, taluk, village name either by column or keyword match"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        # Look back up to 72 hours for local news to ensure there's always something to show
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        query = '''
            SELECT title, description, url, source, published_at, category, region, state, district, taluk
            FROM news_articles
            WHERE fetched_at >= ? AND (1=0
        '''
        params = [cutoff_time]
        
        if state:
            query += " OR state = ? OR title LIKE ? OR description LIKE ?"
            params.extend([state, f"%{state}%", f"%{state}%"])
        if district:
            query += " OR district = ? OR region = ? OR title LIKE ? OR description LIKE ?"
            params.extend([district, district, f"%{district}%", f"%{district}%"])
        if taluk:
            query += " OR taluk = ? OR title LIKE ? OR description LIKE ?"
            params.extend([taluk, f"%{taluk}%", f"%{taluk}%"])
        if village:
            query += " OR title LIKE ? OR description LIKE ?"
            params.extend([f"%{village}%", f"%{village}%"])
            
        query += '''
            )
            ORDER BY published_at DESC, fetched_at DESC
            LIMIT ?
        '''
        params.append(limit)
        
        try:
            cursor.execute(query, params)
            rows = cursor.fetchall()
        except Exception as e:
            logger.error(f"Error querying local news: {e}")
            rows = []
        finally:
            conn.close()
            
        articles = []
        for row in rows:
            articles.append({
                'title': row[0],
                'description': row[1],
                'url': row[2],
                'source': row[3],
                'published_at': row[4],
                'category': row[5],
                'region': row[6],
                'state': row[7],
                'district': row[8],
                'taluk': row[9]
            })
        return articles
    
    def get_latest_news(self, limit: int = 20, hours: int = 24) -> List[Dict]:
        """Get latest news from all categories"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(hours=hours)).isoformat()
        
        cursor.execute('''
            SELECT title, description, url, source, published_at, category, region
            FROM news_articles 
            WHERE fetched_at >= ?
            ORDER BY published_at DESC, fetched_at DESC
            LIMIT ?
        ''', (cutoff_time, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        articles = []
        for row in rows:
            articles.append({
                'title': row[0],
                'description': row[1],
                'url': row[2],
                'source': row[3],
                'published_at': row[4],
                'category': row[5],
                'region': row[6]
            })
        
        return articles
    
    def increment_views(self, article_url: str):
        """Increment view count for an article"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            UPDATE news_articles 
            SET views = views + 1 
            WHERE url = ?
        ''', (article_url,))
        
        conn.commit()
        conn.close()
    
    def get_article_by_url(self, url: str) -> Optional[Dict]:
        """Get full article details by URL"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT title, description, content, url, source, published_at, image_url
            FROM news_articles 
            WHERE url = ?
        ''', (url,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'title': row[0],
                'description': row[1],
                'content': row[2],
                'url': row[3],
                'source': row[4],
                'published_at': row[5],
                'image_url': row[6]
            }
        return None
    
    def save_user_preference(self, user_id: int, district: str = None, state: str = None, taluk: str = None):
        """Save user's location preferences"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_preferences 
            (user_id, preferred_district, preferred_state, preferred_taluk, last_notified)
            VALUES (?, ?, ?, ?, ?)
        ''', (user_id, district, state, taluk, datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_user_preference(self, user_id: int) -> Dict:
        """Get user's saved preferences"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT preferred_district, preferred_state, preferred_taluk, daily_digest
            FROM user_preferences 
            WHERE user_id = ?
        ''', (user_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'district': row[0],
                'state': row[1],
                'taluk': row[2],
                'daily_digest': row[3]
            }
        return {}
    
    def get_statistics(self) -> Dict:
        """Get database statistics"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM news_articles')
        total_articles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(DISTINCT source) FROM news_articles')
        total_sources = cursor.fetchone()[0]
        
        cursor.execute('''
            SELECT category, COUNT(*) 
            FROM news_articles 
            GROUP BY category 
            ORDER BY COUNT(*) DESC 
            LIMIT 5
        ''')
        top_categories = cursor.fetchall()
        
        conn.close()
        
        return {
            'total_articles': total_articles,
            'total_sources': total_sources,
            'top_categories': dict(top_categories),
            'last_updated': datetime.now().isoformat()
        }
    
    def cleanup_old_articles(self, days: int = 7):
        """Delete articles older than specified days"""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('DELETE FROM news_articles WHERE fetched_at < ?', (cutoff_time,))
        deleted_count = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        logger.info(f"Cleaned up {deleted_count} old articles")
        return deleted_count