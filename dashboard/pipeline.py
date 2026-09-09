"""
Runs the full pipeline once: acquisition -> processing -> intelligence
-> Live Event Store. This is the single function the Hour 6 scheduler
will call every 2 minutes; for now the dashboard just calls it on startup.
"""
from __future__ import annotations
import logging

from acquisition.provider_manager import ProviderManager
from processing.normalizer import Normalizer
from processing.deduplicator import Deduplicator
from intelligence.classifier import Classifier
from intelligence.event_builder import EventBuilder
from dashboard import store

logger = logging.getLogger(__name__)

_provider_manager = None
_classifier = None


def run_cycle() -> int:
    """Runs one full fetch->build->store cycle. Returns event count."""
    global _provider_manager, _classifier
    if _provider_manager is None:
        _provider_manager = ProviderManager()
    if _classifier is None:
        _classifier = Classifier()

    logger.info("=== pipeline cycle starting ===")
    raw = _provider_manager.collect()
    normalized = Normalizer().normalize(raw)
    deduped = Deduplicator().deduplicate(normalized)
    clusters = _classifier.cluster(deduped)
    events = EventBuilder().build(clusters)

    store.replace_events(events)
    logger.info("=== pipeline cycle done: %d events live ===", len(events))
    return len(events)
