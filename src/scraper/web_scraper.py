from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

HSREPLAY_DECKS_URL = "https://hsreplay.net/decks/"


class HSReplayWebScraper:
    def __init__(self, base_url: str = HSREPLAY_DECKS_URL):
        self.base_url = base_url

    async def scrape_tier_list(self, format_type: str = "standard") -> list[dict]:
        from playwright.async_api import async_playwright
        url = f"{self.base_url}?hl=ko&gameType={'RANKED_STANDARD' if format_type == 'standard' else 'RANKED_WILD'}"
        pw = None
        try:
            pw = await async_playwright().start()
            browser = await pw.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            await page.goto(url, wait_until="networkidle")
            await page.wait_for_selector(".deck-tile", timeout=15000)

            deck_elements = await page.query_selector_all(".deck-tile")
            results = []
            for el in deck_elements:
                deck_data = await self._parse_deck_element(el)
                if deck_data:
                    results.append(deck_data)

            await page.close()
            await context.close()
            await browser.close()
            return results
        except Exception as e:
            logger.error("Playwright scraping failed: %s", e)
            return []
        finally:
            if pw:
                await pw.stop()

    @staticmethod
    async def _parse_deck_element(element) -> dict[str, Any] | None:
        try:
            name_el = await element.query_selector(".deck-name")
            winrate_el = await element.query_selector(".win-rate")
            games_el = await element.query_selector(".game-count")
            link_el = await element.query_selector("a")

            name = await name_el.inner_text() if name_el else "Unknown"
            winrate_text = await winrate_el.inner_text() if winrate_el else "0%"
            games_text = await games_el.inner_text() if games_el else "0"
            href = await link_el.get_attribute("href") if link_el else ""

            winrate = float(winrate_text.replace("%", "").strip())
            games = int(games_text.replace(",", "").strip())

            return {
                "name": name,
                "win_rate": winrate,
                "total_games": games,
                "url": href,
            }
        except Exception:
            return None
