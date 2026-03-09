#!/usr/bin/env python3
"""
Test the fixed pipeline
"""

import asyncio
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.WARNING,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

async def test_pipeline():
    print("\n" + "="*60)
    print("TESTING FIXED PIPELINE")
    print("="*60)
    
    # Test 1: Fallback search
    print("\n[Test 1] Testing fallback search...")
    from app.services.fallback_search import generate_fallback_signals
    
    fallback = generate_fallback_signals("tires", "Kenya")
    print(f"  Generated {len(fallback)} fallback signals")
    if fallback:
        print(f"  Sample: {fallback[0]['title']}")
    
    # Test 2: Query generation
    print("\n[Test 2] Testing query generation...")
    from app.services.kenya_high_recall_pipeline import generate_high_recall_queries
    
    queries = generate_high_recall_queries("tires", "Kenya")
    print(f"  Generated queries: {queries}")
    
    # Test 3: Full search (with fallback)
    print("\n[Test 3] Testing full search pipeline...")
    from app.services.search_service import search
    
    result = await search("tires", "Kenya")
    print(f"  Status: {result['status']}")
    print(f"  Count: {result['count']}")
    print(f"  Leads: {len(result['leads'])}")
    
    if result['leads']:
        print("\n  First lead:")
        lead = result['leads'][0]
        print(f"    Title: {lead.get('title', 'N/A')}")
        print(f"    Source: {lead.get('source', 'N/A')}")
        print(f"    Score: {lead.get('intent_score', 'N/A')}")
    
    # Test 4: Another query
    print("\n[Test 4] Testing 'plumber' query...")
    result2 = await search("plumber", "Kenya")
    print(f"  Status: {result2['status']}")
    print(f"  Count: {result2['count']}")
    
    print("\n" + "="*60)
    print("TEST COMPLETE")
    print("="*60)

if __name__ == "__main__":
    asyncio.run(test_pipeline())
