"""Deduplication utilities for sentences."""

import hashlib
import logging
import os
from typing import Optional, Set

logger = logging.getLogger("filipino_collector")


def sentence_hash(sentence: str) -> str:
    """Generate a normalized hash for a sentence."""
    normalized = sentence.lower().strip()
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


def load_existing_hashes(csv_path: str) -> Set[str]:
    """Load sentence hashes from an existing CSV file."""
    hashes: Set[str] = set()
    if not os.path.exists(csv_path):
        return hashes
    try:
        import pandas as pd
        df = pd.read_csv(csv_path)
        if "sentence" in df.columns:
            for s in df["sentence"].dropna():
                hashes.add(sentence_hash(str(s)))
    except Exception as e:
        logger.warning(f"Could not load existing hashes from {csv_path}: {e}")
    return hashes


def deduplicate_sentences(
    sentences: list,
    existing_hashes: Optional[Set[str]] = None,
) -> list:
    """
    Remove duplicate sentences.
    Compares against existing hashes and removes intra-batch duplicates.
    """
    if existing_hashes is None:
        existing_hashes = set()

    seen: Set[str] = set()
    unique = []
    for s in sentences:
        h = sentence_hash(s)
        if h not in existing_hashes and h not in seen:
            seen.add(h)
            unique.append(s)
    return unique
