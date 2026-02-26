
import sys
import os

# Add the project root to sys.path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal, engine
from app.db import models

def clear_db():
    db = SessionLocal()
    try:
        # Delete all records from tables
        db.query(models.Notification).delete()
        db.query(models.Lead).delete()
        db.query(models.Agent).delete()
        db.query(models.SystemSetting).delete()
        db.commit()
        print("Successfully cleared all data from the database.")
    except Exception as e:
        db.rollback()
        print(f"Error clearing database: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    clear_db()
