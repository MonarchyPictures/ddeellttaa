import logging
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)


class TelegramScraper(BaseScraper):
    source = "telegram"

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """
        Uses Google Dorks to find public Telegram channels/groups related to the query.
        """
        # Google Dork: site:t.me "Kenya" "iPhone 15" ("join" OR "channel" OR "group")
        search_query = f'site:t.me "Kenya" {query} ("join" OR "channel" OR "group" OR "buy" OR "sell")'
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://www.google.com/search?q={encoded_query}&gl=ke"

        logger.info(f"TELEGRAM: Searching: {url}")

        # Use BaseScraper's get_page_content (uses Playwright/Selenium internally)
        html = self.get_page_content(url, wait_selector="#search")
        if not html:
            logger.warning("TELEGRAM: No HTML content retrieved")
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        results = []
        for g in soup.select('div.g'):
            link_tag = g.select_one('a')
            if not link_tag:
                continue

            href = link_tag.get('href')
            if not href or "t.me" not in href:
                continue

            title_tag = g.select_one('h3')
            snippet_tag = g.select_one('.VwiC3b')

            title = title_tag.get_text(strip=True) if title_tag else "Telegram Channel"
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            # Extract channel/group name from URL if possible
            # e.g., https://t.me/kenya_market -> kenya_market
            channel_name = href.split("t.me/")[-1].split("?")[0]

            signal = ScraperSignal(
                source=self.source,
                text=f"{title} - {snippet}",
                title=title,
                author=f"@{channel_name}",
                contact={"phone": None, "whatsapp": None, "telegram": href, "email": None},
                location="Kenya",
                url=href,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())

        logger.info(f"TELEGRAM: Found {len(results)} channels/groups")
        return results
