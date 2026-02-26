import sys
import os
import asyncio
from concurrent.futures import ThreadPoolExecutor

# Add project root to path
sys.path.append(os.getcwd())

from app.scrapers.duckduckgo import DuckDuckGoScraper
from app.scrapers.jiji import JijiScraper
from app.scrapers.google_cse import GoogleCSEScraper
from app.scrapers.facebook_marketplace import FacebookMarketplaceScraper
from app.scrapers.google_maps import GoogleMapsScraper
from app.scrapers.whatsapp_public_groups import WhatsAppPublicGroupScraper
from app.scrapers.serpapi_scraper import SerpAPIScraper

def run_scraper_test_sync(scraper_cls, name, queries):
    print(f"\n--- Testing {name} ---")
    try:
        scraper = scraper_cls()
    except Exception as e:
        print(f"❌ Could not initialize {name}: {e}")
        return False
        
    all_passed = True
    
    for query in queries:
        try:
            print(f"Querying '{query}'...")
            # Try passing time_window_hours to all, as most seem to require it
            try:
                results = scraper.scrape(query, time_window_hours=24)
            except TypeError:
                # Fallback if it doesn't accept time_window_hours
                results = scraper.scrape(query)
                 
            count = len(results)
            if count > 0:
                print(f"✅ {name} returned {count} results for '{query}'")
            else:
                print(f"❌ {name} returned 0 results for '{query}'")
                all_passed = False
        except Exception as e:
            print(f"❌ {name} raised exception for '{query}': {e}")
            all_passed = False
            
    return all_passed

async def main():
    queries = ["water tank", "car", "apartment"]
    
    # List of scrapers to test
    scrapers = [
        (DuckDuckGoScraper, "DuckDuckGo"),
        (JijiScraper, "Jiji"),
        (GoogleCSEScraper, "GoogleCSE"), 
        (FacebookMarketplaceScraper, "Facebook"), 
        (GoogleMapsScraper, "GoogleMaps"),
        (WhatsAppPublicGroupScraper, "WhatsApp"),
        (SerpAPIScraper, "SerpApi") 
    ]
    
    loop = asyncio.get_running_loop()
    with ThreadPoolExecutor() as pool:
        for cls, name in scrapers:
            await loop.run_in_executor(pool, run_scraper_test_sync, cls, name, queries)

if __name__ == "__main__":
    asyncio.run(main())
