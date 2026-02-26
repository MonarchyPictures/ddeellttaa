import logging
import urllib.parse
from datetime import datetime, timezone
from typing import List, Dict, Any
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)


class KenyanForumsScraper(BaseScraper):
    source = "kenyan_forums"

    def scrape(self, query: str, time_window_hours: int) -> List[Dict[str, Any]]:
        """
        Uses Google Dorks to search popular Kenyan forums.
        """
        forums = [
            "wazua.co.ke",
            "kenyatalk.com",
            "jamiiforums.com",
            "skyscrapercity.com",  # Kenya section often active
            "kilimani.co.ke"
        ]
        
        site_dork = " OR ".join([f"site:{site}" for site in forums])
        search_query = f'({site_dork}) {query} ("looking for" OR "want to buy" OR "budget" OR "natafuta")'
        encoded_query = urllib.parse.quote(search_query)
        url = f"https://www.google.com/search?q={encoded_query}&gl=ke"

        logger.info(f"FORUMS: Searching: {url}")

        html = self.get_page_content(url, wait_selector="#search")
        if not html:
            logger.warning("FORUMS: No HTML content retrieved")
            return []

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')

        results = []
        for g in soup.select('div.g'):
            link_tag = g.select_one('a')
            if not link_tag:
                continue

            href = link_tag.get('href')
            if not href:
                continue

            # Check if it matches one of our target forums
            if not any(forum in href for forum in forums):
                continue

            title_tag = g.select_one('h3')
            snippet_tag = g.select_one('.VwiC3b')

            title = title_tag.get_text(strip=True) if title_tag else "Forum Post"
            snippet = snippet_tag.get_text(strip=True) if snippet_tag else ""

            # Determine specific forum source
            forum_source = "Unknown Forum"
            for forum in forums:
                if forum in href:
                    forum_source = forum
                    break

            signal = ScraperSignal(
                source=self.source,
                text=f"{title} - {snippet}",
                title=title,
                author=forum_source,
                contact={"phone": None, "whatsapp": None, "email": None},
                location="Kenya",
                url=href,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())

        logger.info(f"FORUMS: Found {len(results)} discussions")
        return results
