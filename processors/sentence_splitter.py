"""Sentence splitting and text cleaning utilities."""

import re
import logging

logger = logging.getLogger("filipino_collector")


def remove_emojis(text: str) -> str:
    """Remove emoji characters from text."""
    # Comprehensive emoji pattern covering most Unicode emoji ranges
    emoji_pattern = re.compile(
        "["
        "\U0001F600-\U0001F64F"  # emoticons
        "\U0001F300-\U0001F5FF"  # symbols & pictographs
        "\U0001F680-\U0001F6FF"  # transport & map symbols
        "\U0001F700-\U0001F77F"  # alchemical symbols
        "\U0001F780-\U0001F7FF"  # geometric shapes
        "\U0001F800-\U0001F8FF"  # supplemental arrows
        "\U0001F900-\U0001F9FF"  # supplemental symbols and pictographs
        "\U0001FA00-\U0001FA6F"  # chess symbols
        "\U0001FA70-\U0001FAFF"  # symbols and pictographs extended-A
        "\U00002600-\U000026BF"  # misc symbols (☀☂☃ etc.)
        "\U00002700-\U000027BF"  # dingbats (✂✅✈ etc.)
        "\U0000FE00-\U0000FE0F"  # variation selectors
        "\U00002B00-\U00002BFF"  # misc symbols and arrows
        "\U0001F1E0-\U0001F1FF"  # flags (regional indicator symbols)
        "\U0001F004"              # mahjong tile
        "\U0001F0CF"              # playing card
        "]+",
        flags=re.UNICODE
    )
    return emoji_pattern.sub("", text)


def remove_trailing_hashtags(text: str) -> str:
    """
    Remove trailing hashtags at the end of text (social media style).
    Keeps hashtags that appear in the middle of sentences.
    
    Examples:
      "Ang ganda ng panahon #Filipino #Tagalog" → "Ang ganda ng panahon"
      "Kumain #ako ng kanin" → "Kumain #ako ng kanin" (hashtag in middle, kept)
    """
    # Remove trailing hashtags: hashtags at the end of the text
    # Pattern: one or more hashtags followed by optional whitespace at the end
    text = re.sub(r'(\s+#[\w]+)+\s*$', '', text)
    # Also handle case where hashtag is the entire trailing content after punctuation
    text = re.sub(r'(\s+#[\w]+)+\s*$', '', text)
    return text


def clean_text(text: str) -> str:
    """Remove unwanted characters and normalize whitespace."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove URLs (http, https, www)
    text = re.sub(r"https?://\S+", "", text)
    text = re.sub(r"www\.\S+", "", text)
    # Remove emojis
    text = remove_emojis(text)
    # Remove trailing hashtags (social media style at end of text)
    text = remove_trailing_hashtags(text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove leading punctuation noise only (keep ending punctuation)
    text = text.lstrip(".,;:!?-—\"'()[]{}")
    # Ensure sentence ends with proper punctuation
    if text and text[-1] not in ".!?":
        text += "."
    return text


def split_sentences_nltk(text: str) -> list:
    """Split text into sentences using NLTK."""
    try:
        import nltk
        nltk.download("punkt_tab", quiet=True)
        from nltk.tokenize import sent_tokenize
        return sent_tokenize(text, language="english")
    except Exception as e:
        logger.warning(f"NLTK tokenization failed, falling back to regex: {e}")
        return split_sentences_regex(text)


def split_sentences_regex(text: str) -> list:
    """Split text into sentences using regex fallback."""
    # Split on sentence-ending punctuation followed by space and uppercase
    sentences = re.split(r'(?<=[.!?。！？])\s+(?=[A-ZÁÉÍÓÚÑ])', text)
    # Also split on newlines that look like sentence boundaries
    result = []
    for s in sentences:
        sub = re.split(r'\n{2,}', s)
        result.extend(sub)
    return [s.strip() for s in result if s.strip()]


def split_sentences(text: str) -> list:
    """Split text into sentences, clean each one, and return valid results."""
    raw_sentences = split_sentences_nltk(text)
    cleaned = []
    for s in raw_sentences:
        s = clean_text(s)
        if len(s) > 1:
            cleaned.append(s)
    return cleaned
