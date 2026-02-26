from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid


class LeadResponse(BaseModel):
    id: uuid.UUID
    title: Optional[str]
    content: Optional[str]
    source: Optional[str]
    url: Optional[str]
    query: Optional[str]
    location: Optional[str]
    confidence: Optional[float]
    contact_phone: Optional[str]
    contact_email: Optional[str]
    contact_flag: Optional[str]
    verification_flag: Optional[str]
    intent_type: Optional[str]
    is_verified_signal: Optional[int]
    created_at: datetime

    class Config:
        from_attributes = True
