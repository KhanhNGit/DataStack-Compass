import os
import glob
import json
import logging
from src.core.logger import setup_logger
from src.core.config_loader import load_env
from src.ai.gemini_client import GeminiClient
from src.crawler.scrapers.factory import ScraperFactory

logger = logging.getLogger('AIPipeline')

def setup_directories():
    os.makedirs('reports/intermediate_features', exist_ok=True)
    os.makedirs('reports/summary_json', exist_ok=True)

def process_file(filepath: str, gemini: GeminiClient):
    filename = os.path.basename(filepath)
    summary_path = os.path.join('reports/summary_json', filename.replace('.json', '_summary.json'))
    
    if os.path.exists(summary_path):
        logger.info(f"Skipping {filename}, summary already exists.")
        return

    with open(filepath, 'r', encoding='utf-8') as f:
        data = json.load(f)

    notes = data.get("release_notes", {})
    if not notes:
        logger.warning(f"No release notes found in {filename}.")
        return

    logger.info(f"--- Processing {filename} ---")
    
    # Dùng One-Shot Summary thay vì chẻ nhỏ từng file
    summarized_data = gemini.summarize_release_one_shot(notes)
    if not summarized_data:
        logger.warning(f"Failed to generate one-shot summary for {filename}.")
        return
        
    final_report = {
        "timestamp": data.get("timestamp"),
        "component": data.get("component"),
        "version": data.get("version"),
        "risk_level": data.get("risk_level"),
        "has_cve": data.get("has_cve"),
        "advisor_summary": summarized_data.get("advisor_summary", {}),
        "cves": summarized_data.get("cves", []),
        "breaking_changes": summarized_data.get("breaking_changes", []),
        "bug_fixes": summarized_data.get("bug_fixes", []),
        "new_features": summarized_data.get("new_features", [])
    }
    
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=4, ensure_ascii=False)
    logger.info(f"Successfully saved AI one-shot summary to {summary_path}")

def run():
    load_env()
    setup_logger()
    setup_directories()
    
    gemini = GeminiClient()
    if not gemini.client:
        logger.error("Vui lòng cấu hình GEMINI_API_KEY trong .env để chạy luồng AI.")
        return

    raw_files = glob.glob('reports/json/*.json')
    if not raw_files:
        logger.info("Không tìm thấy file JSON nào trong reports/json/")
        return
        
    for filepath in raw_files:
        process_file(filepath, gemini)
        
    logger.info("Hoàn tất tiến trình AI Summarizer.")
