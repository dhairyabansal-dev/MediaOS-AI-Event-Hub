"""
Hour 1 + 2 entry point.
Hour 1: proves models/config work.
Hour 2: proves the acquisition layer (all 4 providers) runs end-to-end
and returns real MediaItems.
"""
import logging
from models.media import MediaItem
from models.event import Event
import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")


def smoke_test():
    print("== AI Event Hub / mediaos — Hour 1 smoke test ==")
    print(f"Fetch interval: {config.FETCH_INTERVAL_SECONDS}s")
    print(f"Max media/cycle: {config.MAX_MEDIA_PER_CYCLE}")
    print(f"Max events: {config.MAX_EVENTS}")

    m1 = MediaItem.create(
        title="Apple unveils AI",
        source="TechCrunch",
        url="https://example.com/apple-ai",
        source_type="rss",
        description="Apple announced new AI features today.",
    )
    m2 = MediaItem.create(
        title="Apple WWDC keynote recap",
        source="YouTube:Apple",
        url="https://example.com/apple-wwdc",
        source_type="youtube",
        image="https://example.com/thumb.jpg",
    )

    event = Event.from_media(title="Apple AI Announcement", media=[m1, m2], score=0.91)

    print("\nBuilt Event:")
    print(f"  id: {event.id}")
    print(f"  title: {event.title}")
    print(f"  media_count: {event.media_count}")
    print(f"  source_counts: {event.source_counts}")
    print(f"  thumbnail: {event.thumbnail}")

    assert event.media_count == 2
    assert event.source_counts == {"rss": 1, "youtube": 1}
    print("\n✅ Hour 1 skeleton OK — models + config working.")


def run_acquisition():
    from acquisition.provider_manager import ProviderManager

    print("\n== Hour 2: acquisition layer ==")
    manager = ProviderManager()
    items = manager.collect()
    print(f"\nCollected {len(items)} media items this cycle.")
    for m in items[:10]:
        print(f"  [{m.source_type:9s}] {m.source:25s} | {m.title}")
    if len(items) > 10:
        print(f"  ... and {len(items) - 10} more")
    return items


def run_processing(items):
    from processing.normalizer import Normalizer
    from processing.deduplicator import Deduplicator

    print("\n== Hour 3: processing layer ==")
    normalized = Normalizer().normalize(items)
    deduped = Deduplicator().deduplicate(normalized)
    print(f"Raw: {len(items)} -> Normalized: {len(normalized)} -> Deduped: {len(deduped)}")
    return deduped


def run_intelligence(items):
    from intelligence.classifier import Classifier
    from intelligence.event_builder import EventBuilder

    print("\n== Hour 4: intelligence layer ==")
    clusters = Classifier().cluster(items)
    events = EventBuilder().build(clusters)
    print(f"{len(items)} media -> {len(clusters)} clusters -> {len(events)} events")
    for e in events[:10]:
        print(f"  score={e.score:5.2f} | media={e.media_count} | {e.title}")
    return events


if __name__ == "__main__":
    smoke_test()
    raw_items = run_acquisition()
    processed_items = run_processing(raw_items)
    run_intelligence(processed_items)
