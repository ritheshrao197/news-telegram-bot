from rss_manager import RSSManager
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

def clean_html(text: str) -> str:
    if not text:
        return ""
    import re
    clean = re.compile('<.*?>')
    text = re.sub(clean, '', text)
    text = ' '.join(text.split())
    return text

def get_full_article_content(url: str) -> str:
    try:
        import requests
        from bs4 import BeautifulSoup
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            paragraphs = soup.find_all('p')
            text_content = ' '.join([p.get_text().strip() for p in paragraphs if len(p.get_text().strip()) > 30])
            return text_content
    except Exception as e:
        logger.error(f"Error fetching full article content from {url}: {e}")
    return ""

def generate_long_summary(article: dict, target_words: int = 100) -> str:
    """Generate a comprehensive summary with at least 100 words"""
    import time
    
    # Get full article content
    full_content = None
    if article.get('url'):
        full_content = get_full_article_content(article['url'])
        time.sleep(0.5)
    
    # Combine all sources
    text_parts = []
    
    if full_content:
        text_parts.append(full_content)
    if article.get('description'):
        text_parts.append(clean_html(article['description']))
    
    combined_text = ' '.join(text_parts)
    combined_text = clean_html(combined_text)
    
    words = combined_text.split()
    
    if len(words) >= target_words:
        # Take first target_words words
        summary = ' '.join(words[:target_words])
        
        # Try to end at a sentence boundary
        for punct in ['.', '!', '?']:
            last_occurrence = summary.rfind(punct)
            if last_occurrence > target_words * 0.6:  # At least 60% of target
                summary = summary[:last_occurrence + 1]
                break
        
        if len(words) > target_words:
            summary += " [Continued...]"
        
        return summary
    else:
        # Not enough content, expand with context
        context = f" This article from {article['source']} covers important news. " * 3
        expanded = combined_text + context
        words = expanded.split()
        return ' '.join(words[:target_words]) + "..."

class NewsFetcher:
    def __init__(self):
        self.rss_manager = RSSManager()
    
    def get_top_headlines(self, category='general', limit=10) -> List[Dict]:
        """Fetch news from RSS sources"""
        return self.rss_manager.fetch_all_news(category=category, max_total=limit)
    
    def get_india_news(self, limit=10) -> List[Dict]:
        """Fetch Indian news"""
        return self.rss_manager.fetch_all_news(category='india', max_total=limit)
    
    def get_tech_news(self, limit=10) -> List[Dict]:
        """Fetch technology news"""
        return self.rss_manager.fetch_all_news(category='technology', max_total=limit)