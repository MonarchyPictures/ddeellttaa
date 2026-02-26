from app.services.market_classifier import classify_market_side
from app.nlp.intent_service import BuyingIntentNLP

def test_classifier_rejection():
    print("--- 1. Market Classifier (Rule-Based) ---")
    # 1. The User's Specific Bad Example (SELLER)
    bad_text = "Shop and Buy Online - iPhones & iPads | Digital Store ... Shop online and Buy original iPhones and iPads from Digital Store, Kenya. The leading Apple Products dealer in Nairobi , Kenya. We Ship Across East Africa. Call +254 111043000 to order."
    
    result = classify_market_side(bad_text)
    print(f"Bad Text Classification: {result}")
    assert result == "supply", f"Expected 'supply' but got '{result}' for bad text."

    # 2. Another Common Seller Example
    seller_text_2 = "Best Price in Kenya for Water Tanks. Order online now. Free delivery within Nairobi."
    result_2 = classify_market_side(seller_text_2)
    print(f"Seller Text 2 Classification: {result_2}")
    assert result_2 == "supply", f"Expected 'supply' but got '{result_2}'"

    # 3. A Good Buyer Example
    good_text = "Looking for a 5000L water tank in Nairobi. Budget is 25k. Serious buyer."
    result_3 = classify_market_side(good_text)
    print(f"Good Text Classification: {result_3}")
    assert result_3 == "demand", f"Expected 'demand' but got '{result_3}'"

    print("\n✅ Market Classifier Tests Passed!")

    print("\n--- 2. Intent Service (NLP/Heuristic) ---")
    nlp = BuyingIntentNLP()
    
    intent_1 = nlp.classify_intent(bad_text)
    print(f"Bad Text Intent: {intent_1}")
    assert intent_1 == "SELLER", f"Expected 'SELLER' but got '{intent_1}'"

    intent_2 = nlp.classify_intent(seller_text_2)
    print(f"Seller Text 2 Intent: {intent_2}")
    assert intent_2 == "SELLER", f"Expected 'SELLER' but got '{intent_2}'"

    intent_3 = nlp.classify_intent(good_text)
    print(f"Good Text Intent: {intent_3}")
    assert intent_3 == "BUYER", f"Expected 'BUYER' but got '{intent_3}'"
    
    print("\n✅ All Intent Tests Passed! System is STRICTLY enforcing Buyer/Seller separation.")

if __name__ == "__main__":
    test_classifier_rejection()
