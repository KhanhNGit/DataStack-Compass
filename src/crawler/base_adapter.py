# src/crawler/base_adapter.py
from abc import ABC, abstractmethod
import requests
import logging

logger = logging.getLogger(__name__)

class BaseAdapter(ABC):
    """Abstract base class for all OSS release crawlers."""
    
    def __init__(self, url: str):
        self.url = url

    def fetch_main(self) -> str:
        """Fetches the raw HTML from the main releases index URL."""
        try:
            logger.info(f"Fetching main page from {self.url}")
            response = requests.get(self.url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching {self.url}: {e}")
            raise

    @abstractmethod
    def parse_versions(self, main_html: str, target_version: str | None = None) -> tuple[str, str]:
        """Parses HTML to find the target (or latest) and previous semantic versions."""
        pass

    @abstractmethod
    def fetch_detail(self, main_html: str, version: str) -> str:
        """Finds the link for the specific version and fetches its detailed HTML."""
        pass

    @abstractmethod
    def extract_notes(self, detail_html: str, target_version: str) -> dict[str, list[str]]:
        """Extracts and categorizes release notes from the detailed HTML."""
        pass