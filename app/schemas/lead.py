from pydantic import BaseModel, ConfigDict, Field, field_validator
from typing import Optional
from datetime import datetime
import uuid


class LeadBase(BaseModel):
    """
    Correct Lead Intelligence Architecture
    
    Every lead MUST have these 5 mandatory fields:
    - text: The lead text/content
    - phone: Contact phone number
    - source: Source platform (e.g., Telegram, Reddit)
    - url: URL to the source post/message
    - timestamp: ISO format timestamp when lead was created
    
    If any are missing → lead is discarded
    """
    text: str = Field(..., description="Lead text/content")
    phone: str = Field(..., description="Contact phone number")
    source: str = Field(..., description="Source platform")
    url: str = Field(..., description="URL to source")
    timestamp: str = Field(..., description="ISO format timestamp")


class LeadResponse(BaseModel):
    """
    Lead Response Schema with 5 mandatory fields + freshness
    """
    model_config = ConfigDict(from_attributes=True)
    
    id: uuid.UUID
    
    # 5 MANDATORY FIELDS - Every lead must have these
    text: str = Field(..., description="Lead text/content")
    phone: str = Field(..., description="Contact phone number")
    source: str = Field(..., description="Source platform")
    url: str = Field(..., description="URL to source")
    timestamp: str = Field(..., description="ISO format timestamp")
    
    # LEAD FRESHNESS - Auto-calculated
    freshness: Optional[str] = Field(None, description="fresh/warm/cold/stale")
    age_hours: Optional[float] = Field(None, description="Age in hours")
    
    # Optional additional fields
    title: Optional[str] = None
    content: Optional[str] = None
    query: Optional[str] = None
    location: Optional[str] = None
    confidence: Optional[float] = None
    contact_phone: Optional[str] = None  # Duplicate of phone for backward compat
    contact_email: Optional[str] = None
    contact_flag: Optional[str] = None
    verification_flag: Optional[str] = None
    intent_type: Optional[str] = None
    is_verified_signal: Optional[int] = None
    created_at: Optional[datetime] = None


class LeadValidator:
    """
    Validates leads according to the Correct Lead Intelligence Architecture.
    
    Every lead must have 5 mandatory fields:
    - text
    - phone
    - source
    - url
    - timestamp
    
    If any are missing → discard lead
    """
    
    MANDATORY_FIELDS = ['text', 'phone', 'source', 'url', 'timestamp']
    
    @classmethod
    def validate(cls, lead_data: dict) -> tuple[bool, Optional[str]]:
        """
        Validate a lead has all mandatory fields.
        
        Returns:
            (is_valid, error_message)
            - is_valid: True if all mandatory fields are present and non-empty
            - error_message: Reason for rejection if invalid, None if valid
        """
        for field in cls.MANDATORY_FIELDS:
            value = lead_data.get(field)
            if value is None or (isinstance(value, str) and not value.strip()):
                return False, f"Missing mandatory field: {field}"
        return True, None
    
    @classmethod
    def validate_or_discard(cls, lead_data: dict) -> Optional[dict]:
        """
        Validate a lead and return None if it should be discarded.
        
        Returns:
            The lead data if valid, None if it should be discarded
        """
        is_valid, error = cls.validate(lead_data)
        if not is_valid:
            print(f"[LeadValidator] ❌ Lead discarded: {error}")
            print(f"[LeadValidator]    Data: {lead_data}")
            return None
        return lead_data


# Example of correct lead structure:
LEAD_EXAMPLE = {
    "text": "Looking for Toyota Vitz 2016",
    "phone": "0723898087",
    "source": "Telegram",
    "url": "https://t.me/kenya_cars/83922",
    "timestamp": "2026-03-08T10:33"
}
