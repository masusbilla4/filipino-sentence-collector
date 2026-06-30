"""RSS feed collector module."""

import logging
from datetime import datetime

import feedparser

logger = logging.getLogger("filipino_collector")

# Global status tracker for RSS feeds
_rss_status = {}


def get_rss_status() -> dict:
    """Return the latest RSS feed status for the /status command."""
    return _rss_status


def fetch_rss_feed(url: str, name: str = "") -> list:
    """
    Fetch and parse a single RSS feed.
    
    Returns a list of dicts with keys:
        title, content, url, published_date, source_name
    """
    try:
        feed = feedparser.parse(url)
        if feed.bozo and not feed.entries:
            error_msg = str(feed.bozo_exception) if feed.bozo_exception else "Unknown error"
            logger.warning(f"Invalid RSS feed: {url} - {error_msg}")
            _rss_status[url] = {
                "name": name,
                "status": "error",
                "entries": 0,
                "error": error_msg[:80],
                "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            return []

        entries = []
        for entry in feed.entries:
            title = getattr(entry, "title", "")
            content = (
                getattr(entry, "summary", "")
                or getattr(entry, "description", "")
                or getattr(entry, "content", [{}])[0].get("value", "")
            )
            url_entry = getattr(entry, "link", "")
            published = getattr(entry, "published", "") or str(datetime.now())

            entries.append({
                "title": title,
                "content": content,
                "url": url_entry,
                "published_date": published,
                "source_name": feed.feed.get("title", name),
            })

        logger.info(f"Fetched {len(entries)} entries from {url}")
        _rss_status[url] = {
            "name": name,
            "status": "ok" if entries else "empty",
            "entries": len(entries),
            "error": "",
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return entries

    except Exception as e:
        logger.error(f"Error fetching RSS feed {url}: {e}")
        _rss_status[url] = {
            "name": name,
            "status": "error",
            "entries": 0,
            "error": str(e)[:80],
            "last_checked": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        return []


def collect_all_rss(rss_sources: list) -> list:
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

        entries = fetch_rss_feed(url, name)
        for entry in entries:
            entry["source_name"] = name
        all_entries.extend(entries)

    logger.info(f"Total RSS entries collected: {len(all_entries)}")
    return all_entries


def process_rss_to_sentences(
    rss_entries: list,
    split_func,
) -> list:
    """
    Process RSS entries into filtered sentence records.
    
    Returns list of sentence record dicts ready for export.
    """
    records = []
    for entry in rss_entries:
        # Combine title + content for sentence extraction
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
