from app.db.database import SessionLocal, engine
from app.db import models
from datetime import datetime
import uuid

def seed_agents():
    db = SessionLocal()
    
    # Check if agents already exist
    if db.query(models.Agent).count() > 0:
        print("Agents already exist, skipping...")
        db.close()
        return

    # Sample agents
    agents = [
        {
            "name": "Furniture Hunter",
            "query": "looking for furniture",
            "location": "Kenya",
            "active": 1
        },
        {
            "name": "Electronics Radar",
            "query": "buying used iphone",
            "location": "Kenya",
            "active": 1
        },
        {
            "name": "Vehicle Scout",
            "query": "want to buy car",
            "location": "Kenya",
            "active": 1
        }
    ]
    
    for agent_data in agents:
        agent = models.Agent(**agent_data)
        db.add(agent)
    
    try:
        db.commit()
        print(f"Successfully seeded {len(agents)} agents!")
    except Exception as e:
        print(f"Error seeding agents: {e}")
        db.rollback()
    finally:
        db.close()

if __name__ == "__main__":
    seed_agents()
