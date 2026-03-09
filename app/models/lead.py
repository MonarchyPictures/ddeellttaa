from sqlalchemy import Column, String, Float, DateTime, JSON, ForeignKey, Enum, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum
import uuid
from app.db.base_class import Base

class ContactStatus(enum.Enum):
    NOT_CONTACTED = "not_contacted"
    CONTACTED = "contacted"
    CONVERTED = "converted"
    REJECTED = "rejected"

class CRMStatus(enum.Enum):
    NEW = "NEW"
    CONTACTED = "CONTACTED"
    REPLIED = "REPLIED"
    NEGOTIATING = "NEGOTIATING"
    CONVERTED = "CONVERTED"
    DEAD = "DEAD"

class Lead(Base):
    __tablename__ = "leads"

    # --- Core Fields (User Requested) ---
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    buyer_name = Column(String, nullable=True, index=True)
    title = Column(String, nullable=False, index=True) # Was product_category
    description = Column(Text, nullable=True) # Added for matching context
    product_category = Column(String, index=True) # Explicit category field
    price = Column(String, nullable=True) # Was Float
    location = Column(String, nullable=True)
    source = Column(String, nullable=False, index=True) # Was source_platform
    url = Column(String, nullable=False, unique=True) # Was source_url
    intent_score = Column(Float, nullable=False, index=True)
    created_at = Column(DateTime, default=func.now(), index=True)

    # --- Extended Schema (Preserved) ---
    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True, index=True)
    query = Column(String, nullable=True)
    contact_phone = Column(String, index=True)
    contact_email = Column(String, index=True)
    quantity_requirement = Column(String)
    location_raw = Column(String)
    radius_km = Column(Float, default=0.0)
    request_timestamp = Column(DateTime, index=True)
    
    # WhatsApp Integration
    whatsapp_link = Column(String)
    contact_method = Column(String)
    
    # Status & Flags
    status = Column(Enum(CRMStatus), default=CRMStatus.NEW, index=True)
    http_status = Column(Integer)
    latency_ms = Column(Integer)
    
    # Standardized Buyer Fields
    is_hot_lead = Column(Integer, default=0, index=True)
    buyer_request_snippet = Column(String)
    urgency_level = Column(String, default="low", index=True)
    confidence_score = Column(Float, default=0.0, index=True)
    is_saved = Column(Integer, default=0)
    is_verified_signal = Column(Integer, default=1, index=True)
    verification_flag = Column(String, default="verified")
    notes = Column(String)
    contact_source = Column(String)
    contact_flag = Column(String, default="ok")
    budget = Column(String)
    buyer_match_score = Column(Float, default=0.0)
    contact_status = Column(String, default="verified")
    property_country = Column(String, default="Kenya")
    geo_score = Column(Float, default=0.0)
    geo_strength = Column(String, default="low")
    geo_region = Column(String, default="Global")
    
    # Ranking
    ranked_score = Column(Float, default=0.0, index=True)
    rank_score = Column(Float, default=0.0, index=True)
    
    # Response Tracking
    response_count = Column(Integer, default=0)
    non_response_flag = Column(Integer, default=0)
    
    # Hyper-Specific Intent
    readiness_level = Column(String)
    urgency_score = Column(Float)
    budget_info = Column(String)
    
    # Kenya-Optimized Scoring Components
    budget_score = Column(Float, default=0.0)
    location_score = Column(Float, default=0.0)
    badge = Column(String, default="COLD", index=True)  # HOT, WARM, COLD, REJECT
    product_specs = Column(JSON)
    deal_probability = Column(Float)
    intent_type = Column(String)
    
    # Smart Matching
    match_score = Column(Float, default=0.0)
    compatibility_status = Column(String)
    match_details = Column(JSON)
    
    # Intent Analysis
    payment_method_preference = Column(String)
    
    # Local Advantage
    delivery_range_score = Column(Float, default=0.0)
    neighborhood = Column(String)
    local_pickup_preference = Column(Integer, default=0)
    delivery_constraints = Column(String)
    
    # Deal Readiness
    decision_authority = Column(Integer, default=0)
    prior_research_indicator = Column(Integer, default=0)
    comparison_indicator = Column(Integer, default=0)
    upcoming_deadline = Column(DateTime)
    
    # Real-Time & Competitive
    availability_status = Column(String)
    competition_count = Column(Integer)
    is_unique_request = Column(Integer)
    optimal_response_window = Column(String)
    peak_response_time = Column(String)
    
    # Contact Verification
    is_contact_verified = Column(Integer, default=0)
    contact_reliability_score = Column(Float, default=0.0)
    preferred_contact_method = Column(String)
    disposable_email_flag = Column(Integer, default=0)
    contact_metadata = Column(JSON)
    
    # Response Tracking (Extended)
    average_response_time_mins = Column(Float)
    conversion_rate = Column(Float, default=0.0)
    
    # Comprehensive Lead Intelligence
    buyer_history = Column(JSON)
    platform_activity_level = Column(String)
    past_response_rate = Column(Float, default=0.0)
    market_price_range = Column(String)
    seasonal_demand = Column(String)
    supply_status = Column(String)
    conversion_signals = Column(JSON)
    talking_points = Column(JSON)
    competitive_advantages = Column(JSON)
    pricing_strategy = Column(String)
    
    verification_badges = Column(JSON)
    is_genuine_buyer = Column(Integer, default=1)
    last_activity = Column(DateTime)

    tap_count = Column(Integer, default=0)
    
    # Deduplication
    content_hash = Column(String, index=True)

    __table_args__ = (
        UniqueConstraint("url", name="uix_source_url"),
        {'extend_existing': True}
    )

    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())

    # --- Compatibility Properties ---
    # @property
    # def product_category(self):
    #     return self.title
        
    # @product_category.setter
    # def product_category(self, value):
    #     self.title = value

    @property
    def source_platform(self):
        return self.source
        
    @source_platform.setter
    def source_platform(self, value):
        self.source = value

    @property
    def source_url(self):
        return self.url
        
    @source_url.setter
    def source_url(self, value):
        self.url = value

    @property
    def buyer_intent_snippet(self):
        return self.buyer_request_snippet

    @buyer_intent_snippet.setter
    def buyer_intent_snippet(self, value):
        self.buyer_request_snippet = value

    @property
    def contact_whatsapp(self):
        return self.whatsapp_link

    @contact_whatsapp.setter
    def contact_whatsapp(self, value):
        self.whatsapp_link = value

    def __init__(self, **kwargs):
        # Map old aliases to new columns
        # product_category is now a real column, so we don't map it to title anymore
        # if 'product_category' in kwargs:
        #    kwargs['title'] = kwargs.pop('product_category')
        
        if 'source_platform' in kwargs:
            kwargs['source'] = kwargs.pop('source_platform')
        if 'source_url' in kwargs:
            kwargs['url'] = kwargs.pop('source_url')
        
        # Map location_raw to location if location is not set
        if 'location_raw' in kwargs and 'location' not in kwargs:
            kwargs['location'] = kwargs['location_raw']
        elif 'location' in kwargs and 'location_raw' not in kwargs:
            kwargs['location_raw'] = kwargs['location']
            
        # User example aliases
        if 'content' in kwargs:
            self.buyer_request_snippet = kwargs.pop('content')
        if 'confidence' in kwargs:
            self.confidence_score = kwargs.pop('confidence')
            
        super().__init__(**kwargs)
        
        if not getattr(self, 'id', None):
            self.id = uuid.uuid4()

    def to_dict(self):
        from app.utils.outreach import whatsapp_link
        
        # Try to generate message if possible, but avoid complex imports if not needed
        msg = "Contact for details"
        try:
             from app.intelligence.outreach import OutreachEngine
             outreach_engine = OutreachEngine()
             msg = outreach_engine.generate_message(self)
        except:
             pass

        phone = self.contact_phone or self.whatsapp_link
        
        return {
            "id": str(self.id),
            "title": self.title,
            "buyer_name": self.buyer_name,
            "price": self.price,
            "location": self.location,
            "source": self.source,
            "url": self.url,
            "intent_score": self.intent_score,
            "created_at": self.created_at.isoformat() if self.created_at is not None else None,
            
            # Mapped/Computed fields
            "query": self.title, # Frontend expects 'query' or 'product'
            "product": self.title,
            "intent_strength": self.intent_score,
            "intent_label": self.urgency_level or "medium",
            "confidence": self.confidence_score,
            "whatsapp_url": whatsapp_link(phone, msg) if phone else self.whatsapp_link,
            "tap_count": self.tap_count or 0,
            
            # Legacy fields
            "lead_id": str(self.id),
            "phone": self.contact_phone,
            "whatsapp_link": self.whatsapp_link,
            "status": self.status.value if hasattr(self.status, 'value') else self.status,
            "source_url": self.url,
            "buyer_intent_quote": self.buyer_request_snippet,
            "outreach_suggestion": msg,
            "is_hot_lead": bool(self.is_hot_lead),
            "buyer_match_score": self.buyer_match_score or 0.0,
            "geo_score": self.geo_score or 0.0,
            "geo_strength": self.geo_strength or "low",
            "geo_region": self.geo_region or "Global",
            "ranked_score": self.ranked_score or 0.0,
            
            # Kenya-optimized scoring components
            "budget_score": self.budget_score or 0.0,
            "location_score": self.location_score or 0.0,
            "badge": self.badge or "COLD",
            
            "contact_flag": self.contact_flag,
            "verification_flag": self.verification_flag,
            "intent_type": self.intent_type,
            "contact_email": self.contact_email,
            "is_verified_signal": self.is_verified_signal
        }
