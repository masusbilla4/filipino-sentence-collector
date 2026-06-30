"""Scheduler for automated RSS collection."""

import os
import logging
import yaml
from apscheduler.schedulers.background import BackgroundScheduler

from collectors.rss_collector import collect_all_rss, process_rss_to_sentences
from processors.sentence_splitter import split_sentences
from exporters.csv_exporter import export_to_csv

logger = logging.getLogger("filipino_collector")


def load_config(config_path: str = "config/settings.yaml") -> dict:
    """Load YAML configuration file."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_sources(config_path: str = "config/sources.yaml") -> dict:
    """Load sources configuration."""
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def export_to_sheets(records: list, settings: dict):
    """Export records to Google Sheets if enabled."""
    gs_config = settings.get("output", {}).get("google_sheets", {})
    if not gs_config.get("enabled", False):
        return

    try:
        from exporters.sheets_exporter import GoogleSheetsExporter
        exporter = GoogleSheetsExporter(
            credentials_path=gs_config.get("credentials_path", ""),
            sheet_name=gs_config.get("sheet_name", "Filipino Sentences"),
        )
        exporter.export(records)
    except Exception as e:
        logger.error(f"Google Sheets export failed: {e}")


def run_rss_collection(settings: dict, sources: dict):
    """Run RSS collection and processing pipeline."""
    logger.info("=== Starting scheduled RSS collection ===")
    try:
        rss_sources = sources.get("rss", [])
        entries = collect_all_rss(rss_sources)
        records = process_rss_to_sentences(entries, split_sentences)

        output_dir = settings.get("output", {}).get("csv_dir", "output")
        daily = settings.get("output", {}).get("daily_files", True)
        min_words = settings.get("filters", {}).get("min_word_count", 5)

        # Export to CSV
        export_to_csv(records, output_dir, daily, min_words)

        # Export to Google Sheets
        if records:
            export_to_sheets(records, settings)

        logger.info("=== RSS collection complete ===")
    except Exception as e:
        logger.error(f"RSS collection failed: {e}")


def create_scheduler(settings: dict, sources: dict) -> BackgroundScheduler:
    """Create and configure the APScheduler."""
    scheduler = BackgroundScheduler()

    rss_interval = settings.get("schedule", {}).get("rss_interval_minutes", 60)

    scheduler.add_job(
        run_rss_collection,
        "interval",
        minutes=rss_interval,
        args=[settings, sources],
        id="rss_collection",
        name="RSS Feed Collection",
    )

    logger.info(f"Scheduler configured: RSS every {rss_interval}min")
    return scheduler
