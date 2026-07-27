import feedparser
from datetime import datetime
import time
from typing import List, Dict, Any
from src.crawler.blogs.base_blog_adapter import BaseBlogAdapter
import logging

logger = logging.getLogger(__name__)

class RssBlogAdapter(BaseBlogAdapter):
    def _parse_date(self, entry) -> datetime:
        if hasattr(entry, 'published_parsed') and entry.published_parsed:
            return datetime.fromtimestamp(time.mktime(entry.published_parsed))
        if hasattr(entry, 'updated_parsed') and entry.updated_parsed:
            return datetime.fromtimestamp(time.mktime(entry.updated_parsed))
        return datetime.now()

    def fetch_new_posts(self) -> List[Dict[str, Any]]:
        possible_urls = [
            self.url.rstrip('/') + '/feed',
            self.url.rstrip('/') + '/rss',
            self.url.rstrip('/') + '/rss.xml',
            self.url.rstrip('/') + '/feed.xml',
            self.url.rstrip('/') + '/index.xml',
            self.url
        ]
        
        feed = None
        for purl in possible_urls:
            f = feedparser.parse(purl)
            if f.entries:
                feed = f
                break
                
        if not feed or not feed.entries:
            logger.debug(f"No RSS feed found or empty for {self.name} at {self.url}")
            return []
            
        max_days = self.config.get('max_days_back', 7)
        max_posts = self.config.get('max_posts_per_run', 5)
        pull_all = self.config.get('pull_all', False)
        
        now = datetime.now()
        posts = []
        
        for entry in feed.entries:
            if not pull_all and max_posts and len(posts) >= max_posts:
                break
                
            pub_date = self._parse_date(entry)
            if not pull_all and max_days:
                days_diff = (now - pub_date).days
                if days_diff > max_days:
                    continue
            
            content = ""
            if hasattr(entry, 'content'):
                content = entry.content[0].value
            elif hasattr(entry, 'summary'):
                content = entry.summary
            elif hasattr(entry, 'description'):
                content = entry.description
                
            posts.append({
                'url': entry.link,
                'title': entry.get('title', ''),
                'author': entry.get('author', ''),
                'publish_date': pub_date.isoformat(),
                'raw_content': content
            })
            
        return posts
