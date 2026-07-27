from abc import ABC, abstractmethod
from typing import List, Dict, Any

class BaseBlogAdapter(ABC):
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.url = config['url']
        self.name = config['name']

    @abstractmethod
    def fetch_new_posts(self) -> List[Dict[str, Any]]:
        """
        Fetch a list of new posts based on config limits.
        Returns a list of dicts with at least:
        - url: str
        - title: str
        - author: str
        - publish_date: str
        - raw_content: str
        """
        pass
