# src/crawler/github_adapter.py
import os
import json
import re
import requests
import logging
from typing import Iterator
from packaging.version import parse, InvalidVersion
from src.crawler.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

class GitHubAdapter(BaseAdapter):
    """Generic adapter for scraping release notes via GitHub REST API."""

    def __init__(self, url: str):
        super().__init__(url)
        # Chuyển đổi URL repo thành URL API. VD: https://github.com/apache/kafka -> apache/kafka
        repo_path = self.url.replace("https://github.com/", "").strip("/")
        self.api_url = f"https://api.github.com/repos/{repo_path}/releases"
        
        self.headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.environ.get("GITHUB_TOKEN")
        
        if token and token.strip():
            self.headers["Authorization"] = f"token {token.strip()}"
            # Xác thực token bằng 1 request nhẹ nhàng theo đúng plan
            try:
                rate_limit_resp = requests.get("https://api.github.com/rate_limit", headers=self.headers, timeout=5)
                if rate_limit_resp.status_code == 401:
                    logger.warning("GITHUB_TOKEN is invalid. Falling back to Guest Mode. GitHub API is limited to 60 requests/hour.")
                    del self.headers["Authorization"]
            except Exception as e:
                logger.debug(f"Failed to check rate_limit: {e}")
        else:
            logger.warning("GITHUB_TOKEN is missing or empty. Operating as Guest. GitHub API is limited to 60 requests/hour.")

    def fetch_pages(self) -> Iterator[str]:
        try:
            logger.info(f"Fetching releases from GitHub API (Lazy Pagination): {self.api_url}")
            
            per_page = os.environ.get('GITHUB_PER_PAGE', '100')
            url = f"{self.api_url}?per_page={per_page}"
            page_count = 0
            
            while url:
                page_count += 1
                logger.debug(f"Fetching page {page_count}...")
                
                response = requests.get(url, headers=self.headers, timeout=15)
                # Cơ chế Fallback Khách Vãng Lai (Guest Mode)
                if response.status_code == 401 and "Authorization" in self.headers:
                    logger.warning("GITHUB_TOKEN is missing or invalid. Falling back to Guest Mode. GitHub API is limited to 60 requests/hour.")
                    del self.headers["Authorization"]
                    response = requests.get(url, headers=self.headers, timeout=15)
                
                response.raise_for_status()
                page_data = response.json()
                
                if not page_data:
                    break
                    
                # Lazy Evaluation: Nhả từng trang về cho Orchestrator
                yield json.dumps(page_data)
                
                # Tìm link trang tiếp theo (Pagination)
                url = None
                if "Link" in response.headers:
                    links = response.headers["Link"].split(",")
                    for link in links:
                        if 'rel="next"' in link:
                            start_idx = link.find("<")
                            end_idx = link.find(">")
                            if start_idx != -1 and end_idx != -1:
                                url = link[start_idx+1:end_idx]
                            break
                            
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API Error: {e}")
            raise

    def parse_versions(self, main_json: str) -> list[str]:
        releases = json.loads(main_json)
        valid_versions = []
        raw_tags = []

        for release in releases:
            if release.get("prerelease") or release.get("draft"):
                continue

            tag = release.get("tag_name", "")
            raw_tags.append(tag)

            semver_match = re.search(r'(\d+\.\d+\.\d+|\b\d{3}\b)', tag)
            if semver_match:
                clean_tag = semver_match.group(1)
                try:
                    # Validate if it's parseable
                    parse(clean_tag)
                    valid_versions.append(clean_tag)
                except InvalidVersion:
                    pass

        # Trường hợp 1: Moi được cấu trúc chuẩn
        if valid_versions:
            # Sort version descending using packaging.version
            return sorted(list(set(valid_versions)), key=parse, reverse=True)

        # Trường hợp 2: Fallback cho MinIO
        if raw_tags:
            logger.warning(f"No semantic versions found. Falling back to chronological tags (e.g., MinIO).")
            # GitHub API trả về chronological tags sẵn rồi, nhưng dùng unique preserving order
            seen = set()
            return [x for x in raw_tags if not (x in seen or seen.add(x))]

        return []

    def fetch_detail(self, main_json: str, version: str) -> str:
        releases = json.loads(main_json)
        for release in releases:
            tag = release.get("tag_name", "")
            # Sửa từ '==' thành 'in' để bao trùm các tag có tiền tố
            if version in tag: 
                return release.get("body", "")
        return ""

    def extract_notes(self, detail_markdown: str, target_version: str) -> dict[str, list[str]]:
        notes = {}
        if not detail_markdown:
            return {"General": ["No release notes body found. See external changelog."]}

        current_category = "General"
        notes[current_category] = []

        lines = detail_markdown.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
            
            # Nhận diện Header Markdown (##)
            if line.startswith('#'):
                current_category = re.sub(r'^#+\s*', '', line)
                if current_category not in notes: notes[current_category] = []
            # Nhận diện Header HTML (<h2>) của Kubernetes
            elif re.match(r'^<h[2-4].*>(.*)</h[2-4]>$', line, re.IGNORECASE):
                current_category = re.sub(r'<[^>]+>', '', line)
                if current_category not in notes: notes[current_category] = []
            # Nhận diện List item (- hoặc *)
            elif line.startswith('- ') or line.startswith('* '):
                notes[current_category].append(line[2:].strip())
            # Giữ lại các câu văn thường (của Keycloak, Superset)
            else:
                # Loại bỏ các đoạn mã code rác làm nặng json
                if not line.startswith('```'):
                    notes[current_category].append(line)

        return {k: v for k, v in notes.items() if v}