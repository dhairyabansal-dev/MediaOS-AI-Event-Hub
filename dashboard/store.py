"""
Live Event Store: the in-memory hand-off between the intelligence layer
and the dashboard. Every fetch cycle REPLACES the whole list — no history,
no database, matching the "just live events" spec.
"""
from __future__ import annotations
import threading
from datetime import datetime, timezone
from typing import List, Optional

from models.event import Event

_lock = threading.Lock()
_events: List[Event] = []
_last_updated: Optional[datetime] = None


def replace_events(new_events: List[Event]) -> None:
    global _events, _last_updated
    with _lock:
        _events = new_events
        _last_updated = datetime.now(timezone.utc)


def get_events() -> List[Event]:
    with _lock:
        return list(_events)


def get_event(event_id: str) -> Optional[Event]:
    with _lock:
        for e in _events:
            if e.id == event_id:
                return e
    return None


def last_updated() -> Optional[datetime]:
    with _lock:
        return _last_updated
