from pydantic import BaseModel
from datetime import datetime
import uuid


from typing import Optional

class NotificationResponse(BaseModel):
    id: uuid.UUID
    agent_id: Optional[uuid.UUID]
    message: str
    lead_count: int
    read: bool
    created_at: datetime

    class Config:
        from_attributes = True
