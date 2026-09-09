"""
Generic RSS/Atom provider. Works for any real RSS feed URL
(news sites, blogs, official press RSS, etc.) — not YouTube or Instagram,
those have dedicated providers.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import List
import feedparser

from acquisition.providers.base import Provider
from models.media import MediaItem
import config

logger = logging.getLogger(__name__)


class RSSProvider(Provider):
    name = "rss"

    def __init__(self, sources: List[dict] | None = None):
        # each source: {"name": "TechCrunch", "url": "https://..."}
        self.sources = sources if sources is not None else config.RSS_SOURCES

    def fetch(self) -> List[MediaItem]:
        items: List[MediaItem] = []
        for src in self.sources:
            if src.get("name", "").strip().upper() == "RSS":
                logger.warning(
                    "RSSProvider: source at %s is named literally 'RSS' — "
                    "use the real outlet name instead", src.get("url")
                )
                continue
            try:
                items.extend(self._fetch_one(src))
            except Exception as e:
                logger.warning("RSSProvider: failed on %s: %s", src.get("name"), e)
        return items

    def _fetch_one(self, src: dict) -> List[MediaItem]:
        feed = feedparser.parse(src["url"])
        out: List[MediaItem] = []
        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "")
            if not title or not link:
                continue

            published = self._parse_published(entry)
            image = self._extract_image(entry)
            description = getattr(entry, "summary", "") or ""

            out.append(
                MediaItem.create(
                    title=title,
                    source=src["name"],
                    url=link,
                    source_type="rss",
                    image=image,
                    published=published,
                    description=description,
                )
            )
        return out

    @staticmethod
    def _parse_published(entry) -> datetime:
        for key in ("published_parsed", "updated_parsed"):
            t = getattr(entry, key, None)
            if t:
                return datetime(*t[:6], tzinfo=timezone.utc)
        return datetime.now(timezone.utc)

    @staticmethod
    def _extract_image(entry) -> str | None:
        # media_content / media_thumbnail / enclosures are the common spots
        media_content = getattr(entry, "media_content", None)
        if media_content:
            url = media_content[0].get("url")
            if url:
                return url
        media_thumb = getattr(entry, "media_thumbnail", None)
        if media_thumb:
            url = media_thumb[0].get("url")
            if url:
                return url
        for enc in getattr(entry, "enclosures", []) or []:
            if str(enc.get("type", "")).startswith("image"):
                return enc.get("href")
        return None
