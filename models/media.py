"""
MediaItem: the atomic unit of content coming out of ANY provider
(RSS, YouTube, Press...). Every provider must normalize into this shape.
"""
from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional
from pydantic import BaseModel, Field
import hashlib


class MediaItem(BaseModel):
    id: str = Field(..., description="stable hash id, derived from url+title")
    title: str
    source: str                 # e.g. "TechCrunch", "YouTube:Apple", "Reuters"
    source_type: str = "rss"    # "rss" | "youtube" | "press"
    url: str
    image: Optional[str] = None
    published: datetime
    description: Optional[str] = ""

    @staticmethod
    def make_id(url: str, title: str) -> str:
        raw = f"{url}|{title}".encode("utf-8", errors="ignore")
        return hashlib.sha256(raw).hexdigest()[:16]

    @classmethod
    def create(
        cls,
        title: str,
        source: str,
        url: str,
        source_type: str = "rss",
        image: Optional[str] = None,
        published: Optional[datetime] = None,
        description: str = "",
    ) -> "MediaItem":
        return cls(
            id=cls.make_id(url, title),
            title=title.strip(),
            source=source,
            source_type=source_type,
            url=url,
            image=image,
            published=published or datetime.now(timezone.utc),
            description=(description or "").strip(),
        )
