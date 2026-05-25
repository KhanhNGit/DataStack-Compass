# src/crawler/kafka_adapter.py
import re
import requests
import logging
from bs4 import BeautifulSoup
from packaging.version import parse, InvalidVersion
from src.crawler.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

class KafkaAdapter(BaseAdapter):
    def parse_versions(self, main_html: str, target_version: str | None = None) -> tuple[str, str]:
        # Tìm tất cả các phiên bản (VD: 3.6.0) từ trang chủ Kafka
        version_pattern = re.compile(r'\b(2\.\d+\.\d+|3\.\d+\.\d+)\b')
        raw_versions = set(version_pattern.findall(main_html))
        
        valid_versions = []
        for v in raw_versions:
            try:
                valid_versions.append(parse(v))
            except InvalidVersion:
                continue
                
        valid_versions = sorted(list(set(valid_versions)), reverse=True)
        if len(valid_versions) < 2:
            raise ValueError("Not enough Kafka versions found.")
            
        return str(valid_versions[0]), str(valid_versions[1])

    def fetch_detail(self, main_html: str, version: str) -> str:
        # Lấy trực tiếp file Release Notes HTML từ Apache Archive
        notes_url = f"https://archive.apache.org/dist/kafka/{version}/RELEASE_NOTES.html"
        try:
            logger.info(f"Fetching Kafka release notes from {notes_url}")
            response = requests.get(notes_url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch Kafka notes for {version}: {e}")
            return ""

    def extract_notes(self, detail_html: str, target_version: str) -> dict[str, list[str]]:
        if not detail_html:
            return {"Notes": ["No release notes available or download failed."]}

        soup = BeautifulSoup(detail_html, 'html.parser')
        notes = {}
        current_category = "General Updates"
        notes[current_category] = []

        # File notes của Kafka thường dùng thẻ <h2> cho danh mục và <li> cho các issue (Bug, Sub-task...)
        for element in soup.find_all(['h2', 'li']):
            if element.name == 'h2':
                current_category = element.get_text(strip=True)
                if current_category not in notes:
                    notes[current_category] = []
            elif element.name == 'li':
                text = element.get_text(separator=" ", strip=True)
                if text:
                    notes[current_category].append(text)

        return {k: v for k, v in notes.items() if v}