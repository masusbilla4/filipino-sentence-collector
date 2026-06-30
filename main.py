#!/usr/bin/env python3
"""
Filipino Sentence Collector - Main Entry Point

Collects sentences from:
  - Telegram bot input (primary)
  - RSS feeds (automated)
"""

import os
import sys
import logging
from dotenv import load_dotenv

# Set base directory to the script's location
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

load_dotenv(os.path.join(BASE_DIR, ".env"))

from utils.logger import setup_logger
from processors.sentence_splitter import split_sentences
from exporters.csv_exporter import export_to_csv
from collectors.telegram_collector import TelegramCollector
from scheduler import load_config, load_sources, create_scheduler, run_rss_collection

logger = setup_logger("filipino_collector", "INFO", "filipino_collector.log")


def process_records(records: list, settings: dict):
    """Process and export sentence records (called by all collectors)."""
    if not records:
        return

    output_dir = settings.get("output", {}).get("csv_dir", "output")
    daily = settings.get("output", {}).get("daily_files", True)
    min_words = settings.get("filters", {}).get("min_word_count", 5)

    csv_path = export_to_csv(records, output_dir, daily, min_words)
    logger.info(f"Records exported to: {csv_path}")

    gs_config = settings.get("output", {}).get("google_sheets", {})
    if gs_config.get("enabled", False):
        try:
            from exporters.sheets_exporter import GoogleSheetsExporter
            exporter = GoogleSheetsExporter(
                credentials_path=gs_config.get("credentials_path", ""),
                sheet_name=gs_config.get("sheet_name", "Filipino Sentences"),
            )
            exporter.export(records)
        except Exception as e:
            logger.error(f"Google Sheets export failed: {e}")


def main():
    """Main entry point."""
    settings = load_config("config/settings.yaml")
    sources = load_sources("config/sources.yaml")

    log_level = settings.get("logging", {}).get("level", "INFO")
    log_file = settings.get("logging", {}).get("file", None)
    global logger
    logger = setup_logger("filipino_collector", log_level, log_file)

    logger.info("=" * 60)
    logger.info("Filipino Sentence Collector - Starting")
    logger.info("=" * 60)

    # Run initial RSS collection
    logger.info("Running initial RSS collection...")
    run_rss_collection(settings, sources)

    # Start scheduler
    scheduler = create_scheduler(settings, sources)
    scheduler.start()
    logger.info("Scheduler started for periodic RSS collection")

    # Start Telegram bot (blocking - keeps app running)
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if telegram_token:
        def telegram_callback(records):
            process_records(records, settings)

        bot = TelegramCollector(
            token=telegram_token,
            process_callback=telegram_callback,
            split_func=split_sentences,
        )
        logger.info("Starting Telegram bot (blocking)...")
        bot.run()
    else:
        logger.warning("No TELEGRAM_BOT_TOKEN found. Running scheduler-only mode.")
        logger.info("Press Ctrl+C to exit.")
        try:
            import time
            while True:
                time.sleep(1)
        except (KeyboardInterrupt, SystemExit):
            scheduler.shutdown()
            logger.info("Shut down gracefully.")


if __name__ == "__main__":
    main()
