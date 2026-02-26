import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class GoogleMapsScraper(BaseScraper): 
    source = "google_maps" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"GOOGLE_MAPS: Scraping for {query}")
        
        # FORCE KENYA LOCATION
        if "kenya" not in query.lower() and "nairobi" not in query.lower():
             search_query = f"{query} Kenya"
        else:
             search_query = query
             
        loc_name = "Kenya"

        # USE DUCKDUCKGO TO FIND GOOGLE MAPS RESULTS (Avoids Google Blocking)
        try:
            from ddgs import DDGS
        except ImportError:
            logger.error("DDGS package missing")
            return []

        search_terms = [
            f"{search_query} site:google.com/maps",
            f"{search_query} site:maps.google.com",
            f"{search_query} site:maps.app.goo.gl",
            f"{search_query} site:goo.gl/maps",
            f"{search_query} \"Google Maps\"",
            f"{search_query} maps",
            f"car dealer {search_query} maps",
            f"water tank supplier {search_query} maps"
        ]
        if "apartment" in search_query.lower():
            search_terms.extend([
                f"apartment complex {search_query} maps",
                f"apartments {search_query} site:google.com/maps"
            ])
        logger.info(f"GOOGLE_MAPS: Searching via DDG: {search_terms[0]}")
        
        results = []
        for term in search_terms:
            try:
                results = list(DDGS().text(term, region='ke-en', max_results=10))
            except Exception as e:
                logger.error(f"GOOGLE_MAPS: DDG Search failed for '{term}': {e}")
                results = []
            if results:
                break

        if not results:
            for term in search_terms:
                try:
                    results = list(DDGS().text(term, region='wt-wt', max_results=10, backend='html'))
                except Exception:
                    results = []
                if results:
                    break

        if not results:
            fallback_terms = [f"{search_query} Kenya", search_query]
            for term in fallback_terms:
                try:
                    results = list(DDGS().text(term, region='ke-en', max_results=10))
                except Exception:
                    results = []
                if results:
                    break
            if not results:
                for term in fallback_terms:
                    try:
                        results = list(DDGS().text(term, region='wt-wt', max_results=10, backend='html'))
                    except Exception:
                        results = []
                    if results:
                        break

        signals = [] 
        for r in results:
            title = r.get('title', 'Unknown Business')
            link = r.get('href', '')
            snippet = r.get('body', '')
            
            # Clean business name
            biz_name = title.split("- Google Maps")[0].strip()
            if "Google Maps" in biz_name: biz_name = biz_name.replace("Google Maps", "").strip()
            
            full_text = f"{title} {snippet}"
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=full_text,
                title=biz_name,
                author=biz_name,
                contact=self.extract_contact_info(f"{full_text} {link}"),
                location=loc_name,
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            signals.append(signal.model_dump())
 
        return signals
