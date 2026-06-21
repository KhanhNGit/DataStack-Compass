import requests
import logging
from bs4 import BeautifulSoup
from .base_scraper import BaseScraper

logger = logging.getLogger(__name__)

class DefaultScraper(BaseScraper):
    def scrape(self) -> str:
        try:
            logger.info(f"Scraping raw HTML: {self.url}")
            # Dùng headers giống trình duyệt để tránh bị chặn 403
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
            response = requests.get(self.url, headers=headers, timeout=15)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Xóa các thẻ rác không mang ngữ nghĩa
            for tag in soup(['script', 'style', 'header', 'footer', 'nav', 'aside', 'svg', 'button']):
                tag.decompose()
                
            main_content = soup.find('main') or soup.find('body') or soup
            return main_content.get_text(separator="\n", strip=True)
        except requests.exceptions.RequestException as e:
            logger.error(f"HTML scrape failed for {self.url}: {e}")
            return ""
