#!/usr/bin/env python3
"""
Delta 9 Dashboard - Railway Entry Point
Simple startup file for Railway deployment
"""
import os
import sys

# Get configuration from environment
port = int(os.environ.get("PORT", 8000))
host = "0.0.0.0"

print("="*60)
print("  DELTA 9 DASHBOARD v3.0")
print("="*60)
print(f"\n  Starting server on {host}:{port}\n")

# Import the FastAPI app
try:
    from app_dashboard import app
    print("  App imported successfully")
except Exception as e:
    print(f"  ERROR importing app: {e}")
    sys.exit(1)

# Start the server
import uvicorn
uvicorn.run(
    app, 
    host=host, 
    port=port, 
    log_level="info",
    access_log=True
)
