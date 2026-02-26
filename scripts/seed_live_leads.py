from app.db.database import SessionLocal, engine
from app.db import models
from datetime import datetime, timezone, timedelta
import uuid
import random

def seed_live_leads():
    db = SessionLocal()
    
    # Sample leads for Kenya
    leads = [
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Facebook",
            "post_link": f"https://facebook.com/groups/kenya-business/posts/{random.randint(1000, 9999)}",
            "location_raw": "Nairobi, Kenya",
            "buyer_request_snippet": "Looking for a reliable supplier of office furniture in Nairobi. Need 10 desks and chairs by Friday.",
            "product_category": "Furniture",
            "intent_score": 0.95,
            "confidence_score": 0.9,
            "status": models.CRMStatus.NEW,
            "source_url": "https://facebook.com/groups/kenya-business/posts/1",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60))
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Reddit",
            "post_link": f"https://reddit.com/r/Kenya/comments/{random.randint(1000, 9999)}",
            "location_raw": "Mombasa, Kenya",
            "buyer_request_snippet": "Anyone selling a used iPhone 13 or 14 in Mombasa? Budget is around 60k-70k.",
            "product_category": "Electronics",
            "intent_score": 0.88,
            "confidence_score": 0.85,
            "status": models.CRMStatus.NEW,
            "source_url": "https://reddit.com/r/Kenya/comments/1",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60))
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Twitter",
            "post_link": f"https://twitter.com/user/status/{random.randint(1000, 9999)}",
            "location_raw": "Nairobi, Kenya",
            "buyer_request_snippet": "URGENT: Need a car for hire for 2 weeks. Must be a 4x4. DMs open.",
            "product_category": "Vehicles",
            "intent_score": 0.92,
            "confidence_score": 0.8,
            "status": models.CRMStatus.NEW,
            "source_url": "https://twitter.com/user/status/1",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60))
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Facebook",
            "post_link": f"https://facebook.com/marketplace/item/{random.randint(1000, 9999)}",
            "location_raw": "Kisumu, Kenya",
            "buyer_request_snippet": "In search of high-quality construction timber. Looking for 500 pieces of 2x4. Deliver to Kisumu.",
            "product_category": "Construction",
            "intent_score": 0.85,
            "confidence_score": 0.75,
            "status": models.CRMStatus.NEW,
            "source_url": "https://facebook.com/marketplace/item/1",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60))
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "TikTok",
            "post_link": f"https://tiktok.com/@user/video/{random.randint(1000, 9999)}",
            "location_raw": "Eldoret, Kenya",
            "buyer_request_snippet": "Who knows where I can get authentic agricultural seeds in Eldoret? #agriculture #kenya",
            "product_category": "Agriculture",
            "intent_score": 0.78,
            "confidence_score": 0.7,
            "status": models.CRMStatus.NEW,
            "source_url": "https://tiktok.com/@user/video/1",
            "created_at": datetime.now(timezone.utc) - timedelta(minutes=random.randint(1, 60))
        }
    ]
    
    for lead_data in leads:
        lead = models.Lead(**lead_data)
        db.add(lead)
    
    try:
        db.commit()
        print(f"Successfully seeded {len(leads)} live leads!")
    except Exception as e:
        print(f"Error seeding leads: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_live_leads()
