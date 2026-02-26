from app.db.database import SessionLocal
from app.db import models
from datetime import datetime, timezone
import uuid

def seed_notifications():
    db = SessionLocal()
    
    # Get some leads and agents
    leads = db.query(models.Lead).all()
    agents = db.query(models.Agent).all()
    
    if not leads or not agents:
        print("Missing leads or agents to notify about!")
        db.close()
        return

    notifications = []
    for i in range(min(len(leads), 3)):
        lead = leads[i]
        agent = agents[i % len(agents)]
        
        notification = models.Notification(
            lead_id=lead.id,
            agent_id=agent.id,
            message=f"🚨 REAL-TIME ALERT: New lead for '{agent.query}' found on {lead.source_platform}!",
            is_read=0,
            created_at=datetime.now(timezone.utc)
        )
        notifications.append(notification)
        db.add(notification)
    
    try:
        db.commit()
        print(f"Successfully seeded {len(notifications)} notifications!")
    except Exception as e:
        print(f"Error seeding notifications: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_notifications()
