
import sys
import os
from datetime import datetime, timezone

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.intelligence.buyer_classifier import classify_post
from app.intelligence.scoring import calculate_buyer_score

def test_buyer_filtering():
    test_cases = [
        {
            "text": "Looking for Toyota Axio 2016 model in Nairobi. My budget is 1.1M. Contact 0722000000",
            "expected": "buyer",
            "description": "Clear buyer with budget and contact"
        },
        {
            "text": "Toyota Axio for sale, clean unit, just imported. Price 1.2M. Call 0711000000",
            "expected": "seller",
            "description": "Clear seller post"
        },
        {
            "text": "Natafuta Toyota Axio haraka sana, budget 1M. Nairobi.",
            "expected": "buyer",
            "description": "Swahili buyer intent"
        },
        {
            "text": "Visit our yard for the best Toyota Axio inventory in Nairobi. Financing arranged.",
            "expected": "seller",
            "description": "Dealer inventory post"
        },
        {
            "text": "I want to buy a Toyota Axio, but please dm for price.",
            "expected": "seller",
            "description": "Hard reject: contains 'dm for' and 'price' even with 'want to buy'"
        },
        {
            "text": "I am looking for a Toyota Axio, price is 1.1M ksh.",
            "expected": "seller",
            "description": "Hard reject: contains 'price' and 'ksh' even with 'looking for'"
        },
        {
            "text": "Anyone selling a Toyota Axio? I need it urgently.",
            "expected": "buyer",
            "description": "Correctly identified as BUYER despite 'selling' keyword (Smart Classification)"
        },
        {
            "text": "Toyota Axio available in our showroom. Call me.",
            "expected": "seller",
            "description": "Hard reject: contains 'available', 'showroom', and 'call me'"
        }
    ]

    print("--- BUYER CLASSIFICATION TEST ---")
    for case in test_cases:
        result = classify_post(case["text"])
        status = "✅ PASS" if result == case["expected"] else "❌ FAIL"
        print(f"[{status}] {case['description']}")
        print(f"  Text: {case['text'][:50]}...")
        print(f"  Result: {result} (Expected: {case['expected']})")
        
        if result == "buyer":
            # Test scoring
            lead_data = {
                "intent": case["text"],
                "budget": "1.1M" if "budget" in case["text"].lower() or "1.1m" in case["text"].lower() else None,
                "location": "Nairobi",
                "contact": "0722000000" if "0722000000" in case["text"] else None,
                "posted_at": datetime.now(timezone.utc).strftime("%Y-%m-%d")
            }
            score = calculate_buyer_score(lead_data)
            print(f"  Score: {score*100}%")

if __name__ == "__main__":
    test_buyer_filtering()
