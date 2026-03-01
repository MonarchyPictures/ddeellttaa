from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
import hashlib
from app.db.base_class import Base

# Imported definitions
from app.models.lead import Lead, ContactStatus, CRMStatus
from app.models.agent import Agent

class BuyerLead(Base):
    """
    🎯 BUYERS TABLE (MINIMAL) - Standardized schema for buyer-only ingestion.
    """
    __tablename__ = "buyer_leads"

    id = Column(String, primary_key=True, index=True)
    name = Column(String)
    platform = Column(String)
    intent = Column(String)
    location = Column(String)
    contact = Column(String)
    contact_status = Column(String)
    confidence = Column(Float) # SQL REAL maps to Float in SQLAlchemy
    posted_at = Column(DateTime)
    created_at = Column(DateTime, server_default=func.now())

class AgentRunLog(Base):
    __tablename__ = "agent_run_logs"

    id = Column(Integer, primary_key=True)
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id", ondelete="CASCADE"), index=True, nullable=False)
    run_time = Column(DateTime, default=func.now())
    leads_found = Column(Integer, default=0)
    errors = Column(Text, nullable=True)
    duration_ms = Column(Integer, default=0)

    agent = relationship("Agent", backref="run_logs")

    def to_dict(self):
        return {
            "id": self.id,
            "agent_id": str(self.agent_id),
            "run_time": self.run_time.isoformat() if self.run_time else None,
            "leads_found": self.leads_found,
            "errors": self.errors,
            "duration_ms": self.duration_ms
        }

class BuyerIntent(Base):
    __tablename__ = "buyer_intents"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(String, index=True) # The agent or user who has this intent
    interest_type = Column(String, index=True) # Flexible: "Toyota", "iPhone", "Apartment"
    vehicle_type = Column(String, index=True) # DEPRECATED: use interest_type
    
    # Matching Criteria
    keywords = Column(String, nullable=True) # Comma-separated keywords (New Field)
    budget_min = Column(Float, default=0.0)
    budget_max = Column(Float)
    location = Column(String, index=True)
    urgency = Column(String, default="medium") # high, medium, low
    
    # Notification Preferences (New Fields)
    email = Column(String, nullable=True)
    phone = Column(String, nullable=True)
    notification_preferences = Column(String, default="email,sms") # "email,sms,websocket"
    
    # Metadata
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, onupdate=func.now())

    @property
    def min_price(self):
        return self.budget_min

    @property
    def max_price(self):
        return self.budget_max

    def to_dict(self):
        return {
            "id": self.id,
            "user_id": self.user_id,
            "interest_type": self.interest_type or self.vehicle_type,
            "keywords": self.keywords,
            "vehicle_type": self.vehicle_type, # Legacy support
            "budget_min": self.budget_min,
            "budget_max": self.budget_max,
            "location": self.location,
            "urgency": self.urgency,
            "email": self.email,
            "phone": self.phone,
            "notification_preferences": self.notification_preferences,
            "is_active": bool(self.is_active),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

class SearchPattern(Base):
    __tablename__ = "search_patterns"
    
    id = Column(Integer, primary_key=True)
    keyword = Column(String, unique=True)
    category = Column(String)
    is_active = Column(Integer, default=1)

class ActivityLog(Base):
    __tablename__ = "activity_logs"
    
    id = Column(Integer, primary_key=True)
    event_type = Column(String, index=True) # WHATSAPP_TAP, LEAD_DISCOVERED, SEARCH_PERFORMED
    lead_id = Column(UUID(as_uuid=True), ForeignKey("leads.id"), nullable=True)
    session_id = Column(String, index=True, nullable=True) # To group user behavior
    timestamp = Column(DateTime, server_default=func.now(), index=True)
    extra_metadata = Column(JSON, nullable=True) # For additional info like product name, etc.

class ScraperMetric(Base):
    __tablename__ = "scraper_metrics"
    
    id = Column(Integer, primary_key=True)
    scraper_name = Column(String, unique=True, index=True)
    runs = Column(Integer, default=0)
    leads_found = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    failures = Column(Integer, default=0)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime)
    history = Column(JSON) # List of last 20 runs
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class CategoryMetric(Base):
    __tablename__ = "category_metrics"
    
    id = Column(Integer, primary_key=True)
    category_name = Column(String, unique=True, index=True)
    total_leads = Column(Integer, default=0)
    verified_leads = Column(Integer, default=0)
    verified_rate = Column(Float, default=0.0)
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

class SystemSetting(Base):
    __tablename__ = "system_settings"
    
    id = Column(Integer, primary_key=True)
    key = Column(String, unique=True, index=True)
    value = Column(JSON)
    updated_at = Column(DateTime, onupdate=func.now())


class Cache(Base):
    """
    🗄️ SEARCH CACHE TABLE - Stores search results to reduce API calls.
    """
    __tablename__ = "cache"

    id = Column(Integer, primary_key=True)
    query = Column(String, index=True)  # Cache key (query:location)
    location = Column(String, default="default")
    data = Column(JSON)  # Cached results
    created_at = Column(DateTime, server_default=func.now())
    expires_at = Column(DateTime, index=True)  # TTL for cache entries
    
    # Index for fast lookup by query
    __table_args__ = (
        UniqueConstraint('query', name='uix_cache_query'),
    )
