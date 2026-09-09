"""
YouTube provider.

YouTube exposes a real, official RSS feed per channel:
    https://www.youtube.com/feeds/videos.xml?channel_id=UC...

The catch: it needs the UC... channel_id, not the @handle people actually
share. So we resolve @handle -> channel_id once (by reading the channel
page's HTML for its canonical channel id) and cache the mapping to disk,
since that resolution step is the fragile/slow part, not the feed read.
"""
from __future__ import annotations
import json
import logging
import re
from pathlib import Path
from typing import List, Optional

import feedparser
import requests

from acquisition.providers.base import Provider
from models.media import MediaItem
import config

logger = logging.getLogger(__name__)

CACHE_PATH = Path(__file__).parent / ".youtube_channel_id_cache.json"
CHANNEL_ID_RE = re.compile(r'"channelId":"(UC[0-9A-Za-z_-]{22})"')


class YouTubeProvider(Provider):
    name = "youtube"

    def __init__(self, sources: List[dict] | None = None):
        # each source: {"name": "PeekTV", "handle": "PeekTVOfficial"}
        self.sources = list(sources) if sources is not None else list(config.YOUTUBE_SOURCES)
        self._cache = self._load_cache()

    def add_discovered(self, name: str, handle_or_url: str) -> None:
        """Registers a YouTube channel discovered via another provider
        (e.g. found in an Instagram bio link) for this run. Accepts either
        a bare @handle or a full youtube.com/... URL and normalizes it."""
        handle = handle_or_url
        for prefix in ("https://www.youtube.com/@", "https://youtube.com/@", "www.youtube.com/@"):
            if handle.startswith(prefix):
                handle = handle[len(prefix):]
                break
        handle = handle.strip("/ ")
        if handle and not any(s["handle"] == handle for s in self.sources):
            self.sources.append({"name": name, "handle": handle})

    def fetch(self) -> List[MediaItem]:
        items: List[MediaItem] = []
        for src in self.sources:
            try:
                channel_id = self._resolve_channel_id(src["handle"])
                if not channel_id:
                    logger.warning("YouTubeProvider: could not resolve @%s", src["handle"])
                    continue
                items.extend(self._fetch_feed(src["name"], channel_id))
            except Exception as e:
                logger.warning("YouTubeProvider: failed on @%s: %s", src.get("handle"), e)
        return items

    # -- channel id resolution -------------------------------------------------

    def _resolve_channel_id(self, handle: str) -> Optional[str]:
        if handle in self._cache:
            return self._cache[handle]

        url = f"https://www.youtube.com/@{handle}"
        resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=10)
        resp.raise_for_status()
        match = CHANNEL_ID_RE.search(resp.text)
        if not match:
            return None

        channel_id = match.group(1)
        self._cache[handle] = channel_id
        self._save_cache()
        return channel_id

    def _load_cache(self) -> dict:
        if CACHE_PATH.exists():
            try:
                return json.loads(CACHE_PATH.read_text())
            except Exception:
                return {}
        return {}

    def _save_cache(self) -> None:
        try:
            CACHE_PATH.write_text(json.dumps(self._cache, indent=2))
        except Exception as e:
            logger.warning("YouTubeProvider: failed to write cache: %s", e)

    # -- feed read --------------------------------------------------------------

    def _fetch_feed(self, name: str, channel_id: str) -> List[MediaItem]:
        feed_url = f"https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}"
        feed = feedparser.parse(feed_url)
        out: List[MediaItem] = []
        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "")
            if not title or not link:
                continue

            thumbnail = None
            media_thumb = getattr(entry, "media_thumbnail", None)
            if media_thumb:
                thumbnail = media_thumb[0].get("url")

            description = ""
            media_desc = getattr(entry, "media_description", None)
            if media_desc:
                description = media_desc

            published = getattr(entry, "published", None)

            out.append(
                MediaItem.create(
                    title=title,
                    source=f"YouTube:{name}",
                    url=link,
                    source_type="youtube",
                    image=thumbnail,
                    description=description,
                )
            )
        return out
