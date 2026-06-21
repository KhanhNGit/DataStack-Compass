import os
import re
import requests
import logging
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class GithubScraper(BaseScraper):
    def scrape(self) -> str:
        # Chuyển đổi từ URL trình duyệt sang URL API để lấy dữ liệu sạch
        # Ví dụ: https://github.com/minio/minio/pull/21569
        match = re.search(r'github\.com/([^/]+)/([^/]+)/(pull|issues)/(\d+)', self.url)
        if not match:
            logger.warning(f"Could not parse Github URL {self.url}. Falling back to default scraper.")
            from .default_scraper import DefaultScraper
            return DefaultScraper(self.url).scrape()
            
        owner, repo, type_, number = match.groups()
        # Github API dùng 'pulls' thay vì 'pull'
        api_type = 'pulls' if type_ == 'pull' else 'issues'
        api_url = f"https://api.github.com/repos/{owner}/{repo}/{api_type}/{number}"
        
        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token and token.strip() and token != "your_github_token_here":
            headers["Authorization"] = f"token {token.strip()}"
            
        try:
            logger.info(f"Scraping Github API: {api_url}")
            response = requests.get(api_url, headers=headers, timeout=15)
            response.raise_for_status()
            data = response.json()
            
            title = data.get('title', '')
            body = data.get('body', '')
            
            # Khác biệt giữa PR và Issue: PR có trường merged, state
            # Ta chỉ cần nội dung body mô tả tính năng
            return f"TITLE: {title}\nDESCRIPTION:\n{body}"
        except requests.exceptions.RequestException as e:
            logger.warning(f"Github API scrape failed for {self.url}: {e}, falling back to HTML scraping.")
            from .default_scraper import DefaultScraper
            return DefaultScraper(self.url).scrape()
