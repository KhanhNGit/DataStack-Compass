import logging
from src.core.logger import setup_logger
from src.core.config_loader import load_env
from src.ai.gemini_client import GeminiClient
from src.pipelines.ai_feature_pipeline import process_file, setup_directories
import os

if __name__ == "__main__":
    load_env()
    setup_logger()
    setup_directories()
    
    gemini = GeminiClient()
    
    # Remove existing summary if exists to force generation
    summary_path = 'reports/summary_json/apache_kafka_v4.3.1_summary.json'
    if os.path.exists(summary_path):
        os.remove(summary_path)

    process_file('reports/json/apache_kafka_v4.3.1.json', gemini)
    print("Done generating Kafka summary.")
