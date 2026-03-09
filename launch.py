#!/usr/bin/env python3
"""
Delta 9 Full Application Launcher
"""
import os
import sys

# Fix Windows encoding
if sys.platform == 'win32':
    import codecs
    sys.stdout = codecs.getwriter('utf-8')(sys.stdout.buffer)
    sys.stderr = codecs.getwriter('utf-8')(sys.stderr.buffer)

# Environment setup
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///./delta9.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'
os.environ['SECRET_KEY'] = 'local-dev-secret-key-change-in-production'

print("="*60)
print("  DELTA 9 - Full Application Server")
print("="*60)
print()
print("  Initializing...")
print()

# Import and start the full app
from app.main import app
import uvicorn

print("  ✅ App loaded successfully")
print()
print("  Starting server...")
print()
print("  URLs:")
print("    http://localhost:8000          - API Root")
print("    http://localhost:8000/docs     - Swagger UI (Interactive)")
print("    http://localhost:8000/api/search - Search Endpoint")
print("    http://localhost:8000/health   - Health Check")
print()
print("  Press CTRL+C to stop")
print("="*60)
print()

uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
