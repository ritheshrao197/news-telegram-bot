import feedparser
import hashlib
import json
import re
from datetime import datetime
from typing import List, Dict, Optional
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RSSManager:
    def __init__(self, sources_file='sources.json'):
        try:
            with open(sources_file, 'r', encoding='utf-8') as f:
                self.config = json.load(f)
        except FileNotFoundError:
            self.config = {"rss_sources": {}, "custom_sources": []}
        
        self.sent_articles = set()
        self.db_file = 'sent_articles.txt'
        self.load_sent_articles()
    
    def load_sent_articles(self):
        """Load previously sent articles to avoid duplicates"""
        try:
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.sent_articles = set(line.strip() for line in f)
        except FileNotFoundError:
            self.sent_articles = set()
    
    def save_sent_article(self, url_hash: str):
        """Save sent article hash"""
        self.sent_articles.add(url_hash)
        with open(self.db_file, 'a', encoding='utf-8') as f:
            f.write(url_hash + '\n')
    
    def clean_html(self, text: str) -> str:
        """Remove HTML tags using regex"""
        if not text:
            return ""
        clean = re.compile('<.*?>')
        text = re.sub(clean, '', text)
        text = ' '.join(text.split())
        return text[:300]
    
    def fetch_from_rss(self, source: Dict, limit: int = 5) -> List[Dict]:
        """Fetch news from a single RSS source"""
        try:
            feed = feedparser.parse(source['url'])
            articles = []
            
            for entry in feed.entries[:limit]:
                # Create unique hash for article
                article_hash = hashlib.md5(
                    f"{entry.get('link', '')}{entry.get('title', '')}".encode('utf-8')
                ).hexdigest()
                
                # Skip if already sent today (you can modify this logic)
                if article_hash in self.sent_articles:
                    continue
                
                article = {
                    'title': entry.get('title', 'No title'),
                    'description': self.clean_html(entry.get('summary', entry.get('description', 'No description'))),
                    'url': entry.get('link', '#'),
                    'source': source['name'],
                    'published_at': entry.get('published', entry.get('pubDate', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))),
                    'category': source.get('category', 'general'),
                    'hash': article_hash
                }
                
                articles.append(article)
                self.save_sent_article(article_hash)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching RSS from {source['name']}: {e}")
            return []
    
    def fetch_all_news(self, category: str = None, max_total: int = 15) -> List[Dict]:
        """Fetch news from all sources matching criteria"""
        all_articles = []
        
        for group, sources in self.config['rss_sources'].items():
            for source in sources:
                if category and source.get('category') != category:
                    continue
                articles = self.fetch_from_rss(source, 3)
                all_articles.extend(articles)
                if len(all_articles) >= max_total:
                    break
            if len(all_articles) >= max_total:
                break
        
        return all_articles[:max_total]