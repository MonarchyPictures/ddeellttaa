from pydantic import BaseModel, ConfigDict
from datetime import datetime
import uuid


from typing import Optional

class NotificationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    agent_id: Optional[uuid.UUID]
    message: str
    lead_count: int
    read: bool
    created_at: datetime
