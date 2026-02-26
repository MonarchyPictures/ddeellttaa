
from app.db.database import SessionLocal
from app.db import models
from sqlalchemy import or_

def check_live_leads():
    db = SessionLocal()
    
    # Check all leads
    total = db.query(models.Lead).count()
    print(f"Total leads: {total}")
    
    # Check genuine leads
    genuine = db.query(models.Lead).filter(models.Lead.is_genuine_buyer == 1).count()
    print(f"Genuine leads: {genuine}")
    
    # Check Kenya leads
    kenya = db.query(models.Lead).filter(or_(
        models.Lead.location_raw.ilike("%Kenya%"),
        models.Lead.location_raw == "Unknown",
        models.Lead.location_raw == None
    )).count()
    print(f"Kenya leads (including Unknown/None): {kenya}")
    
    # Check leads that pass both filters (what the API sees)
    api_leads = db.query(models.Lead).filter(
        models.Lead.is_genuine_buyer == 1,
        or_(
            models.Lead.location_raw.ilike("%Kenya%"),
            models.Lead.location_raw == "Unknown",
            models.Lead.location_raw == None
        )
    ).count()
    print(f"Leads passing both Genuine + Kenya filters: {api_leads}")
    
    if api_leads > 0:
        latest = db.query(models.Lead).filter(
            models.Lead.is_genuine_buyer == 1,
            or_(
                models.Lead.location_raw.ilike("%Kenya%"),
                models.Lead.location_raw == "Unknown",
                models.Lead.location_raw == None
            )
        ).order_by(models.Lead.created_at.desc()).first()
        print(f"\nLatest API-visible lead:")
        print(f" - Snippet: {latest.buyer_request_snippet[:100]}...")
        print(f" - Platform: {latest.source_platform}")
        print(f" - Created: {latest.created_at}")
        print(f" - Confidence: {latest.confidence_score}")
        print(f" - Intent: {latest.intent_score}")
    
    db.close()

if __name__ == "__main__":
    check_live_leads()
