from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class AgentCreate(BaseModel):
    name: str
    query: str
    location: Optional[str] = "Kenya"
    interval_hours: int = 2
    duration_days: int = 7


class AgentResponse(BaseModel):
    id: uuid.UUID
    name: str
    query: str
    location: Optional[str]
    interval_hours: int
    duration_days: int
    start_time: Optional[datetime]
    end_time: Optional[datetime]
    next_run_at: Optional[datetime]
    active: bool
    leads_count: int = 0
    high_intent_count: int = 0
    last_run: Optional[datetime] = None

    class Config:
        orm_mode = True
