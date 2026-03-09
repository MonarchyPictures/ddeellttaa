#!/usr/bin/env python3
"""Test SERPAPI integration - simple version"""

import asyncio
import logging
import sys

# Suppress all logging
logging.basicConfig(level=logging.CRITICAL)

async def test_serpapi():
    print("=== Testing SERPAPI Scraper ===\n")
    
    from app.scrapers.serpapi_scraper import SerpAPIScraper
    scraper = SerpAPIScraper()
    
    # Check key is detected
    key = scraper._get_serpapi_key()
    print(f"SERPAPI Key detected: {bool(key)}")
    if key:
        print(f"Key prefix: {key[:20]}...")
    else:
        print("ERROR: Key not found!")
        return
    
    # Test search
    print("\nSearching for 'tires' in Kenya...")
    sys.stdout.reconfigure(encoding='utf-8')
    results = await scraper.search("tires", "Kenya")
    
    print(f"Results returned: {len(results)}")
    if results:
        print("\nFirst 3 results:")
        for i, r in enumerate(results[:3]):
            title = r.get('title', 'N/A')[:50] if r.get('title') else 'N/A'
            print(f"  {i+1}. {title}...")
        print("\nSUCCESS: SERPAPI is working!")
    else:
        print("\nNo results from SERPAPI - checking fallback...")
        # Fallback would have been used

if __name__ == "__main__":
    asyncio.run(test_serpapi())
