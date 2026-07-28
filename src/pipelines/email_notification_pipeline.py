import os
import glob
import json
import smtplib
import shutil
import logging
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from jinja2 import Environment, FileSystemLoader

from src.core.logger import setup_logger
from src.core.config_loader import load_env

logger = logging.getLogger('EmailPipeline')

def setup_directories():
    os.makedirs('reports/summary_json/sent', exist_ok=True)

def parse_emails(email_str):
    if not email_str:
        return []
    return [e.strip() for e in email_str.split(';') if e.strip()]

def send_email(subject, html_content, mail_to, mail_cc, mail_bcc, smtp_config):
    to_list = parse_emails(mail_to)
    cc_list = parse_emails(mail_cc)
    bcc_list = parse_emails(mail_bcc)

    if not to_list:
        raise ValueError("No valid 'TO' recipient addresses found.")

    all_recipients = to_list + cc_list + bcc_list

    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = smtp_config['user']
    msg['To'] = ", ".join(to_list)
    if cc_list:
        msg['Cc'] = ", ".join(cc_list)
        
    msg['Date'] = email.utils.formatdate(localtime=True)
    msg['Message-ID'] = email.utils.make_msgid(domain=smtp_config['user'].split('@')[-1])

    part2 = MIMEText(html_content, 'html')
    msg.attach(part2)

    port = int(smtp_config['port'])
    host = smtp_config['host']
    user = smtp_config.get('user')
    password = smtp_config.get('pass')

    if port == 465:
        server = smtplib.SMTP_SSL(host, port, timeout=60)
        if user and password:
            server.login(user, password)
    else:
        server = smtplib.SMTP(host, port, timeout=60)
        server.ehlo()
        if server.has_extn('STARTTLS'):
            server.starttls()
            server.ehlo()
        if user and password:
            server.login(user, password)
    
    try:
        refused = server.sendmail(smtp_config['user'], all_recipients, msg.as_string())
        if refused:
            logger.warning(f"Email sent, but some recipients were refused by server: {refused}")
    except smtplib.SMTPRecipientsRefused as e:
        server.quit()
        raise Exception(f"All recipients were refused. {e}")
    except Exception as e:
        server.quit()
        raise e
        
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
    mail_cc = os.environ.get("MAIL_CC", "")
    mail_bcc = os.environ.get("MAIL_BCC", "")

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
                send_email(subject, html_content, mail_to, mail_cc, mail_bcc, smtp_config)
                logger.info(f"Successfully sent email for {component_raw} v{version} to {mail_to} (CC: {mail_cc}, BCC: {mail_bcc})")
                
                # Move to sent
                sent_path = os.path.join('reports/summary_json/sent', filename)
                shutil.move(filepath, sent_path)
                logger.info(f"Moved {filename} to sent folder.")
            except Exception as e:
                logger.error(f"Failed to send email for {filename}: {e}")

    logger.info("Email Pipeline Completed.")
