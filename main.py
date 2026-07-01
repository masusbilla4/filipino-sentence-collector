#!/usr/bin/env python3
"""
Filipino Sentence Collector - Main Entry Point

Collects sentences from:
  - Telegram bot input (primary)
  - RSS feeds (automated)

Designed for deployment on Render free tier (Web Service).
Runs a minimal HTTP server on $PORT (required by Render) while
the Telegram bot and scheduler run in the background.
"""

import os
import sys
import threading
import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from dotenv import load_dotenv

# Set timezone to Asia/Singapore (GMT+8) before any datetime calls
os.environ["TZ"] = "Asia/Singapore"
try:
    import time
    time.tzset()
except AttributeError:
    pass  # Windows doesn't support tzset()


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


class HealthCheckHandler(BaseHTTPRequestHandler):
    """Minimal HTTP handler so Render detects a web service on $PORT."""

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/plain")
        self.end_headers()
        self.wfile.write(b"Filipino Sentence Collector is running!")

    def log_message(self, format, *args):
        pass  # Suppress default access logs


def start_keep_alive():
    """Ping own URL every 10 minutes to prevent Render free tier spin-down."""
    import urllib.request
    import time

    # Wait 60 seconds for the service to be fully up
    time.sleep(60)

    while True:
        try:
            # Render sets RENDER_EXTERNAL_URL automatically
            url = os.environ.get("RENDER_EXTERNAL_URL", "")
            if url:
                if not url.startswith("http"):
                    url = f"https://{url}"
                urllib.request.urlopen(url, timeout=10)
                logger.info("Keep-alive ping sent successfully")
        except Exception as e:
            logger.debug(f"Keep-alive ping failed (will retry): {e}")
        time.sleep(600)  # 10 minutes


def start_web_server():
    """Start a minimal HTTP server on the PORT env var (required by Render)."""
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), HealthCheckHandler)
    logger.info(f"Web server listening on port {port}")
    server.serve_forever()



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


def run_telegram_bot(settings: dict):
    """Run the Telegram bot in a background thread."""
    telegram_token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not telegram_token:
        logger.warning("No TELEGRAM_BOT_TOKEN found. Skipping Telegram bot.")
        return

    def telegram_callback(records):
        process_records(records, settings)

    bot = TelegramCollector(
        token=telegram_token,
        process_callback=telegram_callback,
        split_func=split_sentences,
    )
    logger.info("Starting Telegram bot...")
    bot.run()


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

    # Start scheduler for periodic RSS collection
    scheduler = create_scheduler(settings, sources)
    scheduler.start()
    logger.info("Scheduler started for periodic RSS collection")

    # Start web server in a background thread (Render needs it on $PORT)
    web_thread = threading.Thread(target=start_web_server, daemon=True)
    web_thread.start()

    # Start keep-alive pinger in a background thread (prevents Render spin-down)
    keep_alive_thread = threading.Thread(target=start_keep_alive, daemon=True)
    keep_alive_thread.start()

    # Run Telegram bot in the MAIN thread (required by asyncio event loop)
    run_telegram_bot(settings)




if __name__ == "__main__":
    main()
