from fastapi import APIRouter, Depends, HTTPException, Request, Header, BackgroundTasks, Response
from sqlalchemy.orm import Session
from datetime import datetime, timezone, timedelta
import os
import logging

from app.db import models
from app.db.database import get_db, SessionLocal
from app.config import PIPELINE_MODE
from app.api.deps import verify_api_key

router = APIRouter(tags=["Admin"])

# Agent routes moved to app/api/routes/agents.py

@router.get("/settings", dependencies=[Depends(verify_api_key)])
def get_settings():
    """Return platform settings."""
    return {
        "notifications_enabled": True,
        "sound_enabled": True,
        "region": "Kenya",
        "currency": "KES",
        "geo_lock": "Kenya",
        "mode": "PROD_STRICT"
    }

# Notification routes moved to app/api/routes/notifications.py
