
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.getcwd())

from app.scrapers.registry import get_active_scrapers_sorted, get_scraper_name

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def verify_scrapers():
    scrapers = get_active_scrapers_sorted()
    logger.info(f"Found {len(scrapers)} active scrapers.")
    
    queries = ["water tank", "car", "apartment"]
    location = "Nairobi, Kenya"
    
    results_summary = {}
    
    for scraper in scrapers:
        scraper_name = get_scraper_name(scraper)
        logger.info(f"Testing scraper: {scraper_name}")
        results_summary[scraper_name] = {}
        
        for query in queries:
            logger.info(f"  Querying: '{query}'")
            try:
                # Call search method (which includes circuit breaker)
                results = await scraper.search(query, location)
                count = len(results)
                logger.info(f"  Result: {count} items found.")
                results_summary[scraper_name][query] = count
            except Exception as e:
                logger.error(f"  Failed: {e}")
                results_summary[scraper_name][query] = f"Error: {str(e)}"

    print("\n\n=== VERIFICATION SUMMARY ===")
    all_passed = True
    for scraper_name, query_results in results_summary.items():
        print(f"Scraper: {scraper_name}")
        for query, count in query_results.items():
            status = "PASS" if isinstance(count, int) and count > 0 else "FAIL"
            print(f"  - {query}: {count} ({status})")
            if status == "FAIL":
                all_passed = False
                
    if all_passed:
        print("\nAll scrapers returned results for all queries. ✅")
    else:
        print("\nSome scrapers failed to return results. ❌")
        # Don't exit with error code yet, as we might not have API keys for some.

if __name__ == "__main__":
    asyncio.run(verify_scrapers())
