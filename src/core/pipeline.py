import time
import json
import logging
import requests
from src.core.version_filter import resolve_target_versions
from src.crawler.factory import AdapterFactory
from src.storage.json_storage import save_to_json, is_cached as is_cached_json
from src.storage.sqlite_storage import save_to_sqlite, is_cached as is_cached_sqlite

logger = logging.getLogger(__name__)

def fetch_and_filter_versions(adapter, name, version_constraint):
    all_versions = []
    target_versions = []
    aggregated_data = []
    
    for page_data in adapter.fetch_pages():
        page_versions = adapter.parse_versions(page_data)
        if not page_versions:
            break
            
        aggregated_data.extend(json.loads(page_data))
        all_versions.extend(page_versions)
        
        page_targets, should_stop = resolve_target_versions(page_versions, version_constraint)
        target_versions.extend(page_targets)
        
        if should_stop:
            logger.info("Lazy Evaluation: Early Stop condition met. Halting pagination.")
            break
            
    if not all_versions:
        logger.warning(f"No valid versions found for {name}")
        return [], [], None
        
    if not target_versions:
        logger.warning(f"No versions matched the constraint for {name}")
        return all_versions, [], None
        
    main_data = json.dumps(aggregated_data)
    logger.info(f"Detected {len(target_versions)} versions to crawl for {name}.")
    
    return all_versions, target_versions, main_data

def process_target_version(name, target_ver, prev_ver, main_data, adapter, analyzer, output_format):
    if output_format == 'sqlite' and is_cached_sqlite(name, target_ver):
        logger.info(f"[CACHED] {name} v{target_ver} already exists in DB. Skipping.")
        return
    elif output_format == 'json' and is_cached_json(name, target_ver):
        logger.info(f"[CACHED] {name} v{target_ver} already exists in JSON. Skipping.")
        return
        
    try:
        detail_data = adapter.fetch_detail(main_data, target_ver)
        notes = adapter.extract_notes(detail_data, target_ver)
        analysis_results = analyzer.analyze(target_ver, prev_ver, notes)

        if output_format == 'sqlite':
            save_to_sqlite(name, target_ver, notes, analysis_results)
        else:
            save_to_json(name, target_ver, notes, analysis_results)
        
        logger.info(f"Successfully processed {name} v{target_ver}")
    except requests.exceptions.RequestException as e:
        logger.error(f"Network error fetching detail for {name} v{target_ver}: {e}")
        raise # Ném lỗi lên process_source để retry
    except Exception as e:
        logger.error(f"Failed to process {name} v{target_ver}: {e}", exc_info=True)

def process_source(source, analyzer, output_format, crawl_delay) -> bool:
    name = source.get('name')
    url = source.get('url')
    version_constraint = source.get('version_constraint')
    
    logger.info(f"--- Processing Source: {name} ---")
    if version_constraint:
        logger.info(f"Version Constraint: {version_constraint}")
        
    try:
        adapter = AdapterFactory.get_adapter(name, url)
        all_versions, target_versions, main_data = fetch_and_filter_versions(adapter, name, version_constraint)
        
        if not target_versions:
            return True
            
        for target_ver in target_versions:
            try:
                idx = all_versions.index(target_ver)
                prev_ver = all_versions[idx + 1] if idx + 1 < len(all_versions) else target_ver
            except ValueError:
                prev_ver = target_ver
                
            process_target_version(name, target_ver, prev_ver, main_data, adapter, analyzer, output_format)
            time.sleep(crawl_delay)
            
        return True
    except requests.exceptions.RequestException as e:
        logger.error(f"Network timeout/error for source '{name}': {e}")
        return False # Báo cho main.py biết cần retry
    except Exception as e:
        logger.error(f"Pipeline failed for source '{name}': {e}", exc_info=True)
        return True # Lỗi logic/cấu hình, không cần retry
