# src/crawler/factory.py
from src.crawler.base_adapter import BaseAdapter
from src.crawler.github_adapter import GitHubAdapter
from src.crawler.apache_jira_adapter import ApacheJiraAdapter
from src.crawler.spark_adapter import SparkAdapter
from src.crawler.kafka_adapter import KafkaAdapter

class AdapterFactory:
    """Factory to instantiate the correct crawler adapter based on source name."""
    
    @staticmethod
    def get_adapter(name: str, url: str) -> BaseAdapter:
        adapters = {
            'apache_spark': SparkAdapter,
            'apache_kafka': KafkaAdapter,
            'github': GitHubAdapter
        }
        
        # Nhóm 1: Nếu url chứa github.com, tự động dùng GitHubAdapter
        if 'github.com' in url and name.lower() not in adapters:
            return GitHubAdapter(url)
        
        # Nhóm 2: Chuẩn Apache Jira (Chỉ cần truyền vào Project Key, vd 'NIFI')
        if url.startswith('JIRA_'):
            project_key = url.replace('JIRA_', '')
            return ApacheJiraAdapter(project_key)

        adapter_class = adapters.get(name.lower())
        if not adapter_class:
            raise NotImplementedError(f"No adapter implemented for source: {name}")
            
        return adapter_class(url)