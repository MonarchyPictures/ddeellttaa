#!/usr/bin/env python3
"""
DELTA-9 SERVER STARTER (Simplified)
Quick start for local testing
"""

import os
import sys

# Set environment
os.environ["DATABASE_URL"] = "sqlite:///./delta9.db"
os.environ["REDIS_URL"] = ""
os.environ["APP_ENV"] = "development"
os.environ["DEBUG"] = "true"
os.environ["SECRET_KEY"] = "local-dev-key"
os.environ["PYTHONPATH"] = "."
os.environ["PYTHONUNBUFFERED"] = "1"

# Add current dir to path
sys.path.insert(0, '.')

print("="*60)
print("DELTA-9 SERVER STARTER")
print("="*60)
print("\nConfiguration:")
print("  Database: SQLite (delta9.db)")
print("  Cache: In-memory")
print("  Environment: Development")
print("\nStarting server at http://localhost:8000")
print("API Docs: http://localhost:8000/docs")
print("Health: http://localhost:8000/api/guardian/health")
print("\nPress Ctrl+C to stop\n")

# Start uvicorn
import uvicorn

if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
