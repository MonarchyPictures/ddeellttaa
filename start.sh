#!/bin/bash
# Startup script for Delta-9 on Render/Railway

# Use PORT from environment, default to 8000 if not set
PORT=${PORT:-8000}

echo "Starting Delta-9 API on port $PORT"
uvicorn app.main:app --host 0.0.0.0 --port $PORT
