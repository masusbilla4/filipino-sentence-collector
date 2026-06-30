"""Telegram bot collector module."""

import logging
from datetime import datetime
from typing import Callable, List

from telegram import Update
from telegram.ext import Application, MessageHandler, filters, ContextTypes

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

        # Split into sentences (no language filter)
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

    def run(self):
        """Start the Telegram bot (blocking)."""
        self.application = Application.builder().token(self.token).build()

        # Handle all text messages
        self.application.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._handle_message)
        )

        logger.info("Telegram bot started. Listening for messages...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
