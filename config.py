import os
from dotenv import load_dotenv

load_dotenv()

# --- Runtime ---
FETCH_INTERVAL_SECONDS = int(os.getenv("FETCH_INTERVAL_SECONDS", 120))   # every 2 min
MAX_MEDIA_PER_CYCLE = int(os.getenv("MAX_MEDIA_PER_CYCLE", 200))
MAX_EVENTS = int(os.getenv("MAX_EVENTS", 30))

# --- Deduplication ---
DEDUP_FUZZY_THRESHOLD = int(os.getenv("DEDUP_FUZZY_THRESHOLD", 92))  # rapidfuzz score 0-100

# --- Clustering ---
CLUSTER_SIMILARITY_THRESHOLD = float(os.getenv("CLUSTER_SIMILARITY_THRESHOLD", 0.55))
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2")

# --- Priority topics ---
# Events matching these (case-insensitive substring against title/description)
# get a score boost in the Hour 4 event builder, so they surface near the
# top of the dashboard even with fewer media items than other clusters.
PRIORITY_TOPICS: list[str] = [
    "Jantar Mantar",
    "Protest",
    "NEET",
    "Cockroach Janta Party",
]

# --- Forced links ---
# Each inner list is a group of phrases whose matching items get merged
# into ONE event regardless of similarity score — overrides the
# classifier's normal clustering for these specific topics.
FORCED_LINK_GROUPS: list[list[str]] = [
    ["Jantar Mantar", "NEET"],
]

# --- Blacklist ---
# Source names that must NEVER appear in results, regardless of which
# provider they'd come through. Matched case-insensitively against
# MediaItem.source (substring match, so "ABP News Hindi" is also blocked).
SOURCE_BLACKLIST: list[str] = [
    "AAJTAK",
    "ABP NEWS",
    "ANI",
]

# --- Sources ---
# Only sources explicitly approved by the user are listed here.
# Do not add new sources without asking first.

# Plain RSS-native feeds (none provided yet — add real blog/news RSS URLs here)
RSS_SOURCES: list[dict] = []

# YouTube channels, referenced by @handle (channel_id is resolved at runtime
# and cached, since YouTube's RSS endpoint requires the UC... channel id)
YOUTUBE_SOURCES: list[dict] = [
    {"name": "PeekTV", "handle": "PeekTVOfficial"},
    {"name": "Shyam Meera Singh", "handle": "ShyamMeeraSingh1"},
]

# Instagram profiles to scrape (seed accounts — logged-in session, see below)
INSTAGRAM_SOURCES: list[dict] = [
    {"name": "PeekTV", "username": "peektv_in"},
    {"name": "Shyam Meera Singh", "username": "shyammeerasingh"},
    {"name": "Priyanshay", "username": "priyanshay"},
    {"name": "The News Pinch", "username": "abhinavpinch"},
    {"name": "Dehat Adda", "username": "dehatadda"},
    {"name": "Strike Originals", "username": "strikeoriginals"},
    {"name": "KK Create", "username": "kk.create"},
    {"name": "Milan Sirr", "username": "milan_sirr"},
    {"name": "RJ Raghav", "username": "rjraghav"},
]

# Instagram now runs a LOGGED-IN session (accepted account-ban risk) so that
# followee ("who they follow") discovery is possible — anonymous mode can't
# see following lists. Credentials must come from environment variables,
# NEVER hardcoded here. Put them in a local .env (gitignored):
#   INSTAGRAM_LOGIN_USERNAME=...
#   INSTAGRAM_LOGIN_PASSWORD=...
INSTAGRAM_LOGIN_USERNAME = os.getenv("INSTAGRAM_LOGIN_USERNAME", "")
INSTAGRAM_LOGIN_PASSWORD = os.getenv("INSTAGRAM_LOGIN_PASSWORD", "")
INSTAGRAM_SESSION_FILE = os.getenv("INSTAGRAM_SESSION_FILE", ".instaloader_session")

# Followee discovery — expensive + carries ban risk, so it does NOT run
# every 2-min cycle. It runs once per refresh window and caches results.
INSTAGRAM_DISCOVER_FOLLOWEES = os.getenv("INSTAGRAM_DISCOVER_FOLLOWEES", "true").lower() == "true"
INSTAGRAM_MAX_FOLLOWEES_PER_SEED = int(os.getenv("INSTAGRAM_MAX_FOLLOWEES_PER_SEED", 15))
INSTAGRAM_DISCOVERY_REFRESH_HOURS = int(os.getenv("INSTAGRAM_DISCOVERY_REFRESH_HOURS", 24))

# Parliamentary data — sansad.in is a JS SPA with no public API/RSS,
# so this provider drives a real headless browser (Playwright) instead
# of a plain HTTP scrape.
PRESS_SOURCES: list[dict] = [
    {
        "name": "Lok Sabha Bills (sansad.in)",
        "url": "https://sansad.in/ls/legislation/bills",
        "house": "Lok Sabha",
    },
]
