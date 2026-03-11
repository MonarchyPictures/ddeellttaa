"""
Delta-9 Lead Database Models
PostgreSQL schema with proper indexing for high-performance queries

Recommended for high scale: ClickHouse (columnar) for analytics + PostgreSQL for transactions
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List, Dict, Any

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, Boolean, 
    Text, JSON, ForeignKey, Index, UniqueConstraint, 
    create_engine, event, inspect
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
import os

# Database configuration
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "sqlite:///./delta9.db"  # Fallback for development
)

# Create engine with connection pooling for PostgreSQL
if DATABASE_URL.startswith("postgresql"):
    engine = create_engine(
        DATABASE_URL,
        pool_size=10,
        max_overflow=20,
        pool_pre_ping=True,  # Verify connections before using
        pool_recycle=3600,   # Recycle connections after 1 hour
    )
else:
    engine = create_engine(
        DATABASE_URL, 
        connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
    )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class LeadStatus(str, Enum):
    """Lead status lifecycle"""
    NEW = "new"
    QUALIFIED = "qualified"
    CONTACTED = "contacted"
    RESPONDED = "responded"
    CONVERTED = "converted"
    DISMISSED = "dismissed"
    ARCHIVED = "archived"


class SignalSource(str, Enum):
    """Signal source platforms"""
    REDDIT = "reddit"
    TWITTER = "twitter"
    FORUM = "forum"
    LINKEDIN = "linkedin"
    QUORA = "quora"
    FACEBOOK = "facebook"
    INSTAGRAM = "instagram"
    YOUTUBE = "youtube"
    OTHER = "other"


class SearchQuery(Base):
    """
    Search queries with expansion tracking
    
    Tracks what users are searching for and performance metrics
    """
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    original_query = Column(String(255), nullable=False, index=True)
    expanded_queries = Column(JSON, default=list)  # List of expanded phrases
    category = Column(String(100), index=True)  # e.g., "plumbing", "software"
    location = Column(String(100), default="Kenya")
    
    # Status
    is_active = Column(Boolean, default=True, index=True)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    last_searched = Column(DateTime, default=datetime.utcnow)
    
    # Metrics
    total_signals = Column(Integer, default=0)
    total_leads = Column(Integer, default=0)
    conversion_rate = Column(Float, default=0.0)
    
    # Relationships
    signals = relationship("Signal", back_populates="search_query")
    
    # Indexes for common queries
    __table_args__ = (
        Index('idx_search_query_active', 'is_active', 'created_at'),
        Index('idx_search_query_category', 'category', 'location'),
    )


class Signal(Base):
    """
    Raw signals from scrapers before processing
    
    This is the 'Signal Stream' persistent storage
    """
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # External IDs
    external_id = Column(String(255), index=True)  # Reddit post ID, Tweet ID, etc.
    
    # Source info
    source = Column(String(50), nullable=False, index=True)  # reddit, twitter, forum
    source_url = Column(Text)
    
    # Content
    title = Column(Text)
    content = Column(Text, nullable=False)
    raw_content = Column(Text)  # Original unprocessed
    
    # Author info
    author = Column(String(255), index=True)
    author_profile_url = Column(Text)
    author_karma = Column(Integer, default=0)  # Platform karma/score
    account_created_at = Column(DateTime)  # Account age for verification
    
    # Query tracking
    query_matched = Column(String(255), index=True)  # Which query found this
    search_query_id = Column(Integer, ForeignKey("search_queries.id"), nullable=True)
    search_query = relationship("SearchQuery", back_populates="signals")
    
    # Platform-specific
    subreddit = Column(String(100), index=True)  # For Reddit
    forum_name = Column(String(100))  # For forums
    
    # Intent scoring (from Intent Detection AI)
    intent_score = Column(Float, default=0.0, index=True)  # 0-1 buyer probability
    intent_category = Column(String(50), index=True)  # buying, researching, vendor
    buying_urgency = Column(String(20))  # immediate, soon, future
    keywords_matched = Column(ARRAY(String))  # PostgreSQL array
    
    # Verification scoring (from Lead Verification Layer)
    verification_score = Column(Float, default=0.0)  # 0-1 quality score
    verification_status = Column(String(20), default="pending")  # verified, suspicious, rejected
    rejection_reasons = Column(ARRAY(String))  # spam, bot, repost, too_old
    
    # Status
    is_processed = Column(Boolean, default=False, index=True)
    is_lead = Column(Boolean, default=False, index=True)
    is_duplicate = Column(Boolean, default=False)
    
    # Timestamps
    posted_at = Column(DateTime, index=True)  # When posted on source
    discovered_at = Column(DateTime, default=datetime.utcnow, index=True)
    processed_at = Column(DateTime)
    
    # Relationships
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=True)
    lead = relationship("Lead", back_populates="signals")
    
    # Extra data (platform-specific)
    extra_metadata = Column(JSONB, default=dict)  # PostgreSQL JSONB for performance (renamed from 'metadata' - reserved)
    
    # Indexes for performance
    __table_args__ = (
        # Composite indexes for common queries
        Index('idx_signals_source_intent', 'source', 'intent_score'),
        Index('idx_signals_author_source', 'author', 'source'),
        Index('idx_signals_discovered_intent', 'discovered_at', 'intent_score'),
        Index('idx_signals_verification', 'verification_status', 'is_lead'),
        Index('idx_signals_query', 'query_matched', 'discovered_at'),
        # Unique constraint to prevent duplicates
        UniqueConstraint('external_id', 'source', name='uix_signal_external'),
    )


class Lead(Base):
    """
    Verified leads with full contact and intent data
    
    CORRECT LEAD INTELLIGENCE ARCHITECTURE:
    Every lead MUST have these 5 mandatory fields:
    - text: The lead text/content
    - phone: Contact phone number  
    - source: Source platform (e.g., Telegram, Reddit)
    - url: URL to the source post/message
    - timestamp: ISO format timestamp when lead was created
    
    If any are missing → lead is discarded at validation layer
    
    This is the main 'Lead Database' table
    """
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # ═══════════════════════════════════════════════════════════════
    # 5 MANDATORY FIELDS - Every lead MUST have these
    # ═══════════════════════════════════════════════════════════════
    text = Column(Text, nullable=False, index=True, 
                  comment="Lead text/content - MANDATORY")
    phone = Column(String(50), nullable=False, index=True,
                   comment="Contact phone number - MANDATORY")
    source = Column(String(100), nullable=False, index=True,
                    comment="Source platform (Telegram, Reddit, etc.) - MANDATORY")
    url = Column(Text, nullable=False, index=True,
                 comment="URL to source post/message - MANDATORY")
    timestamp = Column(DateTime, nullable=False, index=True,
                       comment="ISO format timestamp - MANDATORY")
    
    # ═══════════════════════════════════════════════════════════════
    # LEAD FRESHNESS - Auto-calculated from timestamp
    # ═══════════════════════════════════════════════════════════════
    freshness = Column(String(20), default="unknown", index=True,
                       comment="Freshness: fresh/warm/cold/stale")
    age_hours = Column(Float, default=0.0, index=True,
                       comment="Age in hours since timestamp")
    
    # ═══════════════════════════════════════════════════════════════
    # Source tracking (legacy support)
    # ═══════════════════════════════════════════════════════════════
    signal_ids = Column(ARRAY(Integer), default=list)  # Source signal IDs
    sources = Column(ARRAY(String), default=list)  # ["reddit", "twitter"]
    
    # ═══════════════════════════════════════════════════════════════
    # Contact Info (extracted from signals)
    # ═══════════════════════════════════════════════════════════════
    name = Column(String(255))
    username = Column(String(255), index=True)
    email = Column(String(255), index=True)
    # Note: phone field above is the MANDATORY contact phone
    company = Column(String(255), index=True)
    job_title = Column(String(255))
    
    # ═══════════════════════════════════════════════════════════════
    # Location
    # ═══════════════════════════════════════════════════════════════
    location = Column(String(255), index=True)
    country = Column(String(100), default="Kenya", index=True)
    
    # ═══════════════════════════════════════════════════════════════
    # Intent Data (from Intent Detection AI)
    # ═══════════════════════════════════════════════════════════════
    intent_signals = Column(ARRAY(Text), default=list)  # What they said
    intent_category = Column(String(50), index=True)  # buying, researching
    intent_score = Column(Float, default=0.0, index=True)  # 0-1
    buying_urgency = Column(String(20), index=True)  # immediate, soon, future
    budget_hint = Column(String(100))  # Extracted budget mentions
    
    # ═══════════════════════════════════════════════════════════════
    # AI INTENT SCORING (NEW)
    # ═══════════════════════════════════════════════════════════════
    ai_intent_score = Column(Integer, default=0, index=True, comment="AI score 0-100")
    ai_temperature = Column(String(20), default="REJECT", index=True, comment="HOT/WARM/COLD/REJECT")
    ai_score_reasoning = Column(Text, comment="Explanation of AI score")
    ai_score_breakdown = Column(JSONB, default=dict, comment="Point breakdown")
    
    # ═══════════════════════════════════════════════════════════════
    # Verification Data (from Lead Verification Layer)
    # ═══════════════════════════════════════════════════════════════
    verification_score = Column(Float, default=0.0, index=True)  # 0-1
    verification_status = Column(String(20), default="pending")
    
    # ═══════════════════════════════════════════════════════════════
    # Engagement
    # ═══════════════════════════════════════════════════════════════
    profile_urls = Column(JSONB, default=dict)  # {"reddit": "...", "twitter": "..."}
    
    # ═══════════════════════════════════════════════════════════════
    # Status & Workflow
    # ═══════════════════════════════════════════════════════════════
    status = Column(String(20), default=LeadStatus.NEW, index=True)
    priority = Column(String(20), default="medium", index=True)  # low, medium, high, urgent
    
    # Scoring
    priority_score = Column(Float, default=0.0, index=True)  # Combined score for sorting
    
    # ═══════════════════════════════════════════════════════════════
    # CRM Integration
    # ═══════════════════════════════════════════════════════════════
    assigned_to = Column(String(255))  # Sales rep
    tags = Column(ARRAY(String), default=list)  # Custom tags
    notes = Column(Text)
    
    # Communication tracking
    contacted_at = Column(DateTime)
    contacted_via = Column(String(50))  # email, phone, dm
    response_at = Column(DateTime)
    converted_at = Column(DateTime)
    
    # ═══════════════════════════════════════════════════════════════
    # Timestamps
    # ═══════════════════════════════════════════════════════════════
    first_seen = Column(DateTime, default=datetime.utcnow, index=True)
    last_active = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    signals = relationship("Signal", back_populates="lead")
    activities = relationship("LeadActivity", back_populates="lead", order_by="desc(LeadActivity.created_at)")
    
    # Metadata
    custom_fields = Column(JSONB, default=dict)  # For extensibility
    
    # Indexes for performance
    __table_args__ = (
        # Composite indexes for common queries
        Index('idx_leads_status_priority', 'status', 'priority_score'),
        Index('idx_leads_intent_verification', 'intent_score', 'verification_score'),
        Index('idx_leads_country_status', 'country', 'status'),
        Index('idx_leads_urgency', 'buying_urgency', 'intent_score'),
        Index('idx_leads_first_seen', 'first_seen', 'id'),
        # NEW: Indexes for mandatory fields
        Index('idx_leads_source', 'source'),
        Index('idx_leads_phone', 'phone'),
        Index('idx_leads_timestamp', 'timestamp'),
        # GIN index for JSONB (PostgreSQL-specific)
        # Index('idx_leads_profile_urls', 'profile_urls', postgresql_using='gin'),
    )
    
    @property
    def has_mandatory_fields(self) -> bool:
        """
        Check if this lead has all 5 mandatory fields populated.
        
        Returns:
            True if text, phone, source, url, and timestamp are all present
        """
        return all([
            self.text and str(self.text).strip(),
            self.phone and str(self.phone).strip(),
            self.source and str(self.source).strip(),
            self.url and str(self.url).strip(),
            self.timestamp is not None
        ])


class LeadActivity(Base):
    """
    Activity log for leads (CRM-style)
    
    Tracks all interactions with a lead
    """
    __tablename__ = "lead_activities"
    
    id = Column(Integer, primary_key=True, index=True)
    lead_id = Column(Integer, ForeignKey("leads.id"), nullable=False, index=True)
    lead = relationship("Lead", back_populates="activities")
    
    activity_type = Column(String(50), nullable=False, index=True)  # email_sent, call_made, note_added
    description = Column(Text)
    
    performed_by = Column(String(255))  # User who performed action
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    
    activity_metadata = Column(JSONB, default=dict)  # Additional data (renamed from 'metadata' - reserved)


class LeadAnalytics(Base):
    """
    Analytics table for lead performance metrics
    
    For high-scale analytics, consider ClickHouse
    """
    __tablename__ = "lead_analytics"
    
    id = Column(Integer, primary_key=True, index=True)
    date = Column(DateTime, default=datetime.utcnow, index=True)
    
    # Daily metrics
    new_leads = Column(Integer, default=0)
    qualified_leads = Column(Integer, default=0)
    contacted_leads = Column(Integer, default=0)
    converted_leads = Column(Integer, default=0)
    
    # Source breakdown
    source_breakdown = Column(JSONB, default=dict)  # {"reddit": 10, "twitter": 5}
    
    # Intent breakdown
    intent_breakdown = Column(JSONB, default=dict)  # {"buying": 8, "researching": 7}
    
    # Performance
    avg_intent_score = Column(Float, default=0.0)
    avg_verification_score = Column(Float, default=0.0)
    conversion_rate = Column(Float, default=0.0)


# Database utilities
def get_db():
    """FastAPI dependency for database sessions"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("✅ Database tables created")


def reset_db():
    """Drop and recreate all tables (DANGER: loses all data)"""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    print("🔄 Database reset complete")


def get_db_stats():
    """Get database statistics"""
    db = SessionLocal()
    try:
        return {
            "leads": db.query(Lead).count(),
            "signals": db.query(Signal).count(),
            "search_queries": db.query(SearchQuery).count(),
            "activities": db.query(LeadActivity).count(),
        }
    finally:
        db.close()


# SQLAlchemy event listeners for auto-scoring
@event.listens_for(Lead, 'before_insert')
def calculate_priority_score_on_insert(mapper, connection, target):
    """Auto-calculate priority score before insert"""
    scores = [
        (target.intent_score or 0) * 0.35,
        (target.verification_score or 0) * 0.25,
        0.20 if target.email else 0,
        0.15 if target.phone else 0,
        0.10 if target.company else 0,
    ]
    target.priority_score = min(sum(scores), 1.0)
    
    # Set priority based on score
    if target.priority_score >= 0.8:
        target.priority = "urgent"
    elif target.priority_score >= 0.6:
        target.priority = "high"
    elif target.priority_score >= 0.4:
        target.priority = "medium"
    else:
        target.priority = "low"


@event.listens_for(Lead, 'before_update')
def update_timestamps_on_update(mapper, connection, target):
    """Update timestamps on changes"""
    target.updated_at = datetime.utcnow()
    target.last_active = datetime.utcnow()


@event.listens_for(Signal, 'before_update')
def mark_signal_processed(mapper, connection, target):
    """Mark signal as processed when lead_id is set"""
    if target.lead_id and not target.is_processed:
        target.is_processed = True
        target.processed_at = datetime.utcnow()


# Migration helper (for Alembic)
def run_migrations():
    """Run database migrations using Alembic"""
    import alembic.config
    alembic_args = [
        '--raiseerr',
        'upgrade', 'head',
    ]
    alembic.config.main(argv=alembic_args)


if __name__ == "__main__":
    # Test database connection and create tables
    print("Testing database connection...")
    init_db()
    
    # Print stats
    stats = get_db_stats()
    print(f"\nDatabase stats: {stats}")
    
    # Print table info
    print("\nTables created:")
    for table in Base.metadata.tables.keys():
        print(f"  - {table}")
