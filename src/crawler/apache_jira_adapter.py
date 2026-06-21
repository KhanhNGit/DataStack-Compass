import requests
import logging
from typing import Iterator
from packaging.version import parse, InvalidVersion
from src.crawler.base_adapter import BaseAdapter

logger = logging.getLogger(__name__)

class ApacheJiraAdapter(BaseAdapter):
    """Adapter lấy dữ liệu tự động từ hệ thống Apache Jira cho tất cả các dự án Apache"""
    
    def __init__(self, project_key: str):
        # project_key ví dụ: NIFI, HBASE, HADOOP, FLINK, KAFKA
        self.project_key = project_key.upper()
        self.base_api = "https://issues.apache.org/jira/rest/api/2"

    def fetch_pages(self) -> Iterator[str]:
        # Lấy danh sách toàn bộ versions của project
        url = f"{self.base_api}/project/{self.project_key}/versions"
        response = requests.get(url, timeout=15)
        response.raise_for_status()
        yield response.text # Trả về list JSON các versions

    def parse_versions(self, main_json: str) -> list[str]:
        import json
        from packaging.version import parse, InvalidVersion
        
        versions_data = json.loads(main_json)
        version_map = {}
        
        for v in versions_data:
            if v.get('released') and not v.get('archived'):
                original_name = v.get('name', '')
                try:
                    parsed_v = parse(original_name)
                    version_map[parsed_v] = original_name
                except InvalidVersion:
                    continue
                    
        sorted_parsed_versions = sorted(version_map.keys(), reverse=True)
        return [version_map[v] for v in sorted_parsed_versions]

    def fetch_detail(self, main_json: str, version: str) -> str:
        # Trả về version thay vì HTML chi tiết. Logic cào issue nằm ở hàm extract_notes.
        return version

    def extract_notes(self, version: str, target_version: str) -> dict[str, list[str]]:
        # Gọi API Jira Query (JQL) để lấy các issue đã được fix trong bản Release này
        jql = f'project = {self.project_key} AND fixVersion = "{version}" AND status in (Resolved, Closed)'
        url = f"{self.base_api}/search?jql={jql}&maxResults=200&fields=issuetype,summary"
        
        response = requests.get(url, timeout=15)
        issues = response.json().get('issues', [])
        
        notes = {}
        for issue in issues:
            fields = issue.get('fields', {})
            issue_type = fields.get('issuetype', {}).get('name', 'Others')
            summary = fields.get('summary', '')
            issue_key = issue.get('key')
            
            if issue_type not in notes:
                notes[issue_type] = []
            # Nối link ticket Jira cho SRE dễ tra cứu
            jira_url = f"https://issues.apache.org/jira/browse/{issue_key}"
            notes[issue_type].append(f"[{issue_key}]({jira_url}) - {summary}")
            
        return notes