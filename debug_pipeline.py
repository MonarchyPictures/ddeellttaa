#!/usr/bin/env python3
"""
DELTA 9 PIPELINE DEBUGGER
=========================
Comprehensive diagnostic tool to trace why "0 buyers found" occurs.
"""

import asyncio
import logging
import sys
import os
from typing import List, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Force reload of modules
import importlib

async def debug_step_1_scraper_registry():
    """Step 1: Check if scrapers are registered and active."""
    print("\n" + "="*60)
    print("STEP 1: SCRAPER REGISTRY CHECK")
    print("="*60)
    
    from app.scrapers.registry import SCRAPER_REGISTRY, ACTIVE_SCRAPERS, get_active_scrapers_sorted
    
    print(f"Registered scrapers: {len(SCRAPER_REGISTRY)}")
    for name, scraper in SCRAPER_REGISTRY.items():
        print(f"  - {name}: {type(scraper).__name__}")
    
    print(f"\nActive scrapers: {len(ACTIVE_SCRAPERS)}")
    for name in ACTIVE_SCRAPERS:
        print(f"  - {name}")
    
    active_scrapers = get_active_scrapers_sorted()
    print(f"\nSorted active scrapers ({len(active_scrapers)}):")
    for i, scraper in enumerate(active_scrapers):
        print(f"  {i+1}. {type(scraper).__name__}")
    
    if not active_scrapers:
        print("\n⚠️  WARNING: No active scrapers found!")
        print("   This means no data sources are available.")
        return False
    
    return True


def debug_step_2_serpapi_config():
    """Step 2: Check SERPAPI configuration."""
    print("\n" + "="*60)
    print("STEP 2: SERPAPI CONFIGURATION CHECK")
    print("="*60)
    
    from app.config.runtime import SERPAPI_KEY
    
    if not SERPAPI_KEY:
        print("⚠️  SERPAPI_KEY is NOT set!")
        print("   The system will fall back to DuckDuckGo (less reliable).")
        print("   To fix: Set SERPAPI_KEY environment variable.")
        return False
    
    if "placeholder" in SERPAPI_KEY.lower() or "your_key" in SERPAPI_KEY.lower():
        print("⚠️  SERPAPI_KEY appears to be a placeholder!")
        print(f"   Value: {SERPAPI_KEY[:30]}...")
        return False
    
    print(f"✓ SERPAPI_KEY is set (length: {len(SERPAPI_KEY)})")
    print(f"  Key starts with: {SERPAPI_KEY[:10]}...")
    return True


async def debug_step_3_test_scrapers():
    """Step 3: Test individual scrapers."""
    print("\n" + "="*60)
    print("STEP 3: TESTING INDIVIDUAL SCRAPERS")
    print("="*60)
    
    from app.scrapers.registry import get_active_scrapers_sorted
    
    scrapers = get_active_scrapers_sorted()
    if not scrapers:
        print("No scrapers to test!")
        return []
    
    test_query = "tires"
    test_location = "Kenya"
    
    all_results = []
    
    for scraper in scrapers[:3]:  # Test top 3 scrapers
        scraper_name = type(scraper).__name__
        print(f"\nTesting {scraper_name}...")
        
        try:
            # Check circuit breaker
            cb_state = getattr(scraper, 'circuit_breaker', None)
            if cb_state:
                print(f"  Circuit breaker state: {cb_state.state}")
                if cb_state.state == "OPEN":
                    print(f"  ⚠️  Skipping {scraper_name} - circuit breaker is OPEN")
                    continue
            
            # Try to run the scraper with timeout
            import asyncio
            
            if hasattr(scraper, 'search'):
                print(f"  Calling {scraper_name}.search('{test_query}', '{test_location}')")
                result = await asyncio.wait_for(
                    scraper.search(test_query, test_location),
                    timeout=10
                )
            elif hasattr(scraper, 'scrape'):
                print(f"  Calling {scraper_name}.scrape('{test_query}', 24)")
                result = await asyncio.wait_for(
                    asyncio.to_thread(scraper.scrape, test_query, 24),
                    timeout=10
                )
            else:
                print(f"  ⚠️  No search or scrape method found!")
                continue
            
            if result is None:
                print(f"  ⚠️  Returned None (should return empty list)")
                result = []
            
            if not isinstance(result, list):
                print(f"  ⚠️  Returned non-list type: {type(result)}")
                result = []
            
            print(f"  ✓ Returned {len(result)} results")
            all_results.extend(result)
            
            if result:
                print(f"  Sample result: {str(result[0])[:150]}...")
                
        except asyncio.TimeoutError:
            print(f"  ⚠️  TIMEOUT after 10 seconds")
        except Exception as e:
            print(f"  ✗ ERROR: {type(e).__name__}: {e}")
    
    print(f"\n{'='*60}")
    print(f"Total raw results from all scrapers: {len(all_results)}")
    print("="*60)
    
    return all_results


def debug_step_4_buyer_detection():
    """Step 4: Test buyer signal detection."""
    print("\n" + "="*60)
    print("STEP 4: BUYER SIGNAL DETECTION TEST")
    print("="*60)
    
    from app.services.market_classifier import is_valid_buyer, calculate_kenyan_intent_score
    from app.config.runtime import HIGH_RECALL_MODE, INTENT_POINTS_FLOOR
    
    print(f"HIGH_RECALL_MODE: {HIGH_RECALL_MODE}")
    print(f"INTENT_POINTS_FLOOR: {INTENT_POINTS_FLOOR}")
    
    test_cases = [
        # Strong buyer signals (should pass)
        ("natafuta tires budget 50k Nairobi", True, "Swahili buyer + budget + location"),
        ("I am looking for tires in Kenya", True, "English buyer phrase"),
        ("Anyone selling tires? Need asap", True, "Question + urgency"),
        ("nahitaji tires 0712345678", True, "Swahili + phone"),
        
        # Weak signals (may or may not pass depending on threshold)
        ("tires for sale", False, "Seller signal"),
        ("Best price on tires in Kenya", False, "Price comparison"),
        ("Tire shop in Nairobi", False, "Business listing"),
    ]
    
    print("\nTesting buyer detection:")
    for text, expected, description in test_cases:
        is_valid = is_valid_buyer(text)
        score, details = calculate_kenyan_intent_score(text)
        
        status = "✓" if is_valid == expected else "✗"
        print(f"\n{status} [{description}]")
        print(f"  Text: '{text}'")
        print(f"  Expected: {'PASS' if expected else 'REJECT'}")
        print(f"  Got: {'PASS' if is_valid else 'REJECT'}")
        print(f"  Score: {score}")
        print(f"  Details: {details[:3]}...")  # First 3 details


def debug_step_5_pipeline_processing(raw_results: List[Dict]):
    """Step 5: Test the pipeline processing."""
    print("\n" + "="*60)
    print("STEP 5: PIPELINE PROCESSING TEST")
    print("="*60)
    
    if not raw_results:
        print("No raw results to process!")
        # Create synthetic test data
        print("Creating synthetic test data...")
        raw_results = [
            {
                "title": "Looking for tires",
                "snippet": "natafuta tires budget 50k Nairobi 0712345678",
                "source": "test",
                "url": "https://example.com/1"
            },
            {
                "title": "Tires for sale",
                "snippet": "Best tires for sale price 45k negotiable",
                "source": "test",
                "url": "https://example.com/2"
            },
            {
                "title": "Need tires urgently",
                "snippet": "I need tires asap in Mombasa call 0722123456",
                "source": "test", 
                "url": "https://example.com/3"
            }
        ]
    
    print(f"Processing {len(raw_results)} raw results...")
    
    from app.services.kenya_high_recall_pipeline import process_high_recall_results
    
    try:
        processed = process_high_recall_results(raw_results)
        print(f"✓ Pipeline returned {len(processed)} processed leads")
        
        for i, lead in enumerate(processed[:3]):
            print(f"\n  Lead {i+1}:")
            if hasattr(lead, 'to_dict'):
                lead_dict = lead.to_dict()
            else:
                lead_dict = lead
            print(f"    Title: {lead_dict.get('title', 'N/A')}")
            print(f"    Score: {lead_dict.get('intent_score', 'N/A')}")
            print(f"    Badge: {lead_dict.get('badge', 'N/A')}")
            
    except Exception as e:
        print(f"✗ Pipeline processing failed: {e}")
        import traceback
        traceback.print_exc()


def debug_step_6_check_query_generation():
    """Step 6: Check query generation."""
    print("\n" + "="*60)
    print("STEP 6: QUERY GENERATION CHECK")
    print("="*60)
    
    from app.services.kenya_high_recall_pipeline import generate_high_recall_queries
    
    test_queries = ["tires", "plumber", "water tank", "iPhone 15"]
    
    for query in test_queries:
        queries = generate_high_recall_queries(query, "Kenya")
        print(f"\nQuery: '{query}'")
        print(f"  Generated {len(queries)} expanded queries:")
        for i, q in enumerate(queries):
            print(f"    {i+1}. {q}")


def debug_step_7_environment_check():
    """Step 7: Check environment variables."""
    print("\n" + "="*60)
    print("STEP 7: ENVIRONMENT CHECK")
    print("="*60)
    
    critical_vars = [
        'SERPAPI_KEY',
        'DATABASE_URL',
        'REDIS_URL',
        'GOOGLE_CSE_API_KEY',
        'GOOGLE_CSE_ID',
        'ENVIRONMENT'
    ]
    
    print("\nEnvironment variables:")
    for var in critical_vars:
        value = os.getenv(var, "")
        if value:
            # Mask sensitive values
            if 'KEY' in var or 'SECRET' in var or 'PASSWORD' in var:
                display_value = f"{value[:10]}..." if len(value) > 10 else "[SET]"
            else:
                display_value = value
            print(f"  ✓ {var}: {display_value}")
        else:
            print(f"  ✗ {var}: NOT SET")


async def run_full_debug():
    """Run all debug steps."""
    print("\n" + "="*60)
    print("DELTA 9 PIPELINE DEBUGGER")
    print("="*60)
    print("\nThis tool will diagnose why '0 buyers found' occurs.\n")
    
    # Step 1: Check scraper registry
    scrapers_ok = await debug_step_1_scraper_registry()
    
    # Step 2: Check SERPAPI config
    serpapi_ok = debug_step_2_serpapi_config()
    
    # Step 3: Test scrapers
    raw_results = await debug_step_3_test_scrapers()
    
    # Step 4: Test buyer detection
    debug_step_4_buyer_detection()
    
    # Step 5: Test pipeline processing
    debug_step_5_pipeline_processing(raw_results)
    
    # Step 6: Check query generation
    debug_step_6_check_query_generation()
    
    # Step 7: Environment check
    debug_step_7_environment_check()
    
    # Summary
    print("\n" + "="*60)
    print("DEBUG SUMMARY")
    print("="*60)
    
    issues = []
    if not scrapers_ok:
        issues.append("No scrapers are active")
    if not serpapi_ok:
        issues.append("SERPAPI not configured (will use fallback)")
    if not raw_results:
        issues.append("Scrapers returned no results")
    
    if issues:
        print("\nIssues found:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("\n✓ No critical issues found")
    
    print("\n" + "="*60)


if __name__ == "__main__":
    asyncio.run(run_full_debug())
