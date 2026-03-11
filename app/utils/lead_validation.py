"""
Lead Validation Utility
Implements the Correct Lead Intelligence Architecture

Every lead must have 5 mandatory fields:
- text: The lead text/content
- phone: Contact phone number
- source: Source platform (e.g., Telegram, Reddit)
- url: URL to the source post/message
- timestamp: ISO format timestamp

If any are missing → lead is discarded

LEAD FRESHNESS FILTER:
- Fresh = < 24 hours old
- Warm = < 3 days old  
- Cold = < 7 days old
- Discard = > 7 days old (REJECTED)
"""
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple, Union
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class LeadFreshness(str, Enum):
    """Lead freshness categories based on age"""
    FRESH = "fresh"      # < 24 hours
    WARM = "warm"        # < 3 days
    COLD = "cold"        # < 7 days
    STALE = "stale"      # >= 7 days (DISCARD)


class LeadValidationError(Exception):
    """Raised when a lead fails mandatory field validation"""
    pass


class LeadFreshnessError(Exception):
    """Raised when a lead is too old (stale)"""
    pass


class LeadValidator:
    """
    Validates leads according to the Correct Lead Intelligence Architecture.
    
    Every lead MUST have 5 mandatory fields:
    1. text - The lead text/content
    2. phone - Contact phone number
    3. source - Source platform (e.g., Telegram, Reddit)
    4. url - URL to the source post/message
    5. timestamp - ISO format timestamp
    
    If any are missing → discard lead
    
    Example of valid lead:
    {
        "text": "Looking for Toyota Vitz 2016",
        "phone": "0723898087",
        "source": "Telegram",
        "url": "https://t.me/kenya_cars/83922",
        "timestamp": "2026-03-08T10:33"
    }
    """
    
    MANDATORY_FIELDS = ['text', 'phone', 'source', 'url', 'timestamp']
    
    @classmethod
    def validate(cls, lead_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Validate a lead has all mandatory fields.
        
        Args:
            lead_data: Dictionary containing lead data
            
        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if all mandatory fields are present and non-empty
            - error_message: Reason for rejection if invalid, None if valid
        """
        if not isinstance(lead_data, dict):
            return False, f"Lead data must be a dict, got {type(lead_data)}"
        
        for field in cls.MANDATORY_FIELDS:
            value = lead_data.get(field)
            
            # Check if field exists
            if value is None:
                return False, f"Missing mandatory field: {field}"
            
            # Check if string fields are non-empty
            if isinstance(value, str) and not value.strip():
                return False, f"Empty mandatory field: {field}"
            
            # Check timestamp is valid
            if field == 'timestamp' and isinstance(value, str):
                try:
                    # Try to parse ISO format
                    datetime.fromisoformat(value.replace('Z', '+00:00'))
                except ValueError:
                    return False, f"Invalid timestamp format: {value}"
        
        return True, None
    
    @classmethod
    def validate_or_discard(cls, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Validate a lead and return None if it should be discarded.
        
        Args:
            lead_data: Dictionary containing lead data
            
        Returns:
            The lead data if valid, None if it should be discarded
        """
        is_valid, error = cls.validate(lead_data)
        if not is_valid:
            logger.warning(f"[LeadValidator] ❌ Lead discarded: {error}")
            logger.debug(f"[LeadValidator]    Data: {lead_data}")
            return None
        return lead_data
    
    @classmethod
    def validate_list(cls, leads: list) -> Tuple[list, list]:
        """
        Validate a list of leads, separating valid from invalid.
        
        Args:
            leads: List of lead dictionaries
            
        Returns:
            Tuple of (valid_leads, rejected_leads_with_reasons)
        """
        valid = []
        rejected = []
        
        for lead in leads:
            is_valid, error = cls.validate(lead)
            if is_valid:
                valid.append(lead)
            else:
                rejected.append({
                    'lead': lead,
                    'reason': error
                })
        
        if rejected:
            logger.warning(f"[LeadValidator] Discarded {len(rejected)}/{len(leads)} leads missing mandatory fields")
        
        return valid, rejected
    
    @classmethod
    def enforce_strict(cls, lead_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Strict validation that raises exception if lead is invalid.
        
        Args:
            lead_data: Dictionary containing lead data
            
        Returns:
            The lead data if valid
            
        Raises:
            LeadValidationError: If any mandatory field is missing
        """
        is_valid, error = cls.validate(lead_data)
        if not is_valid:
            raise LeadValidationError(error)
        return lead_data


class FreshnessChecker:
    """
    Checks lead freshness based on timestamp.
    
    Freshness Categories:
    - Fresh: < 24 hours old (highest priority)
    - Warm: < 3 days old (medium priority)
    - Cold: < 7 days old (low priority)
    - Stale: >= 7 days old (DISCARDED)
    
    Example:
        checker = FreshnessChecker()
        freshness = checker.check_freshness(lead_timestamp)
        if freshness == LeadFreshness.STALE:
            discard_lead()
    """
    
    # Freshness thresholds
    FRESH_HOURS = 24      # < 24h = Fresh
    WARM_DAYS = 3         # < 3 days = Warm
    COLD_DAYS = 7         # < 7 days = Cold, >= 7 days = Stale (DISCARD)
    
    def __init__(self, reference_time: Optional[datetime] = None):
        """
        Initialize freshness checker.
        
        Args:
            reference_time: Time to compare against (default: now)
        """
        self.reference_time = reference_time or datetime.now(timezone.utc)
    
    def check_freshness(self, timestamp: Union[str, datetime]) -> LeadFreshness:
        """
        Check the freshness category of a lead.
        
        Args:
            timestamp: Lead timestamp (ISO string or datetime)
            
        Returns:
            LeadFreshness category
        """
        # Parse timestamp if string
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                logger.warning(f"[FreshnessChecker] Invalid timestamp format: {timestamp}")
                return LeadFreshness.STALE
        
        # Ensure both are timezone-aware
        if timestamp.tzinfo is None:
            timestamp = timestamp.replace(tzinfo=timezone.utc)
        if self.reference_time.tzinfo is None:
            self.reference_time = self.reference_time.replace(tzinfo=timezone.utc)
        
        # Calculate age
        age = self.reference_time - timestamp
        
        # Categorize
        if age < timedelta(hours=self.FRESH_HOURS):
            return LeadFreshness.FRESH
        elif age < timedelta(days=self.WARM_DAYS):
            return LeadFreshness.WARM
        elif age < timedelta(days=self.COLD_DAYS):
            return LeadFreshness.COLD
        else:
            return LeadFreshness.STALE
    
    def is_fresh_enough(self, timestamp: Union[str, datetime]) -> bool:
        """
        Check if lead is fresh enough to keep (< 7 days old).
        
        Args:
            timestamp: Lead timestamp
            
        Returns:
            True if lead should be kept, False if stale
        """
        freshness = self.check_freshness(timestamp)
        return freshness != LeadFreshness.STALE
    
    def get_freshness_with_metadata(self, timestamp: Union[str, datetime]) -> Dict[str, Any]:
        """
        Get freshness category with additional metadata.
        
        Returns:
            Dict with freshness, age_hours, age_days, is_acceptable
        """
        # Parse timestamp if string
        if isinstance(timestamp, str):
            try:
                parsed_ts = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except ValueError:
                return {
                    'freshness': LeadFreshness.STALE,
                    'age_hours': None,
                    'age_days': None,
                    'is_acceptable': False,
                    'error': 'Invalid timestamp'
                }
        else:
            parsed_ts = timestamp
        
        # Ensure timezone-aware
        if parsed_ts.tzinfo is None:
            parsed_ts = parsed_ts.replace(tzinfo=timezone.utc)
        if self.reference_time.tzinfo is None:
            reference = self.reference_time.replace(tzinfo=timezone.utc)
        else:
            reference = self.reference_time
        
        age = reference - parsed_ts
        freshness = self.check_freshness(parsed_ts)
        
        return {
            'freshness': freshness,
            'freshness_label': freshness.value,
            'age_hours': round(age.total_seconds() / 3600, 1),
            'age_days': round(age.total_seconds() / 86400, 1),
            'is_acceptable': freshness != LeadFreshness.STALE,
            'is_fresh': freshness == LeadFreshness.FRESH,
            'is_warm': freshness == LeadFreshness.WARM,
            'is_cold': freshness == LeadFreshness.COLD
        }
    
    @classmethod
    def validate_or_discard(cls, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Check lead freshness and return None if too old (stale).
        
        Args:
            lead_data: Lead dictionary with 'timestamp' field
            
        Returns:
            Lead data if fresh, None if stale
        """
        timestamp = lead_data.get('timestamp')
        if not timestamp:
            logger.warning("[FreshnessChecker] ❌ Lead discarded: No timestamp")
            return None
        
        checker = cls()
        freshness = checker.check_freshness(timestamp)
        
        if freshness == LeadFreshness.STALE:
            metadata = checker.get_freshness_with_metadata(timestamp)
            logger.warning(
                f"[FreshnessChecker] ❌ Lead discarded: Too old ({metadata['age_days']} days)"
            )
            return None
        
        # Add freshness info to lead
        metadata = checker.get_freshness_with_metadata(timestamp)
        lead_data['_freshness'] = metadata
        
        logger.info(
            f"[FreshnessChecker] ✅ Lead freshness: {freshness.value} "
            f"({metadata['age_hours']}h old)"
        )
        
        return lead_data


# ═══════════════════════════════════════════════════════════════════════════════
# Combined Validation (Mandatory Fields + Freshness)
# ═══════════════════════════════════════════════════════════════════════════════

class LeadQualificationValidator:
    """
    Combined validator that checks both mandatory fields AND freshness.
    
    A lead must pass BOTH checks to be accepted:
    1. Have all 5 mandatory fields (text, phone, source, url, timestamp)
    2. Be less than 7 days old (not stale)
    """
    
    @classmethod
    def validate(cls, lead_data: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Full validation: mandatory fields + freshness.
        
        Returns:
            (is_valid, error_message)
        """
        # Step 1: Check mandatory fields
        is_valid, error = LeadValidator.validate(lead_data)
        if not is_valid:
            return False, error
        
        # Step 2: Check freshness
        timestamp = lead_data.get('timestamp')
        if not timestamp:
            return False, "Missing timestamp for freshness check"
        
        checker = FreshnessChecker()
        freshness = checker.check_freshness(timestamp)
        
        if freshness == LeadFreshness.STALE:
            metadata = checker.get_freshness_with_metadata(timestamp)
            return False, f"Lead too old: {metadata['age_days']} days (max 7 days)"
        
        return True, None
    
    @classmethod
    def validate_or_discard(cls, lead_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Full validation - returns None if lead fails any check.
        
        Returns:
            Lead with freshness metadata if valid, None if rejected
        """
        is_valid, error = cls.validate(lead_data)
        if not is_valid:
            logger.warning(f"[LeadQualification] ❌ Lead discarded: {error}")
            return None
        
        # Add freshness metadata
        checker = FreshnessChecker()
        metadata = checker.get_freshness_with_metadata(lead_data.get('timestamp'))
        lead_data['_freshness'] = metadata
        
        logger.info(
            f"[LeadQualification] ✅ Lead qualified: "
            f"freshness={metadata['freshness_label']}, "
            f"age={metadata['age_hours']}h"
        )
        
        return lead_data


# Convenience function for quick validation
def validate_lead(lead_data: Dict[str, Any]) -> bool:
    """
    Quick check if a lead has all mandatory fields.
    
    Args:
        lead_data: Dictionary containing lead data
        
    Returns:
        True if valid, False otherwise
    """
    is_valid, _ = LeadValidator.validate(lead_data)
    return is_valid


def filter_valid_leads(leads: list) -> list:
    """
    Filter a list of leads, keeping only valid ones.
    
    Args:
        leads: List of lead dictionaries
        
    Returns:
        List of valid leads only
    """
    valid, _ = LeadValidator.validate_list(leads)
    return valid


def check_lead_freshness(timestamp: Union[str, datetime]) -> LeadFreshness:
    """
    Quick freshness check for a timestamp.
    
    Args:
        timestamp: Lead timestamp
        
    Returns:
        LeadFreshness category
    """
    checker = FreshnessChecker()
    return checker.check_freshness(timestamp)
