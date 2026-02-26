
import sys
import os

# Add the project root to the python path
sys.path.append(os.getcwd())

from sqlalchemy.orm import Session
from app.db.database import SessionLocal
from app.models.lead import Lead
from app.services.market_classifier import classify_market_side
from app.nlp.intent_service import BuyingIntentNLP

def cleanup_sellers():
    db = SessionLocal()
    try:
        print("Starting cleanup of existing seller leads...")
        
        # Initialize NLP service
        nlp = BuyingIntentNLP()
        
        # Fetch all leads that are NOT currently marked as SELLER
        # We want to re-check everything that might be showing up in the dashboard
        leads = db.query(Lead).filter(Lead.intent_type != 'SELLER').all()
        
        print(f"Found {len(leads)} potential leads to check.")
        
        seller_count = 0
        cleaned_count = 0
        
        for lead in leads:
            # Handle potential None description
            desc = lead.description if lead.description else ""
            text = f"{lead.title} {desc}"
            
            # 1. Check Market Classifier (Rule-based)
            market_side = classify_market_side(text)
            
            # 2. Check Intent Service (NLP/Heuristic)
            intent = nlp.classify_intent(text)
            
            is_seller = False
            reason = ""
            
            if market_side == "supply":
                is_seller = True
                reason = "Market Classifier (Supply)"
            elif intent == "SELLER":
                is_seller = True
                reason = "Intent Service (SELLER)"
            
            if is_seller:
                print(f"❌ Marking as SELLER: {lead.title[:50]}... [{reason}]")
                lead.intent_type = 'SELLER'
                lead.intent_score = 0.0 # Force score to 0 to remove from high-intent lists
                seller_count += 1
                cleaned_count += 1
            
            # Commit every 100 updates to avoid huge transactions
            if cleaned_count % 100 == 0:
                db.commit()
                
        db.commit()
        print(f"\n✅ Cleanup Complete!")
        print(f"Total leads checked: {len(leads)}")
        print(f"Leads re-classified as SELLER: {seller_count}")
        
    except Exception as e:
        print(f"Error during cleanup: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cleanup_sellers()
