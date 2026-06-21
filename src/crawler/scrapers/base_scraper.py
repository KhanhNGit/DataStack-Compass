from abc import ABC, abstractmethod

class BaseScraper(ABC):
    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def scrape(self) -> str:
        """Fetches the content from the URL and returns raw text for summarization."""
        pass
