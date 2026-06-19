import os
import json
import sqlite3
import logging
from datetime import datetime, timezone

logger = logging.getLogger(__name__)

def init_sqlite_db(db_path="reports/sql/tracker.db"):
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS releases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            component TEXT,
            version TEXT,
            risk_level TEXT,
            has_cve BOOLEAN,
            release_notes TEXT
        )
    ''')
    conn.commit()
    return conn

def is_cached(name: str, version: str, db_path="reports/sql/tracker.db") -> bool:
    if not os.path.exists(db_path):
        return False
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM releases WHERE component=? AND version=? LIMIT 1", (name, version))
    row = cursor.fetchone()
    conn.close()
    return row is not None

def save_to_sqlite(name: str, version: str, notes: dict, analysis: dict, db_path="reports/sql/tracker.db"):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    timestamp = datetime.now(timezone.utc).isoformat()
    risk_level = analysis.get("risk_level", "Low")
    has_cve = "CRITICAL" in analysis.get("recommendation", "")
    notes_json = json.dumps(notes, ensure_ascii=False)
    
    cursor.execute('''
        INSERT INTO releases (timestamp, component, version, risk_level, has_cve, release_notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (timestamp, name, version, risk_level, has_cve, notes_json))
    
    conn.commit()
    conn.close()
    logger.info(f"Data ingested and saved to DB: {db_path} (Component: {name} v{version})")
