import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class FacebookMarketplaceScraper(BaseScraper): 
    source = "facebook" 
    
    def _fallback_ddg(self, query: str):
        try:
            from ddgs import DDGS
        except Exception as e:
            logger.error(f"FACEBOOK: DDG import failed: {e}")
            return []

        ddg_queries = [
            f'site:facebook.com/groups "{query}" "looking for" Kenya',
            f'facebook groups {query} Kenya',
            f'site:facebook.com "{query}" Kenya',
            'site:facebook.com/groups kenya buy sell',
            'facebook groups kenya buy sell',
            f'site:facebook.com/groups {query} Kenya',
            'site:facebook.com/groups car Kenya',
            'facebook group car Kenya'
        ]

        ddg_results = []
        for q in ddg_queries:
            try:
                ddg_results = list(DDGS().text(q, region='ke-en', max_results=15))
            except Exception as e:
                logger.error(f"FACEBOOK: DDG search failed for '{q}': {e}")
                ddg_results = []
            if not ddg_results:
                try:
                    ddg_results = list(DDGS().text(q, region='ke-en', max_results=15, backend='html'))
                except Exception:
                    ddg_results = []
            if ddg_results:
                break
        
        if not ddg_results:
            generic_queries = [f"{query} Kenya", query]
            for q in generic_queries:
                try:
                    ddg_results = list(DDGS().text(q, region='ke-en', max_results=15))
                except Exception:
                    ddg_results = []
                if not ddg_results:
                    try:
                        ddg_results = list(DDGS().text(q, region='wt-wt', max_results=15, backend='html'))
                    except Exception:
                        ddg_results = []
                if ddg_results:
                    break

        results = []
        for item in ddg_results:
            title = item.get('title', '')
            body = item.get('body', '')
            href = item.get('href', '')
            text = f"{title} {body}".strip()
            if not text:
                continue
            signal = ScraperSignal(
                source=self.source,
                text=text,
                author="Facebook User",
                contact=self.extract_contact_info(f"{text} {href}"),
                location="Kenya",
                url=href,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
        return results

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"FACEBOOK: Scraping for {query}")
        
        # FORCE KENYA LOCATION + BUYER INTENT
        # The user explicitly requested to lock to Kenya AND exclude sellers.
        # Facebook Marketplace is mostly sellers, so we must be very specific in the query.
        # Adding "wanted" or "looking for" in the query string itself.
        search_query = f"{query} looking for wanted"
        url = f"https://www.facebook.com/marketplace/nairobi/search?query={search_query}"
        location_name = "Kenya"
        
        html = self.get_page_content(url, wait_selector="div[role='feed']") 
        
        if not html:
            return self._fallback_ddg(query)
 
        results = [] 
        # items = re.findall(r'/marketplace/item/\d+', html) 
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Facebook marketplace items are usually in a feed
        # Selectors change frequently, so we use a broad approach + regex for links
        links = soup.find_all('a', href=re.compile(r'/marketplace/item/\d+'))
        
        processed_links = set()

        for link_tag in links[:10]: 
            href = link_tag.get('href')
            if not href or href in processed_links:
                continue
            
            processed_links.add(href)
            link = f"https://www.facebook.com{href}"
            
            # Try to extract text from the link tag or parent
            text = link_tag.get_text(strip=True)
            
            # If text is empty, look for parent text (often the link wraps an image and text is sibling or parent)
            if not text:
                parent = link_tag.find_parent('div')
                if parent:
                    text = parent.get_text(strip=True)
            
            if not text:
                continue

            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=text,
                author="Facebook User",
                contact=self.extract_contact_info(f"{text} {link}"),
                location=location_name,
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results if results else self._fallback_ddg(query)
