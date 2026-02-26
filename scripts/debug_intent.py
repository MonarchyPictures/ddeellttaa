
from app.intelligence.intent import buyer_intent_score, is_buyer_intent
from app.utils.intent_scoring import IntentScorer

scorer = IntentScorer()

texts = [
    "looking for laptop",
    "I need to buy a laptop",
    "Anyone selling a laptop?",
    "Laptop for sale",
    "Best price for laptop",
    "I want to purchase a laptop",
    "looking for laptop price 50k"
]

print("--- Intent Debug ---")
for text in texts:
    score = buyer_intent_score(text)
    is_buyer = is_buyer_intent(text)
    validate = scorer.validate_lead(text)
    print(f"Text: '{text}'")
    print(f"  Score: {score}")
    print(f"  Is Buyer: {is_buyer}")
    print(f"  Validate: {validate}")
    print("-" * 20)
