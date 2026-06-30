"""RSS feed collector module."""

import logging
from datetime import datetime
from typing import Callable, List

import feedparser

logger = logging.getLogger("filipino_collector")


def fetch_rss_feed(url: str) -> List[dict]:
    """
    Fetch and parse a single RSS feed.

    Returns a list of dicts with keys:
        title, content, url, published_date, source_name
    """
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            logger.warning(f"Invalid RSS feed: {url} - {feed.bozo_exception}")
            return []

        entries = []
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            content = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or getattr(entry, "content", [{}])[0].get("value", "")
            )
            url_val = getattr(entry, "link", "")
            published = getattr(entry, "published", "") or str(datetime.now())

            entries.append({
                "title": title,
                "content": content,
                "url": url_val,
                "published_date": published,
                "source_name": feed.feed.get("title", url),
            })

        logger.info(f"Fetched {len(entries)} entries from {url}")
        return entries

    except Exception as e:
        logger.error(f"Error fetching RSS feed {url}: {e}")
        return []


def collect_all_rss(rss_sources: List[dict]) -> List[dict]:
    """
    Collect entries from all configured RSS sources.

    Args:
        rss_sources: List of dicts with 'name' and 'url' keys.

    Returns:
        List of entry dicts.
    """
    all_entries = []
    for source in rss_sources:
        name = source.get("name", "Unknown")
        url = source.get("url", "")
        if not url:
            logger.warning(f"Skipping RSS source with no URL: {name}")
            continue

        entries = fetch_rss_feed(url)
        for entry in entries:
            entry["source_name"] = name
        all_entries.extend(entries)

    logger.info(f"Total RSS entries collected: {len(all_entries)}")
    return all_entries


def process_rss_to_sentences(rss_entries: List[dict], split_func: Callable) -> List[dict]:
    """Process RSS entries into sentence records (no language filter)."""
    records = []
    for entry in rss_entries:
        full_text = f"{entry['title']}. {entry['content']}"
        sentences = split_func(full_text)

        for sentence in sentences:
            records.append({
                "sentence": sentence,
                "word_count": len(sentence.split()),
                "source_type": "rss",
                "source_title": entry["title"],
                "source_url_or_video_id": entry["url"],
                "timestamp": "",
                "date_extracted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    logger.info(f"Processed {len(records)} sentences from RSS")
    return records
