"""
Database initialization module.
Creates all tables on application startup.
"""
import logging

logger = logging.getLogger("delta9")

# CRITICAL: Import all models BEFORE importing engine/Base
# This ensures all tables are registered with SQLAlchemy metadata
logger.debug("Importing models to register with metadata...")
from app.db import models  # noqa: F401 - imports all models for side effects

# Now import engine and Base after models are registered
from app.db.database import engine
from app.db.base_class import Base


def init_db():
    """
    Initialize database by creating all tables.
    Safe to run multiple times (idempotent).
    """
    try:
        # Log all tables that will be created
        tables = list(Base.metadata.tables.keys())
        logger.info(f"📊 Registered tables: {tables}")
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info(f"✅ Database initialized with {len(tables)} tables")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize database: {e}")
        raise
