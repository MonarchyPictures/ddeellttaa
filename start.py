#!/usr/bin/env python3
"""
Delta 9 Dashboard Startup Script for Railway
"""
import os
import sys

# Get port from environment variable (Railway sets this)
port = int(os.environ.get("PORT", 8000))
host = "0.0.0.0"

print("="*60)
print("  DELTA 9 DASHBOARD v3.0")
print("="*60)
print()
print(f"  Starting server on {host}:{port}")
print()

# Import and run the app
from app_dashboard import app
import uvicorn

uvicorn.run(app, host=host, port=port, log_level="info")
