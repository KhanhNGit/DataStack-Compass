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

    def _process_rss2json_items(self, items: List[Dict], max_days: int, max_posts: int, pull_all: bool) -> List[Dict]:
        now = datetime.now()
        posts = []
        for item in items:
            if not pull_all and max_posts and len(posts) >= max_posts:
                break
                
            pub_date_str = item.get('pubDate', '')
            try:
                pub_date = datetime.strptime(pub_date_str, "%Y-%m-%d %H:%M:%S")
            except:
                pub_date = now
                
            if not pull_all and max_days:
                days_diff = (now - pub_date).days
                if days_diff > max_days:
                    continue
                    
            content = item.get('content') or item.get('description', '')
            posts.append({
                'url': item.get('link', ''),
                'title': item.get('title', ''),
                'author': item.get('author', ''),
                'publish_date': pub_date.isoformat(),
                'raw_content': content
            })
        return posts

    def fetch_new_posts(self) -> List[Dict[str, Any]]:
        possible_urls = []
        if 'rss_url' in self.config:
            possible_urls.append(self.config['rss_url'])
        else:
            possible_urls = [
                self.url.rstrip('/') + '/feed',
                self.url.rstrip('/') + '/rss',
                self.url.rstrip('/') + '/rss.xml',
                self.url.rstrip('/') + '/feed.xml',
                self.url.rstrip('/') + '/index.xml',
                self.url
            ]
        
        feed = None
        f = None
        for purl in possible_urls:
            f = feedparser.parse(purl)
            if f.entries:
                feed = f
                break
                
        import urllib.error
        is_network_error = False
        if f and hasattr(f, 'bozo') and f.bozo == 1 and hasattr(f, 'bozo_exception') and isinstance(f.bozo_exception, urllib.error.URLError):
            is_network_error = True
                
        if not feed or not feed.entries:
            if is_network_error:
                import requests
                target_rss = possible_urls[0] if 'rss_url' in self.config else (self.url.rstrip('/') + '/feed')
                proxy_url = f"https://api.rss2json.com/v1/api.json?rss_url={target_rss}"
                try:
                    logger.warning(f"Network block detected. Bypassing ISP via RSS2JSON Proxy for {target_rss}...")
                    r = requests.get(proxy_url, timeout=15)
                    if r.status_code == 200:
                        data = r.json()
                        if data.get('status') == 'ok':
                            items = data.get('items', [])
                            max_days = self.config.get('max_days_back', 7)
                            max_posts = self.config.get('max_posts_per_run', 5)
                            pull_all = self.config.get('pull_all', False)
                            return self._process_rss2json_items(items, max_days, max_posts, pull_all)
                except Exception as e:
                    logger.error(f"Proxy fallback failed for {self.url}: {e}")
                
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
