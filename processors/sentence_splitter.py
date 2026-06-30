"""Sentence splitting and text cleaning utilities."""

import re
import logging

logger = logging.getLogger("filipino_collector")


def clean_text(text: str) -> str:
    """Remove unwanted characters and normalize whitespace."""
    if not text:
        return ""
    # Remove HTML tags
    text = re.sub(r"<[^>]+>", "", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", "", text)
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text).strip()
    # Remove leading/trailing punctuation noise
    text = text.strip(".,;:!?-—")
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
