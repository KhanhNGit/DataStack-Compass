# src/crawler/github_adapter.py
import os
import json
import re
import requests
import logging
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
        if token:
            self.headers["Authorization"] = f"token {token}"

    def fetch_main(self) -> str:
        try:
            logger.info(f"Fetching releases from GitHub API: {self.api_url}")
            # Cần đảm bảo hệ thống có cấu hình proxy môi trường nếu chạy trong private DC
            response = requests.get(self.api_url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text # Trả về chuỗi JSON
        except requests.exceptions.RequestException as e:
            logger.error(f"GitHub API Error: {e}")
            raise

    def parse_versions(self, main_json: str, target_version: str | None = None) -> tuple[str, str]:
        releases = json.loads(main_json)
        valid_versions = []
        raw_tags = [] # Lưu trữ lại các tag thô dành cho MinIO

        for release in releases:
            if release.get("prerelease") or release.get("draft"):
                continue

            tag = release.get("tag_name", "")
            raw_tags.append(tag) # GitHub API luôn trả về list được sort sẵn từ mới -> cũ

            # Dùng Regex để moi cấu trúc SemVer (VD: "apache-iceberg-1.4.3" -> "1.4.3")
            semver_match = re.search(r'(\d+\.\d+\.\d+|\b\d{3}\b)', tag)
            if semver_match:
                clean_tag = semver_match.group(1)
                try:
                    valid_versions.append(parse(clean_tag))
                except InvalidVersion:
                    pass

        # Trường hợp 1: Moi được cấu trúc chuẩn (Iceberg, Hudi, Vault,...)
        if len(valid_versions) >= 2:
            valid_versions = sorted(list(set(valid_versions)), reverse=True)
            return str(valid_versions[0]), str(valid_versions[1])

        # Trường hợp 2: Fallback cho MinIO (Không dùng X.Y.Z)
        if len(raw_tags) >= 2:
            logger.warning(f"No semantic versions found. Falling back to chronological tags (e.g., MinIO).")
            return raw_tags[0], raw_tags[1]

        raise ValueError("Not enough stable releases found in repository.")

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