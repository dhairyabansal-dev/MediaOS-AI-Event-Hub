"""
Normalizer: takes the raw MediaItems straight out of ProviderManager.collect()
and cleans them up so downstream dedup/clustering sees consistent data —
stripped/collapsed whitespace, HTML stripped from descriptions, titles
truncated to a sane length, obviously-broken items dropped.
"""
from __future__ import annotations
import re
import logging
from typing import List

from bs4 import BeautifulSoup
from models.media import MediaItem

logger = logging.getLogger(__name__)

MAX_TITLE_LEN = 200
MAX_DESC_LEN = 600
_WHITESPACE_RE = re.compile(r"\s+")


class Normalizer:
    def normalize(self, items: List[MediaItem]) -> List[MediaItem]:
        out: List[MediaItem] = []
        for item in items:
            cleaned = self._normalize_one(item)
            if cleaned is not None:
                out.append(cleaned)
        logger.info("Normalizer: %d -> %d items", len(items), len(out))
        return out

    def _normalize_one(self, item: MediaItem) -> MediaItem | None:
        title = self._clean_text(item.title)
        if not title:
            return None  # nothing usable to cluster/display on

        description = self._strip_html(item.description or "")
        description = self._clean_text(description)[:MAX_DESC_LEN]
        title = title[:MAX_TITLE_LEN]

        # pydantic models are mutable here (not frozen), safe to update in place
        item.title = title
        item.description = description
        return item

    @staticmethod
    def _strip_html(text: str) -> str:
        if "<" not in text:
            return text
        try:
            return BeautifulSoup(text, "html.parser").get_text(separator=" ")
        except Exception:
            return text

    @staticmethod
    def _clean_text(text: str) -> str:
        text = _WHITESPACE_RE.sub(" ", text or "")
        return text.strip()
