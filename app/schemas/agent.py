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


class AgentExecutionStatus(BaseModel):
    """Real-time execution status for an agent."""
    status: str  # "running", "scheduled", "due", "inactive"
    is_active: bool
    is_running: bool
    last_run: Optional[datetime]
    next_run: Optional[datetime]
    time_until_next: Optional[str]  # Human readable like "2h 30m"
    interval_hours: int


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
    is_running: bool = False
    leads_count: int = 0
    high_intent_count: int = 0
    last_run: Optional[datetime] = None
    execution_status: Optional[AgentExecutionStatus] = None

    model_config = {"from_attributes": True}
