import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)

class GoogleScraper(BaseScraper): 
    source = "google" 

    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"GOOGLE: Scraping for {query}")
        # Build a simpler query for better recall on Google
        # We'll use the core query terms but relax the mandatory quotes slightly
        clean_query = query.replace('"', '')
        search_query = f'{clean_query} (site:facebook.com OR site:jiji.co.ke OR site:pigiame.co.ke)'
        
        url = f"https://www.google.com/search?q={search_query}" 
        
        # Use a more generic selector for waiting
        html = self.get_page_content(url, wait_selector="body")
        
        if not html:
            logger.warning("GOOGLE: No HTML content received")
            return []
 
        results = [] 
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        # Google search results are usually in 'div.g' or 'div.MjjYud'
        search_results = soup.select('div.g') or soup.select('div.MjjYud')
        logger.info(f"GOOGLE: Found {len(search_results)} result blocks")
        
        if len(search_results) == 0:
            logger.info(f"GOOGLE: Found 0 result blocks. HTML snippet: {html[:500]}...")
            # Try a broader fallback selector
            search_results = soup.select('div[data-hveid]')
            logger.info(f"GOOGLE: Fallback found {len(search_results)} potential result blocks")

        # Second Fallback: Just find all anchors with H3 (titles)
        if len(search_results) == 0:
             possible_links = soup.select('a:has(h3)')
             logger.info(f"GOOGLE: Second fallback found {len(possible_links)} links with titles")
             search_results = possible_links
        
        # Third Fallback: Basic HTML Google (links starting with /url?q=)
        if len(search_results) == 0:
             basic_links = soup.select('a[href^="/url?q="]')
             logger.info(f"GOOGLE: Third fallback found {len(basic_links)} basic links")
             search_results = basic_links

        for res in search_results:
            # If res is an anchor (from fallbacks), use it directly
            if res.name == 'a':
                link_tag = res
                # Try to find snippet in parent or near elements
                snippet_tag = None
                # For basic HTML, snippet might be in a div or font tag nearby
                # But keeping it simple for now
            else:
                link_tag = res.select_one('a')
                # Multiple possible snippet selectors
                snippet_tag = res.select_one('div.VwiC3b') or res.select_one('div.kb0u9b') or res.select_one('span.st') or res.select_one('.yD9P9') or res.select_one('.MUF3bd')
            
            if not link_tag:
                continue
            
            link = link_tag.get('href')
            if not link:
                continue
                
            # Clean up Google redirection links
            if "/url?q=" in link:
                try:
                    link = link.split("/url?q=")[1].split("&")[0]
                    import urllib.parse
                    link = urllib.parse.unquote(link)
                except:
                    pass
            
            title_tag = link_tag.select_one('h3') or link_tag
            title = title_tag.get_text(strip=True) if title_tag else "No Title"
            
            if snippet_tag:
                snippet = snippet_tag.get_text()
            else:
                snippet = title
            
            if not link or not snippet or not link.startswith('http'):
                continue

            if any(x in link for x in ["google.com", "gstatic.com", "youtube.com"]):
                continue

            logger.info(f"GOOGLE: Found potential lead at {link}")
            
            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=snippet,
                author="Google Search Result",
                contact=self.extract_contact_info(f"{snippet}"),
                location="Kenya",
                url=link,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results[:10]
