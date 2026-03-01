"""
Database initialization module.
Creates all tables on application startup.
"""
from app.db.database import engine
from app.db.base_class import Base
from app.db import models  # Import all models to register them
import logging

logger = logging.getLogger("delta9")


def init_db():
    """
    Initialize database by creating all tables.
    Safe to run multiple times (idempotent).
    """
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database tables initialized successfully")
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
