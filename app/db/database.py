"""
Database connection and session management.

Provides SQLAlchemy engine and session factory with proper configuration.
Optimized for PostgreSQL with connection pooling.
"""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.logging_config import get_logger

logger = get_logger(__name__)


def create_engine_with_config():
    """Create SQLAlchemy engine with appropriate configuration."""
    
    # Base engine arguments
    engine_kwargs = {
        "pool_pre_ping": True,  # Verify connections before using
        "echo": settings.DATABASE_ECHO,
    }
    
    # PostgreSQL-specific configuration
    if settings.DATABASE_URL.startswith("postgresql"):
        engine_kwargs.update({
            "pool_size": settings.DATABASE_POOL_SIZE,
            "max_overflow": settings.DATABASE_MAX_OVERFLOW,
            "pool_recycle": 3600,  # Recycle connections after 1 hour
            "pool_timeout": 30,    # Timeout for getting connection from pool
        })
    else:
        # SQLite configuration (for development/testing)
        engine_kwargs["poolclass"] = NullPool
        engine_kwargs["connect_args"] = {"check_same_thread": False}
    
    return create_engine(settings.DATABASE_URL, **engine_kwargs)


# Create the engine
engine = create_engine_with_config()

# Create session factory
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db() -> Generator[Session, None, None]:
    """
    Dependency for FastAPI to get database sessions.
    
    Yields a database session and ensures it's closed after use.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """
    Context manager for database sessions.
    
    Use this when you need a database session outside of FastAPI's
    dependency injection (e.g., in background tasks).
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        db.rollback()
        logger.error("Database error", extra={"error": str(e)})
        raise
    finally:
        db.close()


def init_db() -> None:
    """
    Initialize the database by creating all tables.
    
    Note: In production, use Alembic migrations instead of this.
    """
    from app.db.base_class import Base
    
    # Import all models to ensure they're registered
    import app.models  # noqa: F401
    
    logger.info("Creating database tables...")
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created")


def check_db_connection() -> bool:
    """Check if database connection is working."""
    try:
        with engine.connect() as conn:
            conn.execute("SELECT 1")
        return True
    except Exception as e:
        logger.error("Database connection failed", extra={"error": str(e)})
        return False
