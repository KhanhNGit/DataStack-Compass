# src/crawler/base_adapter.py
from abc import ABC, abstractmethod
from typing import Iterator

class BaseAdapter(ABC):
    """Abstract base class for all OSS release crawlers."""

    def __init__(self, url: str):
        self.url = url

    @abstractmethod
    def fetch_pages(self) -> Iterator[str]:
        """Fetch all pages of release data from the API as a generator yielding JSON/HTML strings."""
        pass

    @abstractmethod
    def parse_versions(self, main_json: str) -> list[str]:
        """Parse raw HTML/JSON to extract a list of unique, valid version strings sorted descending."""
        pass

    @abstractmethod
    def fetch_detail(self, main_json: str, version: str) -> str:
        """Fetch the detailed Markdown or HTML release notes for a specific version."""
        pass

    @abstractmethod
    def extract_notes(self, detail_markdown: str, target_version: str) -> dict[str, list[str]]:
        """Extract and categorize notes into a structured dictionary."""
        pass