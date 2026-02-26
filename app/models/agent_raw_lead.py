import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Boolean, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base


class AgentRawLead(Base):
    __tablename__ = "agent_raw_leads"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    agent_id = Column(UUID(as_uuid=True), ForeignKey("agents.id"))

    raw_text = Column(Text)
    phone = Column(String, nullable=True)
    source = Column(String, nullable=True)
    source_url = Column(String, nullable=True)

    intent_score = Column(Float, default=0.0)
    geo_score = Column(Float, default=0.0)
    ranked_score = Column(Float, default=0.0)

    notified = Column(Boolean, default=False)

    discovered_at = Column(DateTime, default=datetime.utcnow)

    agent = relationship("Agent", back_populates="raw_leads")
