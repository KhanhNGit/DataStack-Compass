import os
import json
import sqlite3
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import email.utils
from jinja2 import Environment, FileSystemLoader

from src.core.logger import setup_logger
from src.core.config_loader import load_env

logger = logging.getLogger('BlogEmailPipeline')

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
    template = env.get_template('tech_blog_digest.html.j2')
    
    db_path = 'reports/blog/sql/blogs.db'
    if not os.path.exists(db_path):
        logger.warning(f"Database {db_path} does not exist. No blogs to send.")
        return

    conn = sqlite3.connect(db_path)
    c = conn.cursor()
    
    # Lấy tối đa 5 bài viết có status = 'SUMMARIZED'
    c.execute("SELECT * FROM blogs WHERE status = 'SUMMARIZED' LIMIT 5")
    rows = c.fetchall()
    
    if not rows:
        logger.info("No summarized posts found to send.")
        conn.close()
        return
        
    cols = [column[0] for column in c.description]
    posts = []
    
    for row in rows:
        post_dict = dict(zip(cols, row))
        # Parse keywords_tags
        raw_tags = post_dict.get('keywords_tags', '[]')
        try:
            post_dict['keywords_tags'] = json.loads(raw_tags)
        except json.JSONDecodeError:
            post_dict['keywords_tags'] = []
            
        # Parse timestamp to nice format if possible
        raw_date = post_dict.get('publish_date')
        if raw_date:
            try:
                # Try ISO 8601
                parsed_date = datetime.fromisoformat(raw_date.replace('Z', '+00:00'))
                post_dict['publish_date_formatted'] = parsed_date.strftime('%B %d, %Y')
            except Exception:
                post_dict['publish_date_formatted'] = raw_date
        else:
            post_dict['publish_date_formatted'] = "Unknown Date"
            
        posts.append(post_dict)
        
    logger.info(f"--- Preparing email digest for {len(posts)} blog posts ---")
    
    today = datetime.now()
    monday = today - timedelta(days=today.weekday())
    friday = monday + timedelta(days=4)
    date_range_str = f"{monday.strftime('%d/%m')} - {friday.strftime('%d/%m/%Y')}"
    
    html_content = template.render(date_range=date_range_str, posts=posts)
    
    subject = "[DataStack Compass] Tech Insight Weekly"
    
    if dry_run:
        dry_run_path = os.path.join('reports', 'blog', 'preview_blog_email.html')
        os.makedirs(os.path.dirname(dry_run_path), exist_ok=True)
        with open(dry_run_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        logger.info(f"[DRY-RUN] Saved preview HTML to {dry_run_path}")
    else:
        try:
            send_email(subject, html_content, mail_to, mail_cc, mail_bcc, smtp_config)
            logger.info(f"Successfully sent blog digest email to {mail_to} (CC: {mail_cc}, BCC: {mail_bcc})")
            
            # Update status to SENT
            urls_to_update = [p['url'] for p in posts]
            c.executemany("UPDATE blogs SET status = 'SENT' WHERE url = ?", [(url,) for url in urls_to_update])
            conn.commit()
            logger.info(f"Updated status to SENT for {len(urls_to_update)} posts.")
        except Exception as e:
            logger.error(f"Failed to send email digest: {e}")
            
    conn.close()
    logger.info("Blog Email Pipeline Completed.")
