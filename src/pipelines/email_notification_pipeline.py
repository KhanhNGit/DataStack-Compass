import os
import glob
import json
import smtplib
import shutil
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader

from src.core.logger import setup_logger
from src.core.config_loader import load_env

logger = logging.getLogger('EmailPipeline')

def setup_directories():
    os.makedirs('reports/summary_json/sent', exist_ok=True)

def send_email(subject, html_content, to_email, smtp_config):
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_config['user']
    msg['To'] = to_email

    part2 = MIMEText(html_content, 'html')
    msg.attach(part2)

    server = smtplib.SMTP(smtp_config['host'], int(smtp_config['port']))
    server.starttls()
    server.login(smtp_config['user'], smtp_config['pass'])
    server.sendmail(smtp_config['user'], to_email, msg.as_string())
    server.quit()

def run(dry_run=False):
    load_env()
    setup_logger()
    setup_directories()
    
    smtp_host = os.environ.get("SMTP_HOST")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    smtp_user = os.environ.get("SMTP_USER")
    smtp_pass = os.environ.get("SMTP_PASS")
    mail_to = os.environ.get("MAIL_TO")

    if not dry_run and not all([smtp_host, smtp_user, smtp_pass, mail_to]):
        logger.error("Missing SMTP configuration in .env. Please configure SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASS, MAIL_TO.")
        return

    smtp_config = {
        'host': smtp_host,
        'port': smtp_port,
        'user': smtp_user,
        'pass': smtp_pass
    }

    env = Environment(loader=FileSystemLoader('templates'))
    template = env.get_template('release_note.html.j2')

    files = glob.glob('reports/summary_json/*.json')
    if not files:
        logger.info("No summary JSON files found to send.")
        return

    for filepath in files:
        filename = os.path.basename(filepath)
        logger.info(f"--- Preparing email for {filename} ---")
        
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)

        component_raw = data.get("component", "Unknown")
        version = data.get("version", "latest")
        
        # Format timestamp
        raw_ts = data.get("timestamp")
        if raw_ts:
            try:
                # Handle ISO 8601
                parsed_date = datetime.fromisoformat(raw_ts.replace('Z', '+00:00'))
                data['timestamp'] = parsed_date.strftime('%d/%m/%Y')
            except Exception as e:
                logger.warning(f"Failed to parse timestamp {raw_ts}: {e}")
                data['timestamp'] = raw_ts

        # Render HTML
        html_content = template.render(**data)
        
        subject = f"[DataStack Compass] Release Notification: {component_raw.replace('_', ' ').upper()} - v{version}"

        if dry_run:
            dry_run_path = os.path.join('reports/summary_json', f"preview_{filename.replace('.json', '.html')}")
            with open(dry_run_path, 'w', encoding='utf-8') as f:
                f.write(html_content)
            logger.info(f"[DRY-RUN] Saved preview HTML to {dry_run_path}")
        else:
            try:
                send_email(subject, html_content, mail_to, smtp_config)
                logger.info(f"Successfully sent email for {component_raw} v{version} to {mail_to}")
                
                # Move to sent
                sent_path = os.path.join('reports/summary_json/sent', filename)
                shutil.move(filepath, sent_path)
                logger.info(f"Moved {filename} to sent folder.")
            except Exception as e:
                logger.error(f"Failed to send email for {filename}: {e}")

    logger.info("Email Pipeline Completed.")
