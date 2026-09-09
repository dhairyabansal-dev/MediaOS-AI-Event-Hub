"""
Provider interface. Every acquisition provider (rss, youtube, instagram,
press, ...) implements `fetch()` and returns a list[MediaItem].
This is the seam that keeps sources swappable.
"""
from __future__ import annotations
from abc import ABC, abstractmethod
from typing import List
from models.media import MediaItem


class Provider(ABC):
    name: str = "base"

    @abstractmethod
    def fetch(self) -> List[MediaItem]:
        """Fetch latest items from this source. Must not raise on
        individual-item failures — log and skip instead, so one bad
        feed/profile doesn't kill the whole cycle."""
        raise NotImplementedError
