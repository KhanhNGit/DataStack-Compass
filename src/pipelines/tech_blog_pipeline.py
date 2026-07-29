import json
import os
import sqlite3
import logging
import re
import requests
from bs4 import BeautifulSoup
from src.crawler.blogs.factory import BlogAdapterFactory
from src.ai.gemini_client import GeminiClient
from src.core.config_loader import load_env

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

DB_PATH = 'reports/blog/sql/blogs.db'
RAW_DIR = 'reports/blog/raw'
SUMMARY_DIR = 'reports/blog/summary'

def init_dirs():
    os.makedirs('reports/blog/sql', exist_ok=True)
    os.makedirs(RAW_DIR, exist_ok=True)
    os.makedirs(SUMMARY_DIR, exist_ok=True)

def init_db():
    init_dirs()
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS blogs (
            url TEXT PRIMARY KEY,
            source_name TEXT,
            title TEXT,
            author TEXT,
            publish_date TEXT,
            category TEXT,
            topics TEXT,
            raw_content TEXT,
            summary_content TEXT,
            keywords_tags TEXT,
            status TEXT
        )
    ''')
    conn.commit()
    return conn

def run_phase_1(config_path):
    logger.info("--- Starting Phase 1: Crawling ---")
    load_env()
    backup_json = os.environ.get('BACKUP_BLOG_JSON', 'false').lower() in ['true', '1', 'yes']
    
    with open(config_path, 'r', encoding='utf-8') as f:
        configs = json.load(f)
        
    conn = init_db()
    c = conn.cursor()
    
    c.execute("SELECT url FROM blogs")
    existing_urls = {row[0] for row in c.fetchall()}
    
    new_count = 0
    for config in configs:
        logger.info(f"Crawling: {config['name']}")
        try:
            adapter = BlogAdapterFactory.get_adapter(config)
            posts = adapter.fetch_new_posts()
            
            for post in posts:
                post['source_name'] = config['name']
                post['category'] = config.get('category', 'uncategorized')
                post['topics'] = config.get('topics', '')
                post['status'] = 'RAW'
                
                if post['url'] not in existing_urls:
                    existing_urls.add(post['url'])
                    
                    c.execute('''
                        INSERT OR REPLACE INTO blogs 
                        (url, source_name, title, author, publish_date, category, topics, raw_content, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (post['url'], post['source_name'], post['title'], post['author'], post['publish_date'], post['category'], post['topics'], post['raw_content'], 'RAW'))
                    new_count += 1
            
            if backup_json:
                source_safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', config['name']).strip('_').lower()
                c.execute("SELECT * FROM blogs WHERE source_name = ?", (config['name'],))
                cols = [column[0] for column in c.description]
                source_raw_data = [dict(zip(cols, row)) for row in c.fetchall()]
                
                raw_file_path = os.path.join(RAW_DIR, f"{source_safe_name}_raw.json")
                with open(raw_file_path, 'w', encoding='utf-8') as f:
                    json.dump(source_raw_data, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            logger.error(f"Error crawling {config['name']}: {e}")
            
    conn.commit()
    conn.close()
    
    logger.info(f"Phase 1 Complete. Fetched {new_count} new posts.")

def fetch_real_title(url: str) -> str:
    """Attempts to fetch the real title from the URL, using direct request or fallback proxy."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        html_content = response.text
    except Exception as e:
        logger.warning(f"Direct fetch failed for title of {url}: {e}. Trying via proxy...")
        try:
            import urllib.parse
            proxy_url = f"https://corsproxy.io/?{urllib.parse.quote(url)}"
            response = requests.get(proxy_url, timeout=15)
            response.raise_for_status()
            html_content = response.text
        except Exception as proxy_e:
            logger.error(f"Proxy fetch also failed for {url}: {proxy_e}")
            return None

    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        og_title = soup.find('meta', property='og:title')
        if og_title and og_title.get('content'):
            return og_title['content'].strip()
            
        if soup.title and soup.title.string:
            return soup.title.string.strip()
            
    return None

def run_phase_2():
    logger.info("--- Starting Phase 2: Summarization ---")
    load_env()
    backup_json = os.environ.get('BACKUP_BLOG_JSON', 'false').lower() in ['true', '1', 'yes']
    
    conn = init_db()
    c = conn.cursor()
    
    c.execute("SELECT url, title, raw_content, source_name FROM blogs WHERE status = 'RAW'")
    rows = c.fetchall()
    
    if not rows:
        logger.info("No new RAW posts to summarize.")
        conn.close()
        return
        
    gemini = GeminiClient()
    
    updated_sources = set()
    
    for row in rows:
        url, title, raw_content, source_name = row
        logger.info(f"Summarizing: {url}")
        
        # Cào lại Title gốc nếu có dấu hiệu bị cắt
        if title and ('…' in title or '...' in title):
            logger.info(f"Title appears truncated: '{title}'. Attempting to fetch real title...")
            real_title = fetch_real_title(url)
            if real_title:
                title = real_title
                logger.info(f"Fetched real title: '{title}'")
            else:
                logger.warning("Could not fetch real title, falling back to original.")
                
        try:
            summary_dict = gemini.summarize_blog_post(title, raw_content)
            summary_content = summary_dict.get('summary_content', '')
            
            # Chuẩn hóa tags: Đảm bảo mọi tag đều bắt đầu bằng #
            raw_tags = summary_dict.get('keywords_tags', [])
            cleaned_tags = [t if t.startswith('#') else f"#{t}" for t in raw_tags]
            keywords_tags = json.dumps(cleaned_tags)
            
            clean_title = summary_dict.get('clean_title', title)
            
            c.execute('''
                UPDATE blogs 
                SET title = ?, summary_content = ?, keywords_tags = ?, status = 'SUMMARIZED'
                WHERE url = ?
            ''', (clean_title, summary_content, keywords_tags, url))
            conn.commit()
            updated_sources.add(source_name)
        except Exception as e:
            logger.error(f"Failed to summarize {url}: {e}")
            
    if backup_json:
        for source_name in updated_sources:
            source_safe_name = re.sub(r'[^a-zA-Z0-9]+', '_', source_name).strip('_').lower()
            c.execute("SELECT * FROM blogs WHERE source_name = ? AND status = 'SUMMARIZED'", (source_name,))
            cols = [column[0] for column in c.description]
            all_summarized = [dict(zip(cols, row)) for row in c.fetchall()]
            
            summary_file_path = os.path.join(SUMMARY_DIR, f"{source_safe_name}_summary.json")
            with open(summary_file_path, 'w', encoding='utf-8') as f:
                json.dump(all_summarized, f, ensure_ascii=False, indent=2)
        
    conn.close()
    
    logger.info(f"Phase 2 Complete. Summarized {len(rows)} posts.")

def run(phase='all', config_path='configs/blogs_config.json'):
    if phase in ['1', 'all']:
        run_phase_1(config_path)
    if phase in ['2', 'all']:
        run_phase_2()
