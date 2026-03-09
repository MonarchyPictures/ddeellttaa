#!/usr/bin/env python3
"""Test SERPAPI integration"""

import asyncio
import logging
logging.basicConfig(level=logging.WARNING)

async def test_serpapi():
    print("=== Testing SERPAPI Scraper ===")
    
    from app.scrapers.serpapi_scraper import SerpAPIScraper
    scraper = SerpAPIScraper()
    
    # Check key is detected
    key = scraper._get_serpapi_key()
    print(f"Key detected: {bool(key)}")
    if key:
        print(f"Key prefix: {key[:20]}...")
    else:
        print("ERROR: Key not found!")
        return
    
    # Test search
    print()
    print("Testing search for 'tires' in Kenya...")
    results = await scraper.search("tires", "Kenya")
    
    print(f"Results returned: {len(results)}")
    if results:
        print()
        print("First 3 results:")
        for i, r in enumerate(results[:3]):
            print(f"  {i+1}. {r.get('title', 'N/A')[:60]}...")
            print(f"     Source: {r.get('source', 'N/A')}")
            print(f"     URL: {r.get('url', 'N/A')[:50]}...")
        print()
        print("SUCCESS: SERPAPI is working!")
    else:
        print("No results - check if key is valid or quota exceeded")

if __name__ == "__main__":
    asyncio.run(test_serpapi())
