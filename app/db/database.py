from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
import os

# PostgreSQL is REQUIRED in production (Railway provides this)
# Local development can use: export DATABASE_URL="sqlite:///./local.db"
DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL environment variable is required. "
        "In Railway, add a Postgres plugin. "
        "For local dev: export DATABASE_URL='sqlite:///./local.db'"
    )

# Render/Heroku fix: SQLAlchemy requires 'postgresql://' instead of 'postgres://'
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

# Connection args
if "sqlite" in DATABASE_URL:
    # SQLite-specific config for local testing only
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
