"""Google Sheets export module (optional)."""

import os
import json
import logging
import tempfile
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
        self._sheet = None

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

            self._sheet = self._client.open(self.sheet_name).sheet1
            logger.info(f"Opened Google Sheet: {self.sheet_name}")
        except ImportError:
            logger.error("gspread not installed. Install with: pip install gspread")
            raise
        except Exception as e:
            logger.error(f"Could not connect to Google Sheets: {e}")
            raise

    def export(self, records: list) -> int:
        """
        Append records to Google Sheet.
        
        Returns the number of rows appended.
        """
        if not records:
            return 0

        if self._sheet is None:
            self._connect()
            if self._sheet is None:
                return 0

        # Add header if sheet is empty
        try:
            existing = self._sheet.get_all_values()
            if not existing:
                self._sheet.append_row(CSV_COLUMNS, value_input_option="RAW")
        except Exception as e:
            logger.warning(f"Could not check sheet headers: {e}")

        # Append rows — use table_range="A1" to ensure data goes vertically
        rows = []
        for r in records:
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
            self._sheet.append_rows(
                rows,
                value_input_option="RAW",
                insert_data_option="INSERT_ROWS",
                table_range="A1"
            )
            logger.info(f"Appended {len(rows)} rows to Google Sheet")
            return len(rows)
        except Exception as e:
            logger.error(f"Error appending to Google Sheet: {e}")
            return 0


