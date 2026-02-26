
import asyncio
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.engine.multi_source_scraper import MultiSourceScraper

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_scraper():
    scraper = MultiSourceScraper()
    
    query = "iPhone 15"
    location = "Kenya"
    
    plan = {
        "original_query": query,
        "location": location,
        "platforms": {
            "duckduckgo": [f'"{query}" {location}'],
            "google": [f'"{query}" {location}']
        }
    }
    
    print(f"Testing search for: {query} in {location}")
    results = await scraper.execute_search_plan(plan)
    
    print(f"Found {len(results)} results")
    for r in results[:3]:
        print(f"- {r.get('title')} ({r.get('url')})")

if __name__ == "__main__":
    asyncio.run(test_scraper())
