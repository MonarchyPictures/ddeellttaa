#!/usr/bin/env python3
"""
Delta 9 Server Startup Script
Handles encoding issues and starts the server properly.
"""

import os
import sys
import subprocess

# Fix Windows encoding
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'

# Set environment variables
os.environ['ENVIRONMENT'] = 'development'
os.environ['DATABASE_URL'] = 'sqlite:///./delta9.db'
os.environ['REDIS_URL'] = 'redis://localhost:6379/0'

print("="*60)
print("  DELTA 9 SERVER")
print("="*60)
print()
print("  Starting server...")
print()
print("  URL: http://localhost:8000")
print("  Docs: http://localhost:8000/docs")
print()
print("  Press CTRL+C to stop")
print("="*60)
print()

# Start uvicorn
try:
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "app.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload"
    ], cwd=os.path.dirname(os.path.abspath(__file__)))
except KeyboardInterrupt:
    print()
    print("\nServer stopped.")
