"""YouTube subtitle collector module."""

import logging
from datetime import datetime
from typing import Callable, List, Optional

from youtube_transcript_api import YouTubeTranscriptApi, TranscriptsDisabled, NoTranscriptFound

logger = logging.getLogger("filipino_collector")


def get_latest_videos(
    channel_id: Optional[str] = None,
    playlist_id: Optional[str] = None,
    max_results: int = 10,
) -> List[dict]:
    """Get latest video IDs from a YouTube channel or playlist via RSS."""
    videos = []
    try:
        import requests
        import feedparser

        if playlist_id:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?playlist_id={playlist_id}"
        elif channel_id:
            rss_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        else:
            logger.warning("No channel_id or playlist_id provided")
            return []

        resp = requests.get(rss_url, timeout=15)
        if resp.status_code == 200:
            feed = feedparser.parse(resp.text)
            for entry in feed.entries[:max_results]:
                video_id = entry.get("yt_videoid", entry.link.split("v=")[-1].split("&")[0])
                videos.append({"video_id": video_id, "title": entry.get("title", "")})
        else:
            logger.warning(f"Could not fetch YouTube RSS: {rss_url}")

    except Exception as e:
        logger.error(f"Error fetching YouTube videos: {e}")

    return videos


def fetch_subtitles(video_id: str, preferred_languages: Optional[List[str]] = None) -> List[dict]:
    """Fetch subtitles for a YouTube video, prioritizing Filipino."""
    if preferred_languages is None:
        preferred_languages = ["tl", "fil"]

    try:
        transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)

        # Try preferred languages first
        for lang in preferred_languages:
            try:
                transcript = transcript_list.find_transcript([lang])
                subtitles = transcript.fetch()
                logger.info(f"Fetched '{lang}' subtitles for video {video_id}")
                return subtitles
            except NoTranscriptFound:
                continue

        # Try translated subtitles
        for lang in preferred_languages:
            try:
                for t in transcript_list:
                    translated = t.translate(lang)
                    subtitles = translated.fetch()
                    logger.info(f"Fetched translated '{lang}' subtitles for video {video_id}")
                    return subtitles
            except Exception:
                continue

        # Fallback: any available transcript
        try:
            first_transcript = next(iter(transcript_list))
            subtitles = first_transcript.fetch()
            logger.info(f"Fetched fallback subtitles for {video_id} in '{first_transcript.language_code}'")
            return subtitles
        except StopIteration:
            pass

    except TranscriptsDisabled:
        logger.info(f"Subtitles disabled for video {video_id}")
    except Exception as e:
        logger.error(f"Error fetching subtitles for {video_id}: {e}")

    return []


def collect_youtube_subtitles(
    youtube_sources: List[dict],
    max_videos_per_source: int = 10,
) -> List[dict]:
    """Collect subtitles from all configured YouTube sources."""
    all_subtitles = []

    for source in youtube_sources:
        name = source.get("name", "Unknown")
        channel_id = source.get("channel_id")
        playlist_id = source.get("playlist_id")

        logger.info(f"Fetching videos for YouTube source: {name}")
        videos = get_latest_videos(
            channel_id=channel_id,
            playlist_id=playlist_id,
            max_results=max_videos_per_source,
        )

        for video in videos:
            video_id = video["video_id"]
            title = video.get("title", "")

            subtitles = fetch_subtitles(video_id)
            if not subtitles:
                logger.info(f"No subtitles for video {video_id} - {title}")
                continue

            for sub in subtitles:
                all_subtitles.append({
                    "text": sub.get("text", ""),
                    "start": sub.get("start", 0),
                    "duration": sub.get("duration", 0),
                    "video_id": video_id,
                    "video_title": title,
                    "source_name": name,
                })

    logger.info(f"Total YouTube subtitle segments collected: {len(all_subtitles)}")
    return all_subtitles


def process_youtube_to_sentences(
    subtitle_data: List[dict],
    split_func: Callable,
) -> List[dict]:
    """Process YouTube subtitle data into sentence records (no language filter)."""
    records = []

    # Group subtitles by video
    videos = {}
    for sub in subtitle_data:
        vid = sub["video_id"]
        if vid not in videos:
            videos[vid] = {"title": sub["video_title"], "segments": []}
        videos[vid]["segments"].append(sub)

    for video_id, data in videos.items():
        full_text = " ".join(seg["text"] for seg in data["segments"])
        sentences = split_func(full_text)

        for sentence in sentences:
            timestamp = _estimate_timestamp(sentence, data["segments"])
            records.append({
                "sentence": sentence,
                "word_count": len(sentence.split()),
                "source_type": "youtube",
                "source_title": data["title"],
                "source_url_or_video_id": video_id,
                "timestamp": timestamp,
                "date_extracted": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            })

    logger.info(f"Processed {len(records)} sentences from YouTube")
    return records


def _estimate_timestamp(sentence: str, segments: List[dict]) -> str:
    """Estimate the start timestamp for a sentence."""
    first_words = sentence.split()[:3]
    for seg in segments:
        seg_words = seg["text"].split()
        overlap = any(w.lower() in [sw.lower() for sw in seg_words] for w in first_words)
        if overlap:
            start = seg.get("start", 0)
            minutes = int(start // 60)
            seconds = int(start % 60)
            return f"{minutes:02d}:{seconds:02d}"
    return ""
