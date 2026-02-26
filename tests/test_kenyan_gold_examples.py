import sys
import os

# Add project root to Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.market_classifier import calculate_kenyan_intent_score, is_valid_buyer

def test_kenyan_gold_examples():
    print("--- Testing Kenyan Gold Examples (New Scoring + Strict Filter) ---")
    
    # 1. Buyer Examples (Should PASS with Score >= 50)
    # New Scoring: Phrase(+30), Budget(+25), Cash(+25), Urgency(+20), Location(+15)
    # STRICT FILTER: Must include "I", "Im", "my", "me", "we", "our", "natafuta", etc.
    buyer_examples = [
        ("natafuta 2br kilimani budget 8M", 70),  # Phrase(30) + Loc(15) + Budget(25) = 70. Valid (natafuta).
        ("I am looking for 3br westy budget 12m", 70), # Phrase(30) + Loc(15) + Budget(25) = 70. Valid (I).
        ("niko ready na cash 5M", 80),            # Phrase(30) + Budget(25) + Cash(25) = 80. Valid (niko).
        ("I am a serious buyer 2 bedroom lavington", 45), # Phrase(30) + Loc(15) = 45 -> FAIL SCORE (Valid I).
        ("I need nyumba south b asap", 65),          # Phrase(30) + Loc(15) + Urgency(20) = 65. Valid (I).
        ("natafuta plot ruaka 2m", 70),            # Phrase(30) + Loc(15) + Budget(25) = 70. Valid (natafuta).
        ("I am looking for probox 600k", 55),      # Phrase(30) + Budget(25) = 55. Valid (I).
        ("natafuta iphone 14 niko na cash", 55),   # Phrase(30) + Cash(25) = 55. Valid (natafuta/niko).
        ("I need any leads ya apartment westlands", 45),  # Phrase(30) + Loc(15) = 45. FAIL SCORE. Valid (I).
        ("nahama next month natafuta nyumba", 30), # Phrase(30). "next month" not urgency. Valid (natafuta).
        ("niko na mortgage approved", 30),         # Phrase(30). Valid (niko).
        ("I am looking for water tank", 30),       # Phrase(30). Valid (I).
        ("I want to buy a car", 30),               # Phrase(30). Valid (I).
        ("I need a water tank asap", 50),          # Phrase(30) + Urgency(20) = 50. PASS. Valid (I).
    ]

    print("\n✅ CHECKING BUYER EXAMPLES (Expect Score >= 50 for High Quality)")
    passed_buyers = 0
    valid_buyers = 0
    
    for text, expected_score in buyer_examples:
        # 1. Check Strict Filter
        is_valid = is_valid_buyer(text)
        
        # 2. Check Score
        score, details = calculate_kenyan_intent_score(text)
        
        status = "✅ PASS" if score >= 50 else "⚠️ LOW SCORE"
        if not is_valid: status = "❌ INVALID"
        
        if score >= 50 and is_valid:
            passed_buyers += 1
            
        print(f"[{status}] Score: {score} | Valid: {is_valid} | Text: '{text}'")
        # print(f"   Details: {details}")

    # 2. Seller Examples (Should FAIL is_valid_buyer OR Negative Score)
    seller_examples = [
        "Looking for iPhone? Buy from us today!", 
        "Shop and Buy Online - iPhones & iPads",  
        "Official Dealer for Samsung",            
        "We have stock available",                
        "Call us to order",                       
        "Visit our shop in CBD",                  
        "Best price in town, delivery available",
        "Jumia: Shop Online for Electronics",
        "Add to cart now"
    ]

    print("\n🚫 CHECKING SELLER EXAMPLES (Expect Rejected)")
    passed_sellers = 0
    for text in seller_examples:
        is_valid = is_valid_buyer(text)
        score, details = calculate_kenyan_intent_score(text)
        
        if not is_valid:
            status = "✅ REJECTED (Filter)"
            passed_sellers += 1
        elif score < 50:
            status = "✅ REJECTED (Score)"
            passed_sellers += 1
        else:
            status = "❌ FAILED (LEAKED)"
            
        print(f"[{status}] Valid: {is_valid} | Score: {score} | Text: '{text}'")

    # 3. Domain/Business Entity Examples (Should FAIL)
    # New Aggressive Rules: /product, /shop, jumia, "Ltd", "Official Dealer", etc.
    domain_examples = [
        # (Text, URL)
        ("I need a phone", "https://jumia.co.ke/product/123"), # Blocked Domain (jumia) + URL part (product)
        ("I want to buy", "https://myshop.com/cart"), # Blocked URL part (cart)
        ("Looking for car", "https://google.com/search?q=car"), # Blocked Search Engine
        ("I need advice", "https://duckduckgo.com/?q=advice"), # Blocked Search Engine
        ("Digital Store Kenya Ltd. We are located in CBD.", None), # Blocked Entity (Ltd, We are located)
        ("Samsung Official Dealer Nairobi", None), # Blocked Entity (Official Dealer)
        ("Wholesale prices for everyone", None), # Blocked Entity (Wholesale)
    ]
    
    print("\n🚫 CHECKING DOMAIN & ENTITY BLOCKS (Expect Rejected)")
    passed_blocks = 0
    for text, url in domain_examples:
        is_valid = is_valid_buyer(text, url)
        # We don't need to check score if is_valid is False, but let's see.
        score, _ = calculate_kenyan_intent_score(text)
        
        if not is_valid:
            status = "✅ REJECTED (Filter)"
            passed_blocks += 1
        else:
            status = "❌ FAILED (LEAKED)"
            
        print(f"[{status}] Valid: {is_valid} | Score: {score} | URL: {url} | Text: '{text}'")

    print("\n--- Summary ---")
    # We expect high quality buyers to pass, and low quality/sellers to fail.
    # I'll count how many "Good" examples passed.
    # Examples with score >= 50 should pass.
    expected_passes = sum(1 for _, s in buyer_examples if s >= 50)
    print(f"High Quality Buyers: {passed_buyers}/{expected_passes} Passed")
    print(f"Sellers Rejected: {passed_sellers}/{len(seller_examples)}")
    print(f"Domain/Entities Rejected: {passed_blocks}/{len(domain_examples)}")

if __name__ == "__main__":
    test_kenyan_gold_examples()
