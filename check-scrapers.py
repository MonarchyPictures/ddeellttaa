#!/usr/bin/env python3
"""Check scraper status"""
import sys
import os

os.environ["DATABASE_URL"] = "sqlite:///./delta9.db"
os.environ["APP_ENV"] = "development"
os.environ["PYTHONPATH"] = "."

sys.path.insert(0, '.')

print("Checking scraper registry...")
print("="*50)

from app.scrapers.registry import SCRAPER_REGISTRY, ACTIVE_SCRAPERS, SCRAPER_PRIORITY

print(f"\nRegistered scrapers: {len(SCRAPER_REGISTRY)}")
for name in sorted(SCRAPER_REGISTRY.keys()):
    priority = SCRAPER_PRIORITY.get(name, 'N/A')
    active = "[ACTIVE]" if name in ACTIVE_SCRAPERS else "[INACTIVE]"
    print(f"  {active} {name} (priority: {priority})")

print(f"\nActive scrapers: {len(ACTIVE_SCRAPERS)}")
print(f"Scrapers: {', '.join(ACTIVE_SCRAPERS)}")

print("\n" + "="*50)
print("\nTo see scrapers in the UI:")
print("1. Start backend: .venv\\Scripts\\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
print("2. Open http://localhost:8000/api/guardian/scrapers")
print("3. Or check frontend at http://localhost:5173/agents")
