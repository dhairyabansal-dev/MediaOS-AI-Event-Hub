"""
Web Dashboard. No login, no accounts, no search (per spec) — just the
live event feed and a detail view per event, grouped by media type.
"""
from __future__ import annotations
import logging
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from dashboard import store
from dashboard.pipeline import run_cycle
from acquisition.scheduler import start_scheduler, stop_scheduler
import config

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).parent
app = FastAPI(title="AI Event Hub")
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def _is_priority(event) -> bool:
    topics = [t.lower() for t in config.PRIORITY_TOPICS]
    text = f"{event.title} {' '.join(m.description or '' for m in event.media)}".lower()
    return any(t in text for t in topics)


def _humanize_age(dt) -> str:
    from datetime import datetime, timezone
    if dt is None:
        return ""
    seconds = (datetime.now(timezone.utc) - dt).total_seconds()
    if seconds < 60:
        return "just now"
    minutes = int(seconds // 60)
    if minutes < 60:
        return f"{minutes}m ago"
    hours = int(minutes // 60)
    if hours < 24:
        return f"{hours}h ago"
    return f"{int(hours // 24)}d ago"


def _decorate(events):
    decorated = []
    for e in events:
        decorated.append({
            "event": e,
            "is_priority": _is_priority(e),
            "age": _humanize_age(e.updated_at),
        })
    return decorated


@app.on_event("startup")
def on_startup():
    # Run once synchronously so the dashboard isn't empty on first load,
    # then hand off to the scheduler for every-2-min refreshes.
    try:
        run_cycle()
    except Exception as e:
        logger.error("Initial pipeline run failed: %s", e)
    start_scheduler(run_cycle)


@app.on_event("shutdown")
def on_shutdown():
    stop_scheduler()


@app.get("/api/health")
def health():
    last = store.last_updated()
    return {
        "status": "ok",
        "last_updated": last.isoformat() if last else None,
        "event_count": len(store.get_events()),
        "fetch_interval_seconds": config.FETCH_INTERVAL_SECONDS,
    }


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    events = store.get_events()
    cards = _decorate(events)
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "cards": cards,
            "ticker_items": [c["event"].title for c in cards[:8]],
            "last_updated": store.last_updated(),
        },
    )


@app.get("/event/{event_id}", response_class=HTMLResponse)
def event_detail(request: Request, event_id: str):
    event = store.get_event(event_id)
    if event is None:
        return templates.TemplateResponse(
            "not_found.html", {"request": request, "event_id": event_id}, status_code=404
        )

    grouped: dict[str, list] = {}
    for m in event.media:
        grouped.setdefault(m.source_type, []).append(m)

    return templates.TemplateResponse(
        "event.html",
        {"request": request, "event": event, "grouped": grouped, "is_priority": _is_priority(event)},
    )


@app.get("/api/events")
def api_events():
    events = store.get_events()
    return JSONResponse(
        {
            "last_updated": store.last_updated().isoformat() if store.last_updated() else None,
            "events": [
                {
                    "id": e.id,
                    "title": e.title,
                    "thumbnail": e.thumbnail,
                    "score": e.score,
                    "media_count": e.media_count,
                    "source_counts": e.source_counts,
                    "is_priority": _is_priority(e),
                }
                for e in events
            ],
        }
    )


@app.post("/api/refresh")
def api_refresh():
    """Manual refresh trigger — useful for testing without waiting 2 min."""
    count = run_cycle()
    return {"events": count}
