"""
Provider manager: runs every registered Provider and returns a flat,
capped list of MediaItems for this fetch cycle. Adding a new source
type later means writing a new Provider and registering it here —
nothing else in the pipeline needs to change.
"""
from __future__ import annotations
import logging
from typing import List

from acquisition.providers.rss import RSSProvider  # noqa: F401 — kept for future use, not registered below
from acquisition.providers.youtube import YouTubeProvider
from acquisition.providers.instagram import InstagramProvider
from acquisition.providers.press import PressProvider
from models.media import MediaItem
import config

logger = logging.getLogger(__name__)


class ProviderManager:
    def __init__(self):
        self.youtube = YouTubeProvider()
        self.instagram = InstagramProvider()
        self.providers = [
            # RSSProvider() intentionally NOT registered — mainstream media
            # / article headlines are explicitly out of scope. The class
            # still exists (kept modular/swappable) in case that changes,
            # but nothing wires it in by default.
            self.youtube,
            self.instagram,
            PressProvider(),
        ]

    def _discover_youtube_from_instagram_bios(self) -> None:
        """For every Instagram seed + cached-discovered account, check its
        bio link for a YouTube channel and register it with YouTubeProvider.
        Uses the anonymous IG loader (bio is public data) — cheap enough to
        run every cycle since it's a single lightweight profile lookup, but
        YouTubeProvider's own channel-id cache means we still only resolve
        each handle to a channel_id once."""
        usernames = {s["username"]: s["name"] for s in self.instagram.seed_sources}
        for cache_entry in self.instagram._discovery_cache.values():
            for u in cache_entry.get("followees", []):
                usernames.setdefault(u, u)

        for username, display_name in usernames.items():
            yt_url = self.instagram.discover_youtube_channel(username)
            if yt_url:
                self.youtube.add_discovered(display_name, yt_url)

    def collect(self) -> List[MediaItem]:
        self._discover_youtube_from_instagram_bios()

        all_items: List[MediaItem] = []
        for provider in self.providers:
            try:
                items = provider.fetch()
                logger.info("%s: fetched %d items", provider.name, len(items))
                all_items.extend(items)
            except Exception as e:
                # A provider failing entirely must not kill the cycle.
                logger.error("%s: provider crashed: %s", provider.name, e)

        all_items = self._apply_blacklist(all_items)

        # Most recent first, capped to MAX_MEDIA_PER_CYCLE
        all_items.sort(key=lambda m: m.published, reverse=True)
        return all_items[: config.MAX_MEDIA_PER_CYCLE]

    @staticmethod
    def _apply_blacklist(items: List[MediaItem]) -> List[MediaItem]:
        blacklist = [b.upper() for b in config.SOURCE_BLACKLIST]
        kept = []
        dropped = 0
        for item in items:
            source_upper = item.source.upper()
            if any(b in source_upper for b in blacklist):
                dropped += 1
                continue
            kept.append(item)
        if dropped:
            logger.info("Blacklist filtered out %d item(s)", dropped)
        return kept
