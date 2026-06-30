"""Google Sheets export module (optional)."""

import logging
from typing import Any, List

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

    def __init__(self, credentials_path: str, sheet_name: str):
        """
        Args:
            credentials_path: Path to Google service account JSON.
            sheet_name: Name of the Google Sheet to write to.
        """
        self.credentials_path = credentials_path
        self.sheet_name = sheet_name
        self._client: Any = None
        self._sheet: Any = None

    def _connect(self):
        """Establish connection to Google Sheets."""
        try:
            import gspread
            self._client = gspread.service_account(filename=self.credentials_path)
            self._sheet = self._client.open(self.sheet_name).sheet1
            logger.info(f"Connected to Google Sheet: {self.sheet_name}")
        except ImportError:
            logger.error("gspread not installed. Install with: pip install gspread")
            raise
        except Exception as e:
            logger.error(f"Could not connect to Google Sheets: {e}")
            raise

    def export(self, records: List[dict]) -> int:
        """
        Append records to Google Sheet.

        Returns the number of rows appended.
        """
        if not records:
            return 0

        if self._sheet is None:
            self._connect()

        # Add header if sheet is empty
        try:
            existing = self._sheet.get_all_values()
            if not existing:
                self._sheet.append_row(CSV_COLUMNS)
        except Exception as e:
            logger.warning(f"Could not check sheet headers: {e}")

        # Append rows
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
            self._sheet.append_rows(rows)
            logger.info(f"Appended {len(rows)} rows to Google Sheet")
            return len(rows)
        except Exception as e:
            logger.error(f"Error appending to Google Sheet: {e}")
            return 0
