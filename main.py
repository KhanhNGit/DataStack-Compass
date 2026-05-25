# main.py
import os
import json
import yaml
import logging
from datetime import datetime
from src.crawler.factory import AdapterFactory
from src.analyzer.release_analyzer import ReleaseAnalyzer
from src.reporter.pdf_generator import PDFReporter

# Configure production-grade logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# TẮT LOG DEBUG RÁC TỪ CÁC THƯ VIỆN BÊN THỨ 3
logging.getLogger('fontTools').setLevel(logging.INFO)
logging.getLogger('weasyprint').setLevel(logging.INFO)

def load_config(config_path: str) -> dict:
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    with open(config_path, 'r') as f:
        return yaml.safe_load(f)
    
def save_to_json(name: str, version: str, notes: dict, analysis: dict, output_dir="reports"):
    os.makedirs(output_dir, exist_ok=True)
    payload = {
        "timestamp": datetime.utcnow().isoformat(),
        "component": name,
        "version": version,
        "risk_level": analysis.get("risk_level", "Low"),
        "has_cve": "CRITICAL" in analysis.get("recommendation", ""),
        "release_notes": notes
    }
    file_path = os.path.join(output_dir, f"{name}_v{version}.json")
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=4, ensure_ascii=False)
    logger.info(f"Data ingested and saved to {file_path}")

def main():
    logger.info("Starting OSS Release Analyzer Pipeline...")
    # os.makedirs('reports', exist_ok=True)
    
    try:
        config = load_config('config.yaml')
    except Exception as e:
        logger.critical(f"Failed to load configuration: {e}")
        return

    analyzer = ReleaseAnalyzer()
    # reporter = PDFReporter()

    for source in config.get('sources', []):
        name = source.get('name')
        url = source.get('url')
        target_version = source.get('target_version')
        
        logger.info(f"--- Processing Source: {name} ---")
        if target_version:
            logger.info(f"Target version specified: {target_version}")
            
        try:
            adapter = AdapterFactory.get_adapter(name, url)
            
            # 1. Tải trang Index (Danh sách phiên bản)
            main_data = adapter.fetch_main()
            
            # 2. Phân tích để lấy phiên bản cần tìm
            latest_ver, prev_ver = adapter.parse_versions(main_data, target_version)
            logger.info(f"Detected Versions -> Target/Latest: {latest_ver}, Previous: {prev_ver}")
            
            # 3. Drill-down: Tìm link và tải trang HTML chi tiết của phiên bản đó
            detail_data = adapter.fetch_detail(main_data, latest_ver)
            
            # 4. Bóc tách nội dung từ trang chi tiết
            notes = adapter.extract_notes(detail_data, latest_ver)
            
            # 5. Phân tích rủi ro & Xuất báo cáo
            analysis_results = analyzer.analyze(latest_ver, prev_ver, notes)
            
            # output_file = os.path.join('reports', f"{name}_{latest_ver}_release_report.pdf")
            # reporter.generate(
            #     source_name=name,
            #     url=url,
            #     latest=latest_ver,
            #     previous=prev_ver,
            #     notes=notes,
            #     analysis=analysis_results,
            #     output_path=output_file
            # )

            save_to_json(name, latest_ver, notes, analysis_results)
            
            logger.info(f"Successfully completed pipeline for {name} (v{latest_ver}).")
            
        except Exception as e:
            logger.error(f"Pipeline failed for source '{name}': {e}", exc_info=True)

if __name__ == "__main__":
    main()