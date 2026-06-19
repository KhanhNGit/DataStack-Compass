import os
import json
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def is_cached(name: str, version: str, output_dir="reports/json") -> bool:
    file_path = os.path.join(output_dir, f"{name}_v{version}.json")
    return os.path.exists(file_path)

def save_to_json(name: str, version: str, notes: dict, analysis: dict, output_dir="reports/json"):
    os.makedirs(output_dir, exist_ok=True)
    payload = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
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
