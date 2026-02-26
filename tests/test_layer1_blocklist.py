
import sys
import os
sys.path.append(os.getcwd())

from app.services.market_classifier import classify_market_side

def test_layer1_blocklist():
    print("--- Testing LAYER 1 Blocklist (Hard Rejection) ---")
    
    # List of phrases that MUST be rejected
    blocklist_phrases = [
        "shop", "buy online", "for sale", "order now", "call now", 
        "dealer", "official store", "we ship", "delivery available", 
        "price negotiable", "stock available", "visit our store", 
        "add to cart", "checkout", "website link"
    ]
    
    # Construct test cases around these phrases
    test_cases = [
        f"I have a great item {phrase} for you." for phrase in blocklist_phrases
    ]
    # Add some realistic examples
    test_cases.append("Visit our shop to see the latest collection.")
    test_cases.append("Best price in Kenya. Buy online today.")
    test_cases.append("We have stock available for immediate delivery.")
    test_cases.append("Official store for Apple products.")
    
    failures = 0
    
    for text in test_cases:
        result = classify_market_side(text)
        status = "✅ REJECTED" if result == "supply" else "❌ FAILED"
        if result != "supply":
            failures += 1
        print(f"[{status}] '{text}' -> {result}")
        
    if failures == 0:
        print("\n✅ All Layer 1 Blocklist tests passed! immediate rejection is working.")
    else:
        print(f"\n❌ {failures} tests failed. Layer 1 Blocklist is leaking.")
        exit(1)

if __name__ == "__main__":
    test_layer1_blocklist()
