
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.db.database import SessionLocal
from app.db import models

def seed_products():
    db = SessionLocal()
    
    products = [
        {
            "name": "50,000L Water Tank",
            "category": "Water Tanks",
            "specs": {"capacity": "50000L", "material": "Plastic", "type": "Vertical"},
            "price": 450000.0,
            "location": "Nairobi"
        },
        {
            "name": "Toyota Camry 2005",
            "category": "Vehicles",
            "specs": {"model": "Camry", "year": "2005", "make": "Toyota"},
            "price": 850000.0,
            "location": "Mombasa"
        },
        {
            "name": "MacBook Pro M2 16GB",
            "category": "Laptops",
            "specs": {"model": "MacBook Pro", "processor": "M2", "ram": "16GB"},
            "price": 250000.0,
            "location": "Nairobi"
        }
    ]
    
    for p_data in products:
        p = models.SellerProduct(**p_data)
        db.add(p)
    
    db.commit()
    db.close()
    print(f"Successfully seeded {len(products)} seller products.")

if __name__ == "__main__":
    seed_products()
