"""
Press provider — parliamentary data from sansad.in.

sansad.in/ls/legislation/bills is a client-side rendered SPA (React).
The raw HTML has no data in it (confirmed) — the table only populates
after JS runs and calls an internal API following a filter action.
There's no public JSON API or RSS to hit directly, so this provider
drives a real headless browser instead of doing a plain HTTP scrape.

⚠️ Selector note: the exact table/row CSS selectors below are based on
the page's rendered structure at the time this was written. Since it's
a SPA, Digital Sansad can change its front-end markup without notice —
if this provider starts returning 0 rows, re-check selectors with
your browser's DevTools (Inspect Element on the bills table) before
assuming the pipeline itself is broken.
"""
from __future__ import annotations
import logging
from datetime import datetime, timezone
from typing import List

from acquisition.providers.base import Provider
from models.media import MediaItem
import config

logger = logging.getLogger(__name__)


class PressProvider(Provider):
    name = "press"

    def __init__(self, sources: List[dict] | None = None):
        # each source: {"name": ..., "url": "https://sansad.in/ls/legislation/bills", "house": "Lok Sabha"}
        self.sources = sources if sources is not None else config.PRESS_SOURCES

    def fetch(self) -> List[MediaItem]:
        items: List[MediaItem] = []
        for src in self.sources:
            try:
                items.extend(self._fetch_one(src))
            except Exception as e:
                logger.warning("PressProvider: failed on %s: %s", src.get("name"), e)
        return items

    def _fetch_one(self, src: dict) -> List[MediaItem]:
        # Imported lazily so the rest of the app works even before
        # `playwright install chromium` has been run.
        from playwright.sync_api import sync_playwright

        out: List[MediaItem] = []

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(user_agent="Mozilla/5.0")
            page.goto(src["url"], wait_until="networkidle", timeout=30000)

            # Trigger the default filter so the table actually populates.
            try:
                page.click("text=Filter", timeout=5000)
                page.wait_for_timeout(2000)  # let the API response render
            except Exception:
                pass  # some views may auto-load without needing the click

            rows = page.query_selector_all("table tbody tr")
            for row in rows:
                cells = [c.inner_text().strip() for c in row.query_selector_all("td")]
                if not cells or all(c == "" for c in cells):
                    continue  # skip the "no data available" placeholder row

                bill_number = cells[0] if len(cells) > 0 else ""
                short_title = cells[1] if len(cells) > 1 else ""
                ministry = cells[2] if len(cells) > 2 else ""
                intro_date = cells[4] if len(cells) > 4 else ""

                if not short_title:
                    continue

                out.append(
                    MediaItem.create(
                        title=short_title,
                        source=src["name"],
                        url=src["url"],
                        source_type="press",
                        published=self._parse_date(intro_date),
                        description=f"Bill {bill_number} · {ministry} · {src.get('house', '')}".strip(" ·"),
                    )
                )

            browser.close()

        return out

    @staticmethod
    def _parse_date(raw: str) -> datetime:
        for fmt in ("%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(raw.strip(), fmt).replace(tzinfo=timezone.utc)
            except Exception:
                continue
        return datetime.now(timezone.utc)
