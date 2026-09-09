"""
Event Builder: takes clusters of MediaItems from the Classifier and turns
each into an Event — picking a representative title, computing a score
(so the dashboard can rank/highlight), and capping at MAX_EVENTS.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import List

from models.media import MediaItem
from models.event import Event
import config

logger = logging.getLogger(__name__)


class EventBuilder:
    def build(self, clusters: List[List[MediaItem]]) -> List[Event]:
        events = [self._build_one(cluster) for cluster in clusters]
        events.sort(key=lambda e: e.score, reverse=True)
        capped = events[: config.MAX_EVENTS]
        logger.info(
            "EventBuilder: %d clusters -> %d events (capped at %d)",
            len(clusters), len(capped), config.MAX_EVENTS,
        )
        return capped

    def _build_one(self, cluster: List[MediaItem]) -> Event:
        title = self._pick_title(cluster)
        score = self._score(cluster)
        return Event.from_media(title=title, media=cluster, score=score)

    @staticmethod
    def _pick_title(cluster: List[MediaItem]) -> str:
        # Representative title = the most recent item's title. Simple,
        # and keeps the card's headline fresh as new media joins the cluster.
        newest = max(cluster, key=lambda m: m.published)
        return newest.title

    def _score(self, cluster: List[MediaItem]) -> float:
        size_score = len(cluster)  # more corroborating media = more "real"

        # Recency bonus: newer clusters edge out stale ones of the same size
        most_recent = max(m.published for m in cluster)
        age_hours = (datetime.now(timezone.utc) - most_recent).total_seconds() / 3600
        recency_bonus = max(0.0, 6 - age_hours) / 6  # full bonus if <1h old, fades out by 6h

        priority_bonus = 5.0 if self._matches_priority_topic(cluster) else 0.0

        return round(size_score + recency_bonus + priority_bonus, 3)

    @staticmethod
    def _matches_priority_topic(cluster: List[MediaItem]) -> bool:
        topics = [t.lower() for t in config.PRIORITY_TOPICS]
        for m in cluster:
            text = f"{m.title} {m.description or ''}".lower()
            if any(topic in text for topic in topics):
                return True
        return False
