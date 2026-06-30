"""Telegram bot collector module."""

import logging
from datetime import datetime
from typing import Callable, List

from telegram import Update
from telegram.ext import Application, MessageHandler, CommandHandler, filters, ContextTypes

logger = logging.getLogger("filipino_collector")


class TelegramCollector:
    """Telegram bot that listens for messages and processes them into sentences."""

    def __init__(
        self,
        token: str,
        process_callback: Callable[[List[dict]], None],
        split_func: Callable,
    ):
        """
        Args:
            token: Telegram bot token.
            process_callback: Function to call with processed sentence records.
            split_func: Sentence splitting function.
        """
        self.token = token
        self.process_callback = process_callback
        self.split_func = split_func
        self.application = None

    async def _handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming text messages."""
        if not update.message or not update.message.text:
            return

        text = update.message.text
        user = update.effective_user
        chat_id = update.effective_chat.id

        logger.info(f"Telegram message from {user.first_name} (chat {chat_id}): {text[:80]}...")

        # Split into sentences
        sentences = self.split_func(text)

        if not sentences:
            await update.message.reply_text("⚠️ No sentences could be extracted from your message.")
            return

        # Create records
        records = []
        for sentence in sentences:
            records.append({
                "sentence": sentence,
                "word_count": len(sentence.split()),
                "source_type": "telegram",
                "source_title": f"Message from {user.first_name}",
                "source_url_or_video_id": f"chat_{chat_id}",
                "timestamp": "",
                "date_extracted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

        # Send to processing pipeline
        self.process_callback(records)

        # Confirm to user
        await update.message.reply_text(
            f"✅ Collected {len(sentences)} sentence(s)!"
        )

    async def _handle_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command — show RSS feed status and stats."""
        try:
            from collectors.rss_collector import get_rss_status

            status = get_rss_status()

            if not status:
                await update.message.reply_text(
                    "📡 RSS Status\n\n"
                    "No RSS feeds have been checked yet.\n"
                    "The first RSS run happens on startup."
                )
                return

            lines = ["📡 *RSS Feed Status*\n"]
            total_entries = 0
            ok_count = 0
            error_count = 0

            for url, info in status.items():
                name = info.get("name", "Unknown")
                state = info.get("status", "unknown")
                entries = info.get("entries", 0)
                total_entries += entries

                if state == "ok":
                    icon = "✅"
                    ok_count += 1
                    lines.append(f"{icon} *{name}*: {entries} entries")
                elif state == "empty":
                    icon = "⚠️"
                    lines.append(f"{icon} *{name}*: 0 entries (feed returned nothing)")
                else:
                    icon = "❌"
                    error_count += 1
                    err = info.get("error", "Unknown error")
                    lines.append(f"{icon} *{name}*: Error - {err}")

            last_checked = list(status.values())[0].get("last_checked", "N/A") if status else "N/A"

            lines.append(f"\n📊 *Summary:*")
            lines.append(f"  • Working feeds: {ok_count}")
            lines.append(f"  • Broken feeds: {error_count}")
            lines.append(f"  • Total entries: {total_entries}")
            lines.append(f"  • Last checked: {last_checked}")
            lines.append(f"\n⏰ RSS runs every 60 minutes automatically.")

            await update.message.reply_text(
                "\n".join(lines),
                parse_mode="Markdown"
            )
        except Exception as e:
            logger.error(f"Error in /status command: {e}")
            await update.message.reply_text(f"⚠️ Could not retrieve status: {e}")

    async def _handle_cleanup(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /cleanup command — remove duplicate rows from Google Sheet."""
        try:
            await update.message.reply_text("🧹 Cleaning up duplicates in Google Sheet...")

            from exporters.sheets_exporter import GoogleSheetsExporter
            import yaml

            # Load settings to get sheet config
            with open("config/settings.yaml", "r", encoding="utf-8") as f:
                settings = yaml.safe_load(f)

            gs_config = settings.get("output", {}).get("google_sheets", {})
            if not gs_config.get("enabled", False):
                await update.message.reply_text("⚠️ Google Sheets is not enabled.")
                return

            exporter = GoogleSheetsExporter(
                credentials_path=gs_config.get("credentials_path", ""),
                sheet_name=gs_config.get("sheet_name", "Filipino Sentences"),
            )
            removed = exporter.cleanup_duplicates()

            if removed > 0:
                await update.message.reply_text(
                    f"✅ Removed {removed} duplicate row(s) from Google Sheet!"
                )
            else:
                await update.message.reply_text("✅ No duplicates found. Sheet is clean!")
        except Exception as e:
            logger.error(f"Error in /cleanup command: {e}")
            await update.message.reply_text(f"⚠️ Cleanup failed: {e}")

    async def _handle_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        await update.message.reply_text(
            "🤖 *Filipino Sentence Collector*\n\n"
            "*Commands:*\n"
            "• Send any text → Collects sentences\n"
            "• /status → Check RSS feed status\n"
            "• /cleanup → Remove duplicate rows from Google Sheet\n"
            "• /help → Show this message\n\n"
            "Sentences are saved to Google Sheets automatically.\n"
            "Duplicates are skipped on new entries automatically.",
            parse_mode="Markdown"
        )


    def run(self):
        """Start the Telegram bot (blocking)."""
        self.application = Application.builder().token(self.token).build()

        # Handle commands
        self.application.add_handler(CommandHandler("status", self._handle_status))
        self.application.add_handler(CommandHandler("cleanup", self._handle_cleanup))
        self.application.add_handler(CommandHandler("help", self._handle_help))


        # Handle all text messages (non-commands)
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        logger.info("Telegram bot started. Listening for messages...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
