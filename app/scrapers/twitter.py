import logging
import re
from datetime import datetime, timezone
from .base_scraper import BaseScraper, ScraperSignal

logger = logging.getLogger(__name__)
  
class TwitterScraper(BaseScraper): 
    source = "twitter" 
 
    def scrape(self, query: str, time_window_hours: int): 
        logger.info(f"TWITTER: Scraping for {query} in Kenya")
        # Note: Backticks in URL removed for proper formatting
        url = f"https://twitter.com/search?q={query}%20near:Kenya&f=live" 
        html = self.get_page_content(url, wait_selector='article[data-testid="tweet"]')
        
        if not html:
            return []
 
        results = [] 
        # Using regex to find tweet content blocks
        # This is a simplified extraction logic
        # tweets = re.findall(r'data-testid="tweetText">.*?>(.*?)</span>', html) 
        
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html, 'html.parser')
        
        articles = soup.select('article[data-testid="tweet"]')
        
        for article in articles[:10]:
            tweet_text_div = article.select_one('[data-testid="tweetText"]')
            if not tweet_text_div:
                continue
                
            tweet_text = tweet_text_div.get_text(strip=True)
            
            # Try to get user handle
            user_handle = "X User"
            user_div = article.select_one('[data-testid="User-Name"]')
            if user_div:
                user_handle = user_div.get_text(strip=True)

            # 🎯 DUMB SCRAPER: Standardized Signal Output
            signal = ScraperSignal(
                source=self.source,
                text=tweet_text,
                author=user_handle,
                contact=self.extract_contact_info(f"{tweet_text} {url}"),
                location="Kenya",
                url=url,
                timestamp=datetime.now(timezone.utc).isoformat()
            )
            results.append(signal.model_dump())
 
        return results
