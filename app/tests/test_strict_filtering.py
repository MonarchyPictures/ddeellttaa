
import sys
import os
import re
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.market_classifier import is_valid_buyer, calculate_kenyan_intent_score

def test_filtering():
    print("=== TESTING STRICT FILTERING ===")
    
    # 1. Seller Test (Should Reject)
    seller_text = "For sale: iPhone 13 Pro Max. Price 120k. Call 0712345678. Shop located in Nairobi."
    seller_url = "https://www.jiji.co.ke/nairobi/mobile-phones/iphone-13-pro-max-xyz"
    
    print(f"\nTest 1: Blatant Seller")
    print(f"Text: {seller_text}")
    print(f"URL: {seller_url}")
    is_valid = is_valid_buyer(seller_text, seller_url)
    score, details = calculate_kenyan_intent_score(seller_text)
    print(f"Result: Valid={is_valid}, Score={score}")
    print(f"Details: {details}")
    
    if not is_valid and score < 50:
        print("✅ PASSED: Correctly rejected.")
    else:
        print("❌ FAILED: Should have been rejected.")

    # 2. Buyer Test (Should Pass)
    buyer_text = "Looking for a 2 bedroom apartment in Kilimani. Budget is 60k. Need to move in by end of month."
    buyer_url = "https://www.facebook.com/groups/rentals/permalink/123"
    
    print(f"\nTest 2: Genuine Buyer")
    print(f"Text: {buyer_text}")
    print(f"URL: {buyer_url}")
    is_valid = is_valid_buyer(buyer_text, buyer_url)
    score, details = calculate_kenyan_intent_score(buyer_text)
    print(f"Result: Valid={is_valid}, Score={score}")
    print(f"Details: {details}")
    
    if is_valid and score >= 50:
        print("✅ PASSED: Correctly accepted.")
    else:
        print("❌ FAILED: Should have been accepted.")

    # 3. DuckDuckGo Leak Simulation (Should Reject)
    # Simulating a search result that is just a summary page or e-commerce listing
    ddg_text = "Shop online for electronics, phones, and more. Jumia Kenya is your number one online shopping site."
    ddg_url = "https://www.jumia.co.ke/phones-tablets/"
    
    print(f"\nTest 3: DuckDuckGo/Jumia Leak")
    print(f"Text: {ddg_text}")
    print(f"URL: {ddg_url}")
    is_valid = is_valid_buyer(ddg_text, ddg_url)
    score, details = calculate_kenyan_intent_score(ddg_text)
    print(f"Result: Valid={is_valid}, Score={score}")
    print(f"Details: {details}")
    
    if not is_valid:
        print("✅ PASSED: Correctly rejected (Domain/Seller Word).")
    else:
        print("❌ FAILED: Should have been rejected.")

    # 4. First Person Check (Should Reject if missing)
    no_fp_text = "House wanted. 3 bedrooms. Nairobi."
    no_fp_url = "https://some-site.com/post"
    
    print(f"\nTest 4: Missing First Person Pronoun")
    print(f"Text: {no_fp_text}")
    is_valid = is_valid_buyer(no_fp_text, no_fp_url)
    print(f"Result: Valid={is_valid}")
    
    if not is_valid:
        print("✅ PASSED: Correctly rejected (No first person).")
    else:
        print("❌ FAILED: Should have been rejected (No first person).")
        
    # 5. First Person Present (Should Pass if buyer phrase exists)
    fp_text = "I am looking for a house. 3 bedrooms. Nairobi."
    fp_url = "https://some-site.com/post"
    
    print(f"\nTest 5: First Person Present")
    print(f"Text: {fp_text}")
    is_valid = is_valid_buyer(fp_text, fp_url)
    print(f"Result: Valid={is_valid}")
    
    if is_valid:
        print("✅ PASSED: Correctly accepted.")
    else:
        print("❌ FAILED: Should have been accepted.")

if __name__ == "__main__":
    test_filtering()
