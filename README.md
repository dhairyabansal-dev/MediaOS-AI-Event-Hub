# AI Event Hub (mediaos)

A live map of what's happening on the internet right now — no articles,
no opinions, no accounts. Just events, grouped from real-time media.

## Setup

```bash
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
playwright install chromium        # needed for the parliamentary-data provider
cp .env.example .env                # then fill in real values
```

Edit `.env`:
```
INSTAGRAM_LOGIN_USERNAME=...   # used ONLY for rare followee discovery — use a burner account
INSTAGRAM_LOGIN_PASSWORD=...
```

## Run

```bash
uvicorn dashboard.app:app --reload --port 8000
```

Open http://localhost:8000. On startup it runs one fetch cycle immediately,
then refreshes automatically every `FETCH_INTERVAL_SECONDS` (default 120s).

`main.py` is a standalone CLI smoke test for the pipeline (acquisition ->
processing -> intelligence) without the web server — useful when debugging
a specific layer:

```bash
python3 main.py
```

## Deploy

Needs a long-running process (not serverless) — the scheduler and
in-memory event store both depend on the process staying alive.
`Procfile` is set up for Render/Railway/Heroku-style platforms:

```
web: uvicorn dashboard.app:app --host 0.0.0.0 --port $PORT
```

Set the same env vars from `.env` in your host's dashboard/secrets manager.

## Sources (as configured — see config.py)

| Type | What | Notes |
|---|---|---|
| YouTube | 2 explicit channels + any discovered via creators' Instagram bios | official RSS feed, reliable |
| Instagram | 9 creator profiles, anonymous reads every cycle | fragile — Meta rate-limits anonymous scraping, expect intermittent 0-item cycles |
| Instagram (discovery) | followees of the 9 creators, logged-in, once per 24h | account-ban risk accepted; use a burner account |
| Press | sansad.in Lok Sabha bills, via headless Playwright | it's a JS SPA with no public API — selectors may need re-checking if the site's markup changes |

Blacklisted (never included): AAJTAK, ABP News, ANI, and any source labeled
just "RSS". Mainstream media/article headlines are out of scope entirely.

Priority topics (boosted in ranking, force-linked to each other): Jantar
Mantar, Protest, NEET, Cockroach Janta Party.

## What's NOT in this MVP (by design)

No login, accounts, comments, likes, database, article archives, AI
summaries, or search. Nothing here posts, tags, or emails anyone — it's
read-only.
