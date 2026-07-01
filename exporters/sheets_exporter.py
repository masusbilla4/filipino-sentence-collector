"""Google Sheets export module (optional)."""

import os
import json
import logging
import tempfile
from datetime import datetime
from typing import Optional

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


class GoogleSheetsExporter:
    """Export sentence records to Google Sheets using gspread."""

    def __init__(self, credentials_path: str = "", sheet_name: str = "Filipino Sentences"):
        """
        Args:
            credentials_path: Path to Google service account JSON file.
            sheet_name: Name of the Google Sheet to write to.
        """
        self.credentials_path = credentials_path
        self.sheet_name = sheet_name
        self._client = None
        self._spreadsheet = None

    def _connect(self):
        """Establish connection to Google Sheets."""
        try:
            import gspread

            # Check for credentials in environment variable first (for cloud deployment)
            google_creds_json = os.environ.get("GOOGLE_CREDENTIALS_JSON", "")
            if google_creds_json:
                # Write the JSON string to a temp file for gspread
                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".json", delete=False, encoding="utf-8"
                ) as f:
                    f.write(google_creds_json)
                    temp_path = f.name
                self._client = gspread.service_account(filename=temp_path)
                os.unlink(temp_path)  # Clean up temp file
                logger.info("Connected to Google Sheets using GOOGLE_CREDENTIALS_JSON env var")
            elif self.credentials_path and os.path.exists(self.credentials_path):
                # Use file path (for local development)
                self._client = gspread.service_account(filename=self.credentials_path)
                logger.info(f"Connected to Google Sheets using {self.credentials_path}")
            else:
                logger.error(
                    "No Google credentials found. Set GOOGLE_CREDENTIALS_JSON env var "
                    "or provide credentials_path in settings.yaml"
                )
                return

            self._spreadsheet = self._client.open(self.sheet_name)
            logger.info(f"Opened Google Sheet: {self.sheet_name}")
        except ImportError:
            logger.error("gspread not installed. Install with: pip install gspread")
            raise
        except Exception as e:
            logger.error(f"Could not connect to Google Sheets: {e}")
            raise

    def _get_or_create_daily_sheet(self):
        """
        Get or create a worksheet (tab) for today's date.
        Returns the worksheet object.
        """
        today = datetime.now().strftime("%Y-%m-%d")

        # Try to get existing worksheet for today
        try:
            worksheet = self._spreadsheet.worksheet(today)
            logger.info(f"Using existing daily tab: {today}")
            return worksheet
        except Exception:
            # Worksheet doesn't exist, create it
            worksheet = self._spreadsheet.add_worksheet(title=today, rows=1, cols=len(CSV_COLUMNS))
            # Add headers
            worksheet.append_row(CSV_COLUMNS, value_input_option="RAW")
            logger.info(f"Created new daily tab: {today}")
            return worksheet

    def _get_existing_sentences(self, worksheet) -> set:
        """Get all existing sentences from a worksheet for deduplication."""
        try:
            all_values = worksheet.get_all_values()
            if not all_values:
                return set()

            # Skip header row, get column A (sentences)
            existing = set()
            for row in all_values[1:]:  # Skip header
                if row and row[0]:
                    existing.add(row[0].lower().strip())
            return existing
        except Exception as e:
            logger.warning(f"Could not read existing sentences for dedup: {e}")
            return set()

    def _remove_duplicates_from_sheet(self, worksheet):
        """Remove duplicate rows from a worksheet, keeping the first occurrence."""
        try:
            all_values = worksheet.get_all_values()
            if not all_values or len(all_values) <= 1:
                return 0

            data_rows = all_values[1:]

            seen = set()
            duplicate_indices = []

            for i, row in enumerate(data_rows):
                sentence = row[0].lower().strip() if row else ""
                if sentence in seen:
                    duplicate_indices.append(i + 2)  # +2: row 1 is header, index is 0-based
                else:
                    seen.add(sentence)

            if not duplicate_indices:
                return 0

            # Delete duplicate rows (from bottom to top to preserve indices)
            for row_num in sorted(duplicate_indices, reverse=True):
                worksheet.delete_rows(row_num)

            logger.info(f"Removed {len(duplicate_indices)} duplicate rows from sheet")
            return len(duplicate_indices)
        except Exception as e:
            logger.warning(f"Could not remove duplicates from sheet: {e}")
            return 0

    def export(self, records: list) -> int:
        """
        Append records to Google Sheet in a daily tab, skipping duplicates.
        
        Returns the number of rows appended.
        """
        if not records:
            return 0

        if self._spreadsheet is None:
            self._connect()
            if self._spreadsheet is None:
                return 0

        # Get or create today's daily tab
        worksheet = self._get_or_create_daily_sheet()

        # Get existing sentences for deduplication
        existing_sentences = self._get_existing_sentences(worksheet)

        # Filter out duplicates
        new_records = []
        for r in records:
            sentence = r.get("sentence", "").lower().strip()
            if sentence and sentence not in existing_sentences:
                new_records.append(r)
                existing_sentences.add(sentence)  # Prevent intra-batch duplicates

        if not new_records:
            logger.info("All records are duplicates in Google Sheet. Nothing new to append.")
            return 0

        # Append rows
        rows = []
        for r in new_records:
            rows.append([
                r.get("sentence", ""),
                r.get("word_count", ""),
                r.get("source_type", ""),
                r.get("source_title", ""),
                r.get("source_url_or_video_id", ""),
                r.get("timestamp", ""),
                r.get("date_extracted", ""),
            ])

        try:
            worksheet.append_rows(
                rows,
                value_input_option="RAW",
                insert_data_option="INSERT_ROWS",
                table_range="A1"
            )
            today = datetime.now().strftime("%Y-%m-%d")
            logger.info(f"Appended {len(rows)} new rows to tab '{today}' (skipped {len(records) - len(rows)} duplicates)")
            return len(rows)
        except Exception as e:
            logger.error(f"Error appending to Google Sheet: {e}")
            return 0

    def cleanup_duplicates(self) -> int:
        """
        Remove all duplicate rows from today's daily tab, keeping the first occurrence.
        """
        if self._spreadsheet is None:
            self._connect()
            if self._spreadsheet is None:
                return 0

        worksheet = self._get_or_create_daily_sheet()
        return self._remove_duplicates_from_sheet(worksheet)
