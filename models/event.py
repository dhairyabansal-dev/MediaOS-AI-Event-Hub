"""
Event: a cluster of MediaItems the classifier decided belong together.
This is what the dashboard actually renders as a "card".
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import List, Dict
from pydantic import BaseModel, Field
from models.media import MediaItem
import hashlib


class Event(BaseModel):
    id: str
    title: str
    media: List[MediaItem] = Field(default_factory=list)
    thumbnail: str | None = None
    score: float = 0.0                # relevance / hotness score
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @staticmethod
    def make_id(title: str) -> str:
        raw = title.strip().lower().encode("utf-8", errors="ignore")
        return hashlib.sha256(raw).hexdigest()[:16]

    @property
    def source_counts(self) -> Dict[str, int]:
        counts: Dict[str, int] = {}
        for m in self.media:
            counts[m.source_type] = counts.get(m.source_type, 0) + 1
        return counts

    @property
    def media_count(self) -> int:
        return len(self.media)

    def pick_thumbnail(self) -> str | None:
        for m in self.media:
            if m.image:
                return m.image
        return None

    @classmethod
    def from_media(cls, title: str, media: List[MediaItem], score: float = 0.0) -> "Event":
        ev = cls(id=cls.make_id(title), title=title, media=media, score=score)
        ev.thumbnail = ev.pick_thumbnail()
        return ev
