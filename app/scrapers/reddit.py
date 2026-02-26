import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class RedditScraper(BaseScraper): 
    source = "reddit" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"REDDIT: Scraping for {query}")
        
        # Check for location in query
        location_suffix = ""
        if "kenya" in query.lower() or "nairobi" in query.lower():
            location_suffix = "%20kenya"
            loc_name = "Kenya"
        else:
            loc_name = "Global"

        url = f"https://www.reddit.com/search/?q={query}{location_suffix}&t=day" 
        try:
            html = self.get_page_content(url, wait_selector='shreddit-post') 
        except Exception as e:
            logger.error(f"REDDIT: Failed to fetch page: {e}")
            html = None
        
        if not html:
            return []
 
        results = [] 
        # Using regex to find reddit post links
        posts = re.findall(r'href="(/r/[^/]+/comments/[^/]+/[^/]+/)"', html)
        
        for post_url in list(set(posts))[:10]: 
            full_url = f"https://www.reddit.com{post_url}"
            
            snippet = f"Reddit post about {query} in {loc_name}"
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=snippet,
                author="Reddit User",
                contact=self.extract_contact_info(f"{snippet} {full_url}"),
                location=loc_name,
                url=full_url,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results
