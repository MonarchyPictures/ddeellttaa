
import sys
import os
from sqlalchemy import create_engine, desc
from sqlalchemy.orm import sessionmaker
from app.db import models

DATABASE_URL = "sqlite:///./intent_radar.db"
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def check_leads():
    db = SessionLocal()
    try:
        leads = db.query(models.Lead).order_by(desc(models.Lead.timestamp)).limit(10).all()
        print(f"Total leads in DB: {db.query(models.Lead).count()}")
        print("-" * 50)
        for lead in leads:
            print(f"ID: {lead.id}")
            print(f"Platform: {lead.source_platform}")
            print(f"Category: {lead.product_category}")
            print(f"Snippet: {lead.buyer_request_snippet[:100]}...")
            print(f"Intent Score: {lead.intent_score}")
            print(f"Genuine: {lead.is_genuine_buyer}")
            print(f"Confidence: {lead.confidence_score}")
            print(f"Location: {lead.location_raw}")
            print(f"Timestamp: {lead.timestamp}")
            print("-" * 50)
    finally:
        db.close()

if __name__ == "__main__":
    check_leads()
