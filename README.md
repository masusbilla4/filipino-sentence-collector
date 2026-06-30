# Filipino Sentence Collector

A Python-based automation system that collects sentences from **Telegram messages**, **RSS feeds**, and **YouTube subtitles**, then stores them in CSV (with optional Google Sheets export).

## 🎯 Features

- **Telegram Bot Input** — Send text from your phone; the bot splits it into sentences and stores them instantly.
- **RSS Feeds** — Automatically fetches and processes articles from configured RSS sources on a schedule.
- **YouTube Subtitles** — Fetches subtitles from YouTube channels/playlists, prioritizing Filipino (`tl`/`fil`) subtitles.
- **Sentence Splitting** — Uses NLTK `sent_tokenize` with a regex fallback.
- **Deduplication** — Prevents duplicate sentences within and across runs.
- **Daily CSV Files** — Exports to date-stamped CSV files in append mode.
- **Google Sheets (Optional)** — Append rows to a Google Sheet matching the CSV structure.
- **Scheduled Automation** — APScheduler runs RSS + YouTube collection on configurable intervals.
- **Error Handling** — Skips invalid feeds and videos without subtitles; logs errors and continues.

## 📦 Project Structure

```
Filipino Sentence Collector/
├── config/
│   ├── sources.yaml          # RSS feeds & YouTube channels
│   └── settings.yaml         # App settings (filters, schedule, output)
├── collectors/
│   ├── telegram_collector.py # Telegram Bot listener
│   ├── rss_collector.py      # RSS feed parser
│   └── youtube_collector.py  # YouTube subtitle fetcher
├── processors/
│   ├── sentence_splitter.py  # Sentence tokenization + cleaning
│   └── deduplicator.py       # Dedup logic
├── exporters/
│   ├── csv_exporter.py        # CSV output (daily files)
│   └── sheets_exporter.py    # Google Sheets (optional)
├── utils/
│   └── logger.py             # Logging setup
├── credentials/              # Google service account JSON (gitignored)
├── output/                   # CSV output directory (gitignored)
├── main.py                   # Entry point
├── scheduler.py              # APScheduler for RSS/YouTube
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

## 🚀 Setup

### 1. Install dependencies

```bash
cd "Filipino Sentence Collector"
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
```

Edit `.env` and set your `TELEGRAM_BOT_TOKEN` (get one from [@BotFather](https://t.me/BotFather) on Telegram).

### 3. Configure sources

Edit `config/sources.yaml` to add your RSS feeds and YouTube channels/playlists.

Edit `config/settings.yaml` to adjust filters, schedule intervals, and output options.

### 4. Run

```bash
python main.py
```

## 📊 CSV Output

Sentences are saved to `output/filipino_sentences_YYYY-MM-DD.csv` with these columns:

| Column | Description |
|--------|-------------|
| `sentence` | The extracted sentence |
| `word_count` | Number of words in the sentence |
| `source_type` | `telegram`, `rss`, or `youtube` |
| `source_title` | Title of the source (article title, video title, or sender name) |
| `source_url_or_video_id` | URL (RSS) or video ID (YouTube) or chat ID (Telegram) |
| `timestamp` | Start timestamp (YouTube only, `MM:SS` format) |
| `date_extracted` | Datetime when the sentence was processed |

## ☁️ Google Sheets (Optional)

1. Create a Google Service Account and download the JSON key.
2. Place it in `credentials/service_account.json`.
3. Create a Google Sheet and share it with the service account email.
4. In `config/settings.yaml`, set:
   ```yaml
   output:
     google_sheets:
       enabled: true
       sheet_name: "Your Sheet Name"
       credentials_path: "credentials/service_account.json"
   ```

## 🔁 Automation

- **Telegram**: Runs continuously (blocking) — listens for messages in real time.
- **RSS + YouTube**: Run on schedule via APScheduler (configurable in `settings.yaml`).
  - Default: RSS every 60 min, YouTube every 120 min.
- An initial RSS + YouTube collection runs on startup.

## ☁️ Cloud Deployment (Railway / Render)

1. Push the project to a Git repository.
2. Create a new service on Railway/Render.
3. Set environment variables: `TELEGRAM_BOT_TOKEN`
4. Set start command: `python main.py`
5. The Telegram bot keeps the process alive; APScheduler handles RSS/YouTube in the background.

## ⚠️ Constraints

This system **only** collects from:
- ✅ Telegram input
- ✅ RSS feeds
- ✅ YouTube subtitles

It does **not** scrape Facebook, TikTok, X (Twitter), Shopee, or Lazada.

## 🛠️ Tech Stack

- Python 3.x
- python-telegram-bot
- feedparser
- YouTubeTranscriptApi
- nltk
- pandas
- gspread (optional)
- APScheduler
- PyYAML
- python-dotenv
