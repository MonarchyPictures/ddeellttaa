import uuid
from datetime import datetime, timedelta
from sqlalchemy import Column, String, Integer, Boolean, DateTime
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.base_class import Base

class Agent(Base):
    __tablename__ = "agents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    name = Column(String, nullable=False)
    query = Column(String, nullable=False)
    location = Column(String, nullable=True)

    interval_hours = Column(Integer, default=2)
    duration_days = Column(Integer, default=7)

    start_time = Column(DateTime, default=datetime.utcnow)
    end_time = Column(DateTime)

    next_run_at = Column(DateTime, default=datetime.utcnow, index=True)
    active = Column(Boolean, default=True, index=True)
    is_running = Column(Boolean, default=False, index=True)
    last_heartbeat = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    created_at = Column(DateTime, server_default=func.now())

    raw_leads = relationship("AgentRawLead", back_populates="agent")

    def initialize_schedule(self):
        now = datetime.utcnow()
        self.start_time = now
        self.end_time = now + timedelta(days=self.duration_days)
        self.next_run_at = now

    def to_dict(self):
        return {
            "id": str(self.id),
            "name": self.name,
            "query": self.query,
            "location": self.location,
            "interval_hours": self.interval_hours,
            "duration_days": self.duration_days,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "end_time": self.end_time.isoformat() if self.end_time else None,
            "next_run_at": self.next_run_at.isoformat() if self.next_run_at else None,
            "active": self.active,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
