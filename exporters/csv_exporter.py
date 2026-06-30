"""CSV export module with daily file support."""

import os
import logging
from datetime import datetime
from typing import List

import pandas as pd

logger = logging.getLogger("filipino_collector")

CSV_COLUMNS = [
    "sentence",
    "word_count",
    "source_type",
    "source_title",
    "source_url_or_video_id",
    "timestamp",
    "date_extracted",
]


def get_csv_path(output_dir: str, daily: bool = True) -> str:
    """Generate the CSV file path, optionally with daily date suffix."""
    os.makedirs(output_dir, exist_ok=True)
    if daily:
        date_str = datetime.now().strftime("%Y-%m-%d")
        filename = f"filipino_sentences_{date_str}.csv"
    else:
        filename = "filipino_sentences.csv"
    return os.path.join(output_dir, filename)


def export_to_csv(
    records: List[dict],
    output_dir: str = "output",
    daily: bool = True,
    min_word_count: int = 5,
) -> str:
    """
    Export sentence records to CSV in append mode.

    Args:
        records: List of sentence record dicts.
        output_dir: Directory for CSV files.
        daily: If True, create separate CSV per day.
        min_word_count: Minimum word count filter.

    Returns:
        Path to the CSV file written.
    """
    if not records:
        logger.info("No records to export.")
        return ""

    # Filter by minimum word count
    filtered = [r for r in records if r.get("word_count", 0) >= min_word_count]

    if not filtered:
        logger.info(f"No records with >= {min_word_count} words after filtering.")
        return ""

    csv_path = get_csv_path(output_dir, daily)

    # Load existing for dedup
    existing_sentences = set()
    if os.path.exists(csv_path):
        try:
            existing_df = pd.read_csv(csv_path)
            if "sentence" in existing_df.columns:
                existing_sentences = set(
                    s.lower().strip() for s in existing_df["sentence"].dropna()
                )
        except Exception as e:
            logger.warning(f"Could not read existing CSV for dedup: {e}")

    # Deduplicate against existing
    new_records = []
    for r in filtered:
        if r["sentence"].lower().strip() not in existing_sentences:
            new_records.append(r)
            existing_sentences.add(r["sentence"].lower().strip())

    if not new_records:
        logger.info("All records are duplicates. Nothing new to write.")
        return csv_path

    # Create DataFrame and append
    df = pd.DataFrame(new_records, columns=CSV_COLUMNS)

    write_header = not os.path.exists(csv_path)
    df.to_csv(csv_path, mode="a", header=write_header, index=False, encoding="utf-8")

    logger.info(f"Exported {len(new_records)} new records to {csv_path}")
    return csv_path
