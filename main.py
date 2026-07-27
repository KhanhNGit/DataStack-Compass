import argparse
from src.core.logger import setup_logger
from src.pipelines import oss_release_pipeline
from src.pipelines import ai_feature_pipeline
from src.pipelines import tech_blog_pipeline
from src.pipelines import email_notification_pipeline

def main():
    setup_logger()
    parser = argparse.ArgumentParser(description="DataStack Compass CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Command: run
    run_parser = subparsers.add_parser("run", help="Run a specific pipeline")
    run_subparsers = run_parser.add_subparsers(dest="pipeline", help="Pipeline to run")

    # Sub-command: run oss
    run_subparsers.add_parser("oss", help="Run OSS Release Analyzer Pipeline (Crawl release notes)")

    # Sub-command: run ai-summary
    run_subparsers.add_parser("ai-summary", help="Run AI Summarizer Pipeline (Deep crawl and feature summary)")

    # Sub-command: run blogs
    blog_parser = run_subparsers.add_parser("blogs", help="Run Tech Blog Crawler & Summarizer Pipeline")
    blog_parser.add_argument("--phase", choices=['1', '2', 'all'], default='all', help="Phase to run: 1 (Crawl), 2 (Summarize), all (Both)")
    blog_parser.add_argument("--config", default='configs/blogs_config.json', help="Path to blog config JSON")

    # Command: notify
    notify_parser = subparsers.add_parser("notify", help="Run Email Notification Pipeline")
    notify_parser.add_argument("--dry-run", action="store_true", help="Run in dry-run mode (render template only)")

    args = parser.parse_args()

    if args.command == "run":
        if args.pipeline == "oss":
            oss_release_pipeline.run()
        elif args.pipeline == "ai-summary":
            ai_feature_pipeline.run()
        elif args.pipeline == "blogs":
            tech_blog_pipeline.run(args.phase, args.config)
        else:
            run_parser.print_help()
    elif args.command == "notify":
        email_notification_pipeline.run(dry_run=args.dry_run)
    else:
        parser.print_help()

if __name__ == "__main__":
    main()