
import asyncio
import logging
import sys
import os
import json

# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from app.services.search_service import search
from app.engine.buyer_classifier import BuyerClassifier
from app.scrapers.registry import SCRAPER_REGISTRY, get_active_scrapers_sorted

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_pipeline():
    print(f"\n--- REGISTRY CHECK ---")
    print(f"Registered Scrapers: {list(SCRAPER_REGISTRY.keys())}")
    active = get_active_scrapers_sorted()
    print(f"Active Scrapers: {[type(s).__name__ for s in active]}")

    query = "iPhone 15"
    location = "Kenya"
    
    print(f"\n--- TESTING SEARCH PIPELINE for '{query}' in '{location}' ---")
    
    # 1. Run Search Service (which uses QueryEngine + MultiScraper + BuyerClassifier)
    result = await search(query, location)
    
    print(f"\n--- RESULTS ---")
    print(f"Status: {result.get('status')}")
    print(f"Total Found: {result.get('total_signals_captured')}")
    print(f"Processed Leads: {len(result.get('leads', []))}")
    
    leads = result.get('leads', [])
    if leads:
        print(f"\nTop 3 Leads:")
        for i, lead in enumerate(leads[:3]):
            print(f"\n[{i+1}] {lead.get('title')}")
            print(f"    Source: {lead.get('source')}")
            print(f"    Intent: {lead.get('intent_score')} ({lead.get('badge')})")
            print(f"    Price: {lead.get('price')}")
            print(f"    Phone: {lead.get('phone')}")
            print(f"    URL: {lead.get('url')}")
    else:
        print("No leads found.")

    # 2. Test Classifier directly with specific text
    print(f"\n--- TESTING CLASSIFIER DIRECTLY ---")
    classifier = BuyerClassifier()
    
    samples = [
        "I am looking for iPhone 15 pro max 256gb within Nairobi. Budget 150k. 0712345678",
        "Brand new iPhone 15 for sale. 120k. Call 0722000000. Located in CBD.",
        "Anyone selling iPhone 15? Urgent.",
        "Natafuta iPhone 15 clean. Budget 80k."
    ]
    
    for text in samples:
        signal = classifier.classify(text)
        print(f"\nText: {text}")
        print(f"  Is Buyer: {signal.is_buyer}")
        print(f"  Score: {signal.intent_score} ({signal.badge})")
        print(f"  Details: {signal.score_details}")
        print(f"  Phone: {signal.phone}")
        print(f"  Budget: {signal.budget}")

if __name__ == "__main__":
    asyncio.run(test_pipeline())
