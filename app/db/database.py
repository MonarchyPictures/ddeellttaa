from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os

# Use PostgreSQL exclusively for production, fallback to SQLite for local
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./intent_radar_v3.db").strip()

if not DATABASE_URL:
    # Should not happen with default, but good safety
    raise ValueError("DATABASE_URL environment variable is required.")

# Render/Heroku fix: SQLAlchemy requires 'postgresql://' instead of 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Connection args
if "sqlite" in DATABASE_URL:
    # SQLite-specific config for local testing
    connect_args = {"check_same_thread": False}
    engine_args = {
        "pool_pre_ping": True,
        "pool_recycle": 1800
    }
else:
    # PostgreSQL-specific config for production
    connect_args = {"options": "-c statement_timeout=30000"}  # 30s statement timeout
    engine_args = {
        "pool_pre_ping": True,
        "pool_recycle": 1800,  # Recycle every 30 mins
        "pool_size": 10,       # Safe size for Railway
        "max_overflow": 5
    }

# Create Engine with Pool Settings
# pool_pre_ping=True handles "database has gone away" errors
engine = create_engine(
    DATABASE_URL, 
    connect_args=connect_args,
    **engine_args
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
