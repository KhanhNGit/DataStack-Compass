import os
import glob
import json
import logging
from src.core.logger import setup_logger
from src.core.config_loader import load_env
from src.ai.gemini_client import GeminiClient
from src.crawler.scrapers.factory import ScraperFactory

# Khởi tạo logger
logger = logging.getLogger('AIPipeline')

def setup_directories():
    os.makedirs('reports/intermediate_features', exist_ok=True)
    os.makedirs('reports/summary_json', exist_ok=True)

def process_file(filepath: str, gemini: GeminiClient):
    filename = os.path.basename(filepath)
    summary_path = os.path.join('reports/summary_json', filename.replace('.json', '_summary.json'))
    intermediate_path = os.path.join('reports/intermediate_features', filename)
    
    # Bỏ qua nếu đã có bản tóm tắt
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
    
    # Phase 1: Semantic Filtering
    features = gemini.extract_features(notes)
    if not features:
        logger.warning(f"No new features found by Gemini for {filename}.")
        return
        
    # Dump intermediate debug file
    with open(intermediate_path, 'w', encoding='utf-8') as f:
        json.dump(features, f, indent=4, ensure_ascii=False)
    logger.info(f"Dumped {len(features)} intermediate features to {intermediate_path}")

    # Phase 2 & 3: Deep Crawling & Summarization
    final_features = []
    for feature in features:
        feature_name = feature.get('feature_name')
        link = feature.get('link')
        original_text = feature.get('original_text')
        
        logger.info(f"Processing Feature: {feature_name}")
        ai_summary = ""
        
        if link:
            # Giai đoạn 2: Crawl
            scraper = ScraperFactory.create(link)
            raw_content = scraper.scrape()
            
            if raw_content:
                # Giai đoạn 3: Tóm tắt
                ai_summary = gemini.summarize_feature(raw_content)
                
        final_features.append({
            "feature_name": feature_name,
            "original_text": original_text,
            "reference_link": link,
            "ai_summary": ai_summary
        })
        
    # Xây dựng báo cáo cuối cùng
    final_report = {
        "timestamp": data.get("timestamp"),
        "component": data.get("component"),
        "version": data.get("version"),
        "risk_level": data.get("risk_level"),
        "has_cve": data.get("has_cve"),
        "features": final_features
    }
    
    # Lưu file
    with open(summary_path, 'w', encoding='utf-8') as f:
        json.dump(final_report, f, indent=4, ensure_ascii=False)
    logger.info(f"Successfully saved AI summary to {summary_path}")

def main():
    load_env()
    setup_logger()
    setup_directories()
    
    gemini = GeminiClient()
    if not gemini.client:
        logger.error("Vui lòng cấu hình GEMINI_API_KEY trong .env để chạy luồng AI.")
        return

    # Lấy danh sách các file JSON thô trong thư mục reports/json
    raw_files = glob.glob('reports/json/*.json')
    if not raw_files:
        logger.info("Không tìm thấy file JSON nào trong reports/json/")
        return
        
    for filepath in raw_files:
        process_file(filepath, gemini)
        
    logger.info("Hoàn tất tiến trình AI Summarizer.")

if __name__ == "__main__":
    main()
