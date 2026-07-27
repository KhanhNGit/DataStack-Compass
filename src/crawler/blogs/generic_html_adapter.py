import requests
from bs4 import BeautifulSoup
import trafilatura
from datetime import datetime
from typing import List, Dict, Any
from src.crawler.blogs.base_blog_adapter import BaseBlogAdapter
import logging

logger = logging.getLogger(__name__)

class GenericHtmlAdapter(BaseBlogAdapter):
    def fetch_new_posts(self) -> List[Dict[str, Any]]:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        try:
            r = requests.get(self.url, headers=headers, timeout=15)
            soup = BeautifulSoup(r.text, 'html.parser')
        except Exception as e:
            logger.error(f"Failed to fetch homepage for {self.url}: {e}")
            return []
            
        links = []
        for a in soup.find_all('a', href=True):
            href = a['href']
            if href.startswith('/'):
                href = self.url.rstrip('/') + href
            if href.startswith(self.url) and len(href) > len(self.url) + 10:
                if href not in links:
                    links.append(href)
                    
        max_posts = self.config.get('max_posts_per_run', 5)
        pull_all = self.config.get('pull_all', False)
        
        posts = []
        for link in links:
            if not pull_all and max_posts and len(posts) >= max_posts:
                break
                
            try:
                downloaded = trafilatura.fetch_url(link)
                if not downloaded:
                    continue
                content = trafilatura.extract(downloaded)
                if not content or len(content) < 500: # Skip non-articles or very short stubs
                    continue
                    
                metadata = trafilatura.extract_metadata(downloaded)
                posts.append({
                    'url': link,
                    'title': metadata.title if metadata and metadata.title else '',
                    'author': metadata.author if metadata and metadata.author else '',
                    'publish_date': metadata.date if metadata and metadata.date else datetime.now().isoformat(),
                    'raw_content': content
                })
            except Exception as e:
                logger.debug(f"Failed to extract {link}: {e}")
                
        return posts
