# main.py
import os
import time
from src.core.logger import setup_logger
from src.core.config_loader import load_config, load_env
from src.core.version_filter import resolve_target_versions
from src.crawler.factory import AdapterFactory
from src.analyzer.release_analyzer import ReleaseAnalyzer
from src.storage.json_storage import save_to_json, is_cached as is_cached_json
from src.storage.sqlite_storage import init_sqlite_db, save_to_sqlite, is_cached as is_cached_sqlite

logger = setup_logger()

from src.core.pipeline import process_source

def main():
    logger.info("Starting OSS Release Analyzer Pipeline (Bulk Crawl Enabled)...")
    
    load_env()
    output_format = os.environ.get('STORAGE_BACKEND', 'json').lower()
    crawl_delay = float(os.environ.get('CRAWL_DELAY', 1.5))
    
    if output_format == 'sqlite':
        init_sqlite_db()
        logger.info("Output mode set to SQLite. Database: reports/sql/tracker.db")
    else:
        logger.info("Output mode set to JSON. Directory: reports/json/")
    
    try:
        config = load_config()
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        return

    analyzer = ReleaseAnalyzer()

    sources_queue = config.get('sources', [])
    for s in sources_queue:
        s['retry_count'] = 0
        
    max_retries = int(os.environ.get('MAX_RETRIES', 3))

    while sources_queue:
        source = sources_queue.pop(0)
        success = process_source(source, analyzer, output_format, crawl_delay)
        
        if not success:
            if source['retry_count'] < max_retries:
                source['retry_count'] += 1
                logger.warning(f"Pushing '{source.get('name')}' to the end of the queue for retry ({source['retry_count']}/{max_retries})")
                sources_queue.append(source)
            else:
                logger.error(f"Max retries reached for '{source.get('name')}'. Abandoning source.")

if __name__ == "__main__":
    main()