# src/crawler/spark_adapter.py
import re
import requests
import logging
from urllib.parse import urljoin
from bs4 import BeautifulSoup
from packaging.version import parse, InvalidVersion
from src.crawler.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

class SparkAdapter(BaseAdapter):
    """Concrete adapter for scraping Apache Spark release pages."""

    def parse_versions(self, main_html: str, target_version: str | None = None) -> tuple[str, str]:
        soup = BeautifulSoup(main_html, 'html.parser')
        text = soup.get_text()
        
        version_pattern = re.compile(r'\b(\d+[.-]\d+[.-]\d+)\b')
        raw_versions = set(version_pattern.findall(text))
        
        valid_versions = []
        for v in raw_versions:
            normalized_v = v.replace('-', '.')
            try:
                valid_versions.append(parse(normalized_v))
            except InvalidVersion:
                continue
                
        valid_versions = list(set(valid_versions))
        valid_versions = sorted(valid_versions, reverse=True)
        
        if len(valid_versions) < 2:
            raise ValueError("Could not detect at least two semantic versions on the page.")
            
        if target_version:
            try:
                normalized_target = target_version.replace('-', '.')
                target_v = parse(normalized_target)
            except InvalidVersion:
                raise ValueError(f"Invalid target version format: {target_version}")

            if target_v not in valid_versions:
                raise ValueError(f"Target version {target_version} not found on the page.")
            
            target_index = valid_versions.index(target_v)
            if target_index + 1 >= len(valid_versions):
                raise ValueError(f"No previous version found for target version {target_version}.")
                
            return str(valid_versions[target_index]), str(valid_versions[target_index + 1])

        return str(valid_versions[0]), str(valid_versions[1])

    def fetch_detail(self, main_html: str, version: str) -> str:
        """Tìm link chi tiết của phiên bản trên trang chủ và tải HTML về."""
        soup = BeautifulSoup(main_html, 'html.parser')
        detail_url = None
        
        # Spark thường dùng định dạng link: spark-release-4-1-0.html hoặc spark-release-4.1.0.html
        v_dash = version.replace('.', '-')
        v_dot = version
        
        for a in soup.find_all('a', href=True):
            href = a['href']
            text = a.get_text().lower()
            # Tìm link có chứa version và từ khóa 'release'
            if ('release' in href.lower() or 'release' in text) and (v_dash in href or v_dot in href or version in text):
                detail_url = urljoin(self.url, href)
                break
                
        if not detail_url:
            raise ValueError(f"Could not find detailed release notes link for version {version}")
            
        logger.info(f"Drilling down: Fetching detailed release notes from {detail_url}")
        try:
            response = requests.get(detail_url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            logger.error(f"Network error fetching detail page {detail_url}: {e}")
            raise

    def extract_notes(self, detail_html: str, target_version: str) -> dict[str, list]:
        soup = BeautifulSoup(detail_html, 'html.parser')
        notes = {}
        current_category = None

        content_div = soup.find('div', class_='col-md-9')
        if not content_div:
            content_div = soup.body if soup.body else soup

        for tag in content_div.find_all(['h3', 'h4', 'ul', 'table']):
            if tag.name == 'h3':
                cat_name = tag.get_text(strip=True)
                if cat_name.lower() not in ['credits', 'upgrading']:
                    current_category = cat_name
                    if current_category not in notes:
                        notes[current_category] = []
            
            elif tag.name == 'h4' and current_category:
                sub_cat = tag.get_text(strip=True)
                notes[current_category].append(f"🔹 {sub_cat}")
                
            elif tag.name == 'ul' and current_category:
                for li in tag.find_all('li', recursive=False):
                    for a in li.find_all('a'):
                        if a.has_attr('href'):
                            a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
                    text = li.get_text(separator=" | ", strip=True)
                    if text and text not in notes[current_category]:
                        notes[current_category].append(text)
                        
            elif tag.name == 'table' and current_category:
                # Bóc tách dữ liệu bảng thành mảng 2 chiều (List of Lists)
                table_data = []
                for tr in tag.find_all('tr'):
                    cols = []
                    for c in tr.find_all(['td', 'th']):
                        for a in c.find_all('a'):
                            if a.has_attr('href'):
                                a.replace_with(f"[{a.get_text(strip=True)}]({a['href']})")
                        cols.append(c.get_text(strip=True))
                    if len(cols) >= 2:
                        table_data.append(cols)
                
                # Lưu vào notes dưới dạng một object dict để Jinja2 dễ nhận diện
                if table_data:
                    notes[current_category].append({
                        "type": "table",
                        "data": table_data
                    })

        return {k: v for k, v in notes.items() if v}
        