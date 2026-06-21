import re
import requests
import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class JiraScraper(BaseScraper):
    def scrape(self) -> str:
        # Chuyển URL trình duyệt sang API URL
        # Ví dụ: https://issues.apache.org/jira/browse/NIFI-1234
        match = re.search(r'(https://[^/]+/jira)/browse/([^/]+)', self.url)
        if not match:
            logger.warning(f"Could not parse Jira URL {self.url}. Falling back to default scraper.")
            from .default_scraper import DefaultScraper
            return DefaultScraper(self.url).scrape()
            
        base_jira, issue_key = match.groups()
        api_url = f"{base_jira}/rest/api/2/issue/{issue_key}"
        
        try:
            logger.info(f"Scraping Jira API: {api_url}")
            response = requests.get(api_url, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            fields = data.get('fields', {})
            summary = fields.get('summary', '')
            description = fields.get('description', '') or ''
            
            # Lấy thêm 3 comment gần nhất nổi bật
            comments_data = fields.get('comment', {}).get('comments', [])
            comments_text = ""
            if comments_data:
                # Lấy 3 comment cuối cùng (thường là kết luận)
                recent_comments = comments_data[-3:]
                comments_text = "\n---\n".join([c.get('body', '') for c in recent_comments])
            
            return f"TITLE: {summary}\nDESCRIPTION:\n{description}\nTOP COMMENTS:\n{comments_text}"
        except requests.exceptions.RequestException as e:
            logger.error(f"Jira API scrape failed for {self.url}: {e}")
            return ""
