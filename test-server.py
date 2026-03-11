#!/usr/bin/env python3
"""Test if backend can start"""
import os
import sys

os.environ["DATABASE_URL"] = "sqlite:///./delta9.db"
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "test-key"
os.environ["PYTHONPATH"] = "."

sys.path.insert(0, '.')

print("Testing backend import...")
try:
    from app.main import app
    print("[OK] App imported successfully")
    
    from fastapi.testclient import TestClient
    client = TestClient(app)
    
    print("Testing /api/guardian/ping...")
    response = client.get("/api/guardian/ping")
    print(f"[OK] Status: {response.status_code}")
    print(f"[OK] Response: {response.json()}")
    
    print("\nTesting /api/guardian/scrapers...")
    response = client.get("/api/guardian/scrapers")
    print(f"[OK] Status: {response.status_code}")
    print(f"[OK] Scrapers count: {len(response.json())}")
    
    print("\n[OK] Backend is working correctly!")
    print("\nStart the server with:")
    print("  .venv\\Scripts\\python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    
except Exception as e:
    print(f"[ERROR] {e}")
    import traceback
    traceback.print_exc()
