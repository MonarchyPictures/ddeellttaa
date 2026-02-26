from app.db.database import SessionLocal, engine
from app.db import models, database
from datetime import datetime, timezone, timedelta
import uuid


def seed_data():
    # Create tables
    models.Base.metadata.drop_all(bind=database.engine)
    models.Base.metadata.create_all(bind=database.engine)
    db = SessionLocal()
    
    now = datetime.now(timezone.utc)
    
    # Sample leads with Kenya context and varied filter attributes (Vehicles focus)
    sample_leads = [
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Twitter",
            "source_url": "https://twitter.com/user/toyota_1",
            "location_raw": "Westlands, Nairobi",
            "property_country": "Kenya",
            "buyer_request_snippet": "I need a Toyota Prado ASAP. Westlands area. Budget 4.5M.",
            "product_category": "Toyota",
            "intent_score": 0.95,
            "radius_km": 2.5,
            "contact_phone": "+254712345678",
            "buyer_name": "John Kamau",
            "status": models.CRMStatus.NEW,
            "created_at": now - timedelta(minutes=15)
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Facebook",
            "source_url": "https://facebook.com/groups/nissan_1",
            "location_raw": "Kitengela, Kajiado",
            "property_country": "Kenya",
            "buyer_request_snippet": "Looking for a Nissan X-Trail for family use. Kitengela.",
            "product_category": "Nissan",
            "intent_score": 0.88,
            "radius_km": 45.0,
            "contact_phone": "+254722998877",
            "buyer_name": "Mary Wambui",
            "status": models.CRMStatus.NEW,
            "created_at": now - timedelta(hours=5)
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Reddit",
            "source_url": "https://reddit.com/r/kenya/subaru",
            "location_raw": "Nakuru",
            "property_country": "Kenya",
            "buyer_request_snippet": "Anyone selling a Subaru Forester in Nakuru? Planning to buy next month.",
            "product_category": "Subaru",
            "intent_score": 0.65,
            "radius_km": 150.0,
            "contact_phone": None, 
            "buyer_name": "David Otieno",
            "status": models.CRMStatus.NEW,
            "created_at": now - timedelta(hours=30)
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Twitter",
            "source_url": "https://twitter.com/user/isuzu_1",
            "location_raw": "Eldoret",
            "property_country": "Kenya",
            "buyer_request_snippet": "Where can I get an Isuzu FRR truck in Eldoret? Bulk order for transport business.",
            "product_category": "Isuzu",
            "intent_score": 0.92,
            "radius_km": 300.0,
            "contact_phone": "+254733112233",
            "buyer_name": "Sarah Juma",
            "status": models.CRMStatus.NEW,
            "created_at": now - timedelta(days=2)
        },
        {
            "id": str(uuid.uuid4()),
            "source_platform": "Instagram",
            "source_url": "https://instagram.com/p/mazda_1",
            "location_raw": "Mombasa Road, Nairobi",
            "property_country": "Kenya",
            "buyer_request_snippet": "I need a Mazda Demio for Uber business. Delivery to Mombasa Road.",
            "product_category": "Mazda",
            "intent_score": 0.98,
            "radius_km": 12.0,
            "contact_phone": "+254700554433",
            "buyer_name": "Peter Njoroge",
            "status": models.CRMStatus.NEW,
            "created_at": now - timedelta(minutes=45)
        }
    ]
    
    for lead_data in sample_leads:
        lead = models.Lead(**lead_data)
        db.add(lead)
    
    # Sample Agents
    sample_agents = [
        {
            "name": "Nairobi Tire Hunter",
            "query": "Tires",
            "location": "Nairobi",
            "active": 1
        },
        {
            "name": "National Tank Scout",
            "query": "Tanks",
            "location": "Kenya",
            "active": 1
        }
    ]

    for agent_data in sample_agents:
        agent = models.Agent(**agent_data)
        db.add(agent)
    
    db.commit()

    # Sample Notifications
    leads = db.query(models.Lead).all()
    agents = db.query(models.Agent).all()
    
    if leads and agents:
        sample_notifications = [
            {
                "lead_id": leads[0].id,
                "agent_id": agents[0].id,
                "message": f"🚨 REAL-TIME ALERT: High intent signal for {leads[0].product_category} detected in {leads[0].location_raw}",
                "is_read": 0
            },
            {
                "lead_id": leads[1].id,
                "agent_id": agents[1].id,
                "message": f"URGENT: New market opportunity: {leads[1].buyer_request_snippet}",
                "is_read": 0
            }
        ]
        for notif_data in sample_notifications:
            notif = models.Notification(**notif_data)
            db.add(notif)

    try:
        db.commit()
        print("Database seeded successfully with Kenya Market Intel!")
    except Exception as e:
        print(f"Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_data()
