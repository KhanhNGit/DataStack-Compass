from .github_scraper import GithubScraper
from .jira_scraper import JiraScraper
from .default_scraper import DefaultScraper
from .base_scraper import BaseScraper

class ScraperFactory:
    @staticmethod
    def create(url: str) -> BaseScraper:
        if not url:
            return DefaultScraper("")
            
        url_lower = url.lower()
        if "github.com" in url_lower:
            return GithubScraper(url)
        elif "/jira/browse/" in url_lower:
            return JiraScraper(url)
        else:
            return DefaultScraper(url)
