"""
Delta-9 Database Models
Lead Generation Intelligence System
"""
from datetime import datetime
from enum import Enum
from typing import Optional, List

from sqlalchemy import (
    Column, Integer, String, Float, DateTime, 
    Text, Boolean, JSON, create_engine, event
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
import os

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./delta9.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


class LeadStatus(str, Enum):
    NEW = "new"
    VERIFIED = "verified"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    DISMISSED = "dismissed"


class SignalSource(str, Enum):
    REDDIT = "reddit"
    TWITTER = "twitter"
    FORUM = "forum"
    LINKEDIN = "linkedin"
    QUORA = "quora"


class SearchQuery(Base):
    """User search queries with expansion"""
    __tablename__ = "search_queries"
    
    id = Column(Integer, primary_key=True, index=True)
    original_query = Column(String(255), nullable=False, index=True)
    expanded_queries = Column(JSON, default=list)  # List of expanded phrases
    category = Column(String(100))  # e.g., "plumbing", "software", "consulting"
    location = Column(String(100), default="Kenya")
    created_at = Column(DateTime, default=datetime.utcnow)
    last_searched = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    total_signals = Column(Integer, default=0)
    total_leads = Column(Integer, default=0)


class Signal(Base):
    """Raw signals from scrapers before intent detection"""
    __tablename__ = "signals"
    
    id = Column(Integer, primary_key=True, index=True)
    external_id = Column(String(255), index=True)  # Reddit post ID, Tweet ID, etc.
    source = Column(String(50), nullable=False, index=True)  # reddit, twitter, forum
    source_url = Column(Text)
    author = Column(String(255), index=True)
    author_profile_url = Column(Text)
    
    # Content
    title = Column(Text)
    content = Column(Text, nullable=False)
    raw_content = Column(Text)  # Original unprocessed content
    
    # Metadata
    query_matched = Column(String(255))  Which query triggered this
    subreddit = Column(String(100))  # For Reddit
    forum_name = Column(String(100))  # For forums
    
    # Scoring
    intent_score = Column(Float, default=0.0)  # 0-1 score
    relevance_score = Column(Float, default=0.0)  # 0-1 score
    
    # Status
    is_processed = Column(Boolean, default=False)
    is_lead = Column(Boolean, default=False)
    lead_id = Column(Integer, nullable=True)
    
    # Timestamps
    posted_at = Column(DateTime)  # When it was posted on source
    discovered_at = Column(DateTime, default=datetime.utcnow)
    processed_at = Column(DateTime)
    
    # Extra data
    metadata = Column(JSON, default=dict)  # Platform-specific data


class Lead(Base):
    """Verified leads with contact info"""
    __tablename__ = "leads"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Source tracking
    signal_ids = Column(JSON, default=list)  # List of signal IDs that created this lead
    sources = Column(JSON, default=list)  # ["reddit", "twitter"]
    
    # Contact Info (extracted from signals)
    name = Column(String(255))
    username = Column(String(255), index=True)
    email = Column(String(255), index=True)
    phone = Column(String(50))
    company = Column(String(255))
    job_title = Column(String(255))
    
    # Location
    location = Column(String(255))
    country = Column(String(100), default="Kenya")
    
    # Intent Data
    intent_signals = Column(JSON, default=list)  # What they said
    intent_category = Column(String(100))  # e.g., "buying", "researching", "complaining"
    intent_score = Column(Float, default=0.0)  # 0-1
    buying_urgency = Column(String(20))  # "immediate", "soon", "future"
    budget_hint = Column(String(50))  # Extracted budget mentions
    
    # Engagement
    profile_urls = Column(JSON, default=dict)  # {"reddit": "...", "twitter": "..."}
    
    # Status & Scoring
    status = Column(String(20), default=LeadStatus.NEW, index=True)
    verification_score = Column(Float, default=0.0)  # How sure we are this is a real lead
    priority_score = Column(Float, default=0.0)  # Combined score for sorting
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_active = Column(DateTime, default=datetime.utcnow)
    contacted_at = Column(DateTime)
    converted_at = Column(DateTime)
    
    # Notes
    notes = Column(Text)
    tags = Column(JSON, default=list)


# Database dependency for FastAPI
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Create tables
def init_db():
    Base.metadata.create_all(bind=engine)


# Event listeners for scoring
@event.listens_for(Lead, 'before_insert')
def calculate_priority_score(mapper, connection, target):
    """Auto-calculate priority score before insert"""
    scores = [
        target.intent_score * 0.4,
        target.verification_score * 0.3,
        0.3 if target.email else 0,
        0.2 if target.phone else 0,
    ]
    target.priority_score = min(sum(scores), 1.0)


@event.listens_for(Lead, 'before_update')
def update_last_active(mapper, connection, target):
    """Update last_active on changes"""
    target.last_active = datetime.utcnow()
