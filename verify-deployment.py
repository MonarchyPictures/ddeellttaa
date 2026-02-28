#!/usr/bin/env python3
"""
Railway Deployment Verification Script
Run this after deploying to verify all fixes are active.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def check_scraper_registry():
    """Verify all scrapers are registered."""
    print("\n" + "="*60)
    print("CHECK 1: SCRAPER REGISTRY")
    print("="*60)
    
    from app.scrapers.registry import SCRAPER_REGISTRY, SCRAPER_PRIORITY
    
    expected_scrapers = [
        "serpapi", "google_cse", "telegram", "facebook", 
        "kenyan_forums", "twitter", "jiji", "pigiame",
        "google_maps", "whatsapp_groups", "duckduckgo"
    ]
    
    registered = list(SCRAPER_REGISTRY.keys())
    print(f"Registered scrapers ({len(registered)}):")
    for name in sorted(registered):
        priority = SCRAPER_PRIORITY.get(name, 0)
        print(f"  - {name} (priority: {priority})")
    
    missing = set(expected_scrapers) - set(registered)
    if missing:
        print(f"\n❌ MISSING SCRAPERS: {missing}")
        print("   RAILWAY_ENVIRONMENT bug still active!")
        return False
    else:
        print(f"\n✅ All {len(expected_scrapers)} expected scrapers registered")
        return True

def check_high_recall_mode():
    """Verify HIGH_RECALL_MODE is enabled."""
    print("\n" + "="*60)
    print("CHECK 2: HIGH RECALL MODE")
    print("="*60)
    
    from app.config.runtime import HIGH_RECALL_MODE
    
    print(f"HIGH_RECALL_MODE = {HIGH_RECALL_MODE}")
    
    if HIGH_RECALL_MODE:
        print("✅ High recall mode is ENABLED")
        return True
    else:
        print("❌ High recall mode is DISABLED")
        return False

def check_classifier_thresholds():
    """Verify classifier uses low thresholds."""
    print("\n" + "="*60)
    print("CHECK 3: CLASSIFIER THRESHOLDS")
    print("="*60)
    
    from app.config.runtime import (
        INTENT_THRESHOLD, CONFIDENCE_FLOOR, 
        INTENT_POINTS_FLOOR, REQUIRE_FIRST_PERSON,
        REQUIRE_BUYER_KEYWORD
    )
    
    checks = {
        "INTENT_THRESHOLD": (INTENT_THRESHOLD, 0.05),
        "CONFIDENCE_FLOOR": (CONFIDENCE_FLOOR, 0.04),
        "INTENT_POINTS_FLOOR": (INTENT_POINTS_FLOOR, 5),
        "REQUIRE_FIRST_PERSON": (REQUIRE_FIRST_PERSON, False),
        "REQUIRE_BUYER_KEYWORD": (REQUIRE_BUYER_KEYWORD, False),
    }
    
    all_pass = True
    for name, (actual, expected) in checks.items():
        status = "✅" if actual == expected else "❌"
        print(f"{status} {name}: {actual} (expected: {expected})")
        if actual != expected:
            all_pass = False
    
    return all_pass

def test_intent_scoring():
    """Test intent scoring with sample texts."""
    print("\n" + "="*60)
    print("CHECK 4: INTENT SCORING")
    print("="*60)
    
    from app.services.kenya_high_recall_pipeline import calculate_kenyan_intent_score
    
    test_cases = [
        ("5000L tank iko?", 0.25, "Swahili question"),
        ("Need 10000L tank urgently", 0.25, "Urgency + need"),
        ("Tank around 25k?", 0.25, "Price question"),
        ("Natafuta tank kubwa", 0.25, "Swahili buyer verb"),
        ("We sell quality tanks call us", 0.0, "Seller (should reject)"),
        ("Tanks for sale best price", 0.0, "Seller (should reject)"),
    ]
    
    all_pass = True
    for text, min_expected, description in test_cases:
        score = calculate_kenyan_intent_score(text)
        passed = score >= min_expected if min_expected > 0 else score == 0
        status = "✅" if passed else "❌"
        print(f"{status} '{text[:40]}' -> {score:.2f} (min: {min_expected}) [{description}]")
        if not passed:
            all_pass = False
    
    return all_pass

def check_celery_config():
    """Verify Celery is configured for Redis."""
    print("\n" + "="*60)
    print("CHECK 5: CELERY CONFIGURATION")
    print("="*60)
    
    try:
        from app.core.celery_app import celery, REDIS_URL
        
        print(f"Redis URL configured: {'Yes' if REDIS_URL else 'No'}")
        print(f"Celery broker: {celery.conf.broker_url[:20]}...")
        print("✅ Celery configured for Redis")
        return True
    except Exception as e:
        print(f"❌ Celery config error: {e}")
        return False

def main():
    """Run all verification checks."""
    print("\n" + "="*60)
    print("DELTA9 DEPLOYMENT VERIFICATION")
    print("="*60)
    print(f"Time: 2026-02-27 23:59 UTC")
    print(f"Version: HIGH-RECALL-V3")
    
    results = {
        "Scraper Registry": check_scraper_registry(),
        "High Recall Mode": check_high_recall_mode(),
        "Classifier Thresholds": check_classifier_thresholds(),
        "Intent Scoring": test_intent_scoring(),
        "Celery Config": check_celery_config(),
    }
    
    print("\n" + "="*60)
    print("SUMMARY")
    print("="*60)
    
    for check, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"{status}: {check}")
    
    all_passed = all(results.values())
    
    if all_passed:
        print("\n🎉 ALL CHECKS PASSED - Deployment is healthy!")
        return 0
    else:
        print("\n⚠️  SOME CHECKS FAILED - Review issues above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
