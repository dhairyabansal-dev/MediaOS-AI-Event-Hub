"""
Deduplicator: removes near-duplicate MediaItems — same story reposted,
same YouTube video showing up via two feeds, etc. Uses fuzzy title
matching (rapidfuzz) rather than exact match, since real-world titles
vary slightly across sources ("Apple unveils AI" vs "Apple Unveils AI
Features Today").

This is NOT the same job as clustering (Hour 4) — dedup removes items
that are literally the same piece of content; clustering groups distinct
items that are about the same event.
"""
from __future__ import annotations
import logging
from typing import List
from rapidfuzz import fuzz

from models.media import MediaItem
import config

logger = logging.getLogger(__name__)


class Deduplicator:
    def __init__(self, threshold: int | None = None):
        self.threshold = threshold if threshold is not None else config.DEDUP_FUZZY_THRESHOLD

    def deduplicate(self, items: List[MediaItem]) -> List[MediaItem]:
        # Exact URL dupes first (cheap, exact)
        seen_urls: set[str] = set()
        deduped_by_url: List[MediaItem] = []
        for item in items:
            if item.url in seen_urls:
                continue
            seen_urls.add(item.url)
            deduped_by_url.append(item)

        # Then fuzzy title dupes (O(n^2) but n <= MAX_MEDIA_PER_CYCLE, so fine)
        kept: List[MediaItem] = []
        for item in deduped_by_url:
            if not self._is_near_duplicate(item, kept):
                kept.append(item)

        logger.info(
            "Deduplicator: %d -> %d items (threshold=%d)",
            len(items), len(kept), self.threshold,
        )
        return kept

    def _is_near_duplicate(self, item: MediaItem, kept: List[MediaItem]) -> bool:
        for existing in kept:
            score = fuzz.token_sort_ratio(item.title.lower(), existing.title.lower())
            if score >= self.threshold:
                return True
        return False
