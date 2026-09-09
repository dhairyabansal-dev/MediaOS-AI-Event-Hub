"""
Instagram provider — LOGGED-IN session, by explicit user choice, so we can
discover "who they follow" (anonymous mode cannot see followee lists at all,
which is why this switched from the earlier anonymous-only approach).

Reality check (kept here so future-you remembers, not just in chat):
- Logging in raises the account-ban risk substantially vs anonymous reads.
  Use a secondary/burner account, not a personal one, if at all possible.
- Followee discovery is the expensive, risky operation — it is NOT run
  every 2-minute cycle. It runs once per INSTAGRAM_DISCOVERY_REFRESH_HOURS
  and caches the resulting usernames to disk. Regular fetch cycles only
  read post data for the (seed + cached-discovered) username list.
- Every discovered account is tagged with which seed creator's network it
  came from, and every MediaItem keeps the real post author — that's the
  "recognition" hook the dashboard will render in Hour 5.
"""
from __future__ import annotations
import json
import logging
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import List

from acquisition.providers.base import Provider
from models.media import MediaItem
import config

logger = logging.getLogger(__name__)

POSTS_PER_SEED_PER_CYCLE = 5
POSTS_PER_DISCOVERED_PER_CYCLE = 2
DISCOVERY_CACHE_PATH = Path(__file__).parent / ".instagram_followee_cache.json"


class InstagramProvider(Provider):
    name = "instagram"

    def __init__(self, sources: List[dict] | None = None):
        self.seed_sources = sources if sources is not None else config.INSTAGRAM_SOURCES
        self._anon_loader = None
        self._auth_loader = None
        self._discovery_cache = self._load_discovery_cache()

    # -- sessions -----------------------------------------------------------

    def _get_anon_loader(self):
        """Used for regular post reads on public profiles — no login, run
        every 2-min cycle. This is the low-risk, high-frequency path."""
        if self._anon_loader is not None:
            return self._anon_loader

        import instaloader
        self._anon_loader = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )
        return self._anon_loader

    def _get_auth_loader(self):
        """Used ONLY for followee discovery, which itself only runs once
        per INSTAGRAM_DISCOVERY_REFRESH_HOURS — this is the risky, rare
        path, kept isolated from the frequent anonymous fetch path so a
        login problem never blocks the regular 2-min cycle."""
        if self._auth_loader is not None:
            return self._auth_loader

        import instaloader
        L = instaloader.Instaloader(
            download_pictures=False,
            download_videos=False,
            download_video_thumbnails=False,
            download_geotags=False,
            download_comments=False,
            save_metadata=False,
            compress_json=False,
            quiet=True,
        )

        session_path = Path(config.INSTAGRAM_SESSION_FILE)
        username = config.INSTAGRAM_LOGIN_USERNAME

        if not username or not config.INSTAGRAM_LOGIN_PASSWORD:
            logger.error(
                "InstagramProvider: INSTAGRAM_LOGIN_USERNAME/PASSWORD not set in "
                "environment — followee discovery will fail. Set them in your local .env."
            )
            self._auth_loader = L
            return self._auth_loader

        try:
            if session_path.exists():
                L.load_session_from_file(username, str(session_path))
            else:
                L.login(username, config.INSTAGRAM_LOGIN_PASSWORD)
                L.save_session_to_file(str(session_path))
        except Exception as e:
            logger.error("InstagramProvider: login failed: %s", e)

        self._auth_loader = L
        return self._auth_loader

    # -- followee discovery (rare, cached) ----------------------------------

    def _load_discovery_cache(self) -> dict:
        if DISCOVERY_CACHE_PATH.exists():
            try:
                return json.loads(DISCOVERY_CACHE_PATH.read_text())
            except Exception:
                return {}
        return {}

    def _save_discovery_cache(self) -> None:
        try:
            DISCOVERY_CACHE_PATH.write_text(json.dumps(self._discovery_cache, indent=2))
        except Exception as e:
            logger.warning("InstagramProvider: failed to write discovery cache: %s", e)

    def _discovery_is_stale(self, seed_username: str) -> bool:
        entry = self._discovery_cache.get(seed_username)
        if not entry:
            return True
        age_hours = (time.time() - entry.get("fetched_at", 0)) / 3600
        return age_hours >= config.INSTAGRAM_DISCOVERY_REFRESH_HOURS

    def _discover_followees(self, seed: dict) -> List[dict]:
        """Returns discovered accounts as [{'name': ..., 'username': ..., 'via': seed_name}]."""
        if not config.INSTAGRAM_DISCOVER_FOLLOWEES:
            return []

        seed_username = seed["username"]
        if not self._discovery_is_stale(seed_username):
            cached = self._discovery_cache[seed_username]["followees"]
            return [{"name": u, "username": u, "via": seed["name"]} for u in cached]

        try:
            import instaloader
            L = self._get_auth_loader()
            profile = instaloader.Profile.from_username(L.context, seed_username)
            followees = []
            for i, followee in enumerate(profile.get_followees()):
                if i >= config.INSTAGRAM_MAX_FOLLOWEES_PER_SEED:
                    break
                followees.append(followee.username)

            self._discovery_cache[seed_username] = {
                "fetched_at": time.time(),
                "followees": followees,
            }
            self._save_discovery_cache()
            logger.info(
                "InstagramProvider: discovered %d followees for @%s",
                len(followees), seed_username,
            )
            return [{"name": u, "username": u, "via": seed["name"]} for u in followees]
        except Exception as e:
            logger.warning(
                "InstagramProvider: followee discovery failed for @%s: %s",
                seed_username, e,
            )
            cached = self._discovery_cache.get(seed_username, {}).get("followees", [])
            return [{"name": u, "username": u, "via": seed["name"]} for u in cached]

    def discover_youtube_channel(self, username: str) -> str | None:
        """Best-effort: reads a public profile's bio external_url and returns
        it if it looks like a YouTube channel/handle link. Uses the anonymous
        loader — bio/external_url is public profile data, no login needed.
        Returns None if no YouTube link is found (common — most bios link
        Linktree, not YouTube directly)."""
        try:
            import instaloader
            L = self._get_anon_loader()
            profile = instaloader.Profile.from_username(L.context, username)
            url = (profile.external_url or "").strip()
            if "youtube.com" in url or "youtu.be" in url:
                return url
            return None
        except Exception as e:
            logger.warning("InstagramProvider: bio YouTube lookup failed for %s: %s", username, e)
            return None

    # -- fetch ---------------------------------------------------------------

    def fetch(self) -> List[MediaItem]:
        items: List[MediaItem] = []

        for seed in self.seed_sources:
            try:
                items.extend(self._fetch_profile(seed, limit=POSTS_PER_SEED_PER_CYCLE))
            except Exception as e:
                logger.warning("InstagramProvider: failed on seed %s: %s", seed.get("username"), e)

        seen_usernames = {s["username"] for s in self.seed_sources}
        for seed in self.seed_sources:
            for discovered in self._discover_followees(seed):
                if discovered["username"] in seen_usernames:
                    continue
                seen_usernames.add(discovered["username"])
                try:
                    items.extend(
                        self._fetch_profile(discovered, limit=POSTS_PER_DISCOVERED_PER_CYCLE)
                    )
                except Exception as e:
                    logger.warning(
                        "InstagramProvider: failed on discovered %s: %s",
                        discovered.get("username"), e,
                    )

        return items

    def _fetch_profile(self, src: dict, limit: int) -> List[MediaItem]:
        import instaloader

        L = self._get_anon_loader()
        profile = instaloader.Profile.from_username(L.context, src["username"])

        via = src.get("via")
        source_label = f"Instagram:{src['name']}"
        if via:
            source_label += f" (via {via}'s network)"

        out: List[MediaItem] = []
        for i, post in enumerate(profile.get_posts()):
            if i >= limit:
                break

            caption = (post.caption or "").strip()
            title = caption.splitlines()[0][:140] if caption else f"New post from {src['name']}"
            url = f"https://www.instagram.com/p/{post.shortcode}/"
            published = post.date_utc.replace(tzinfo=timezone.utc) if post.date_utc else datetime.now(timezone.utc)

            out.append(
                MediaItem.create(
                    title=title,
                    source=source_label,
                    url=url,
                    source_type="instagram",
                    image=post.url,
                    published=published,
                    description=caption,
                )
            )
        return out
