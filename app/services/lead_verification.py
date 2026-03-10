"""
Lead Verification Service
Validates and enriches lead data from multiple signals
"""
import re
from typing import List, Dict, Optional, Any
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VerifiedLead:
    """Verified lead data structure"""
    name: Optional[str]
    username: str
    email: Optional[str]
    phone: Optional[str]
    company: Optional[str]
    location: Optional[str]
    profile_urls: Dict[str, str]
    intent_signals: List[str]
    verification_score: float


class LeadVerificationService:
    """
    Verifies leads by:
    1. Cross-referencing multiple signals
    2. Extracting contact info
    3. Validating data quality
    4. Calculating verification score
    """
    
    # Email extraction patterns
    EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')
    
    # Phone patterns (international)
    PHONE_PATTERNS = [
        re.compile(r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),  # US/Intl
        re.compile(r'\+254[\s-]?\d{9}'),  # Kenya
        re.compile(r'0\d{9}'),  # Kenya local
    ]
    
    # Social media username patterns
    USERNAME_PATTERNS = {
        "reddit": re.compile(r'/?u/(\w+)'),
        "twitter": re.compile(r'@(\w+)'),
        "linkedin": re.compile(r'linkedin\.com/in/(\w+)'),
    }
    
    def __init__(self):
        pass
    
    def verify_and_create(self, signals: List[Dict]) -> Optional[VerifiedLead]:
        """
        Verify signals and create a lead.
        
        Args:
            signals: List of signal dictionaries from scrapers
            
        Returns:
            VerifiedLead if valid, None if not enough data
        """
        if not signals:
            return None
        
        # Aggregate data from all signals
        usernames = []
        emails = []
        phones = []
        locations = []
        companies = []
        profile_urls = {}
        intent_signals = []
        
        for signal in signals:
            content = signal.get("content", "") + " " + signal.get("title", "")
            author = signal.get("author", "")
            source = signal.get("source", "")
            
            # Extract username
            if author:
                usernames.append(author)
                profile_urls[source] = signal.get("source_url", "")
            
            # Extract email
            email = self._extract_email(content)
            if email:
                emails.append(email)
            
            # Extract phone
            phone = self._extract_phone(content)
            if phone:
                phones.append(phone)
            
            # Extract location
            location = self._extract_location(content)
            if location:
                locations.append(location)
            
            # Extract company mention
            company = self._extract_company(content)
            if company:
                companies.append(company)
            
            # Collect intent signals
            intent_signals.append(content[:200])  # First 200 chars
        
        # Need at least a username to be a valid lead
        if not usernames:
            return None
        
        # Calculate verification score
        score = self._calculate_verification_score(
            len(signals),
            len(emails),
            len(phones),
            len(locations),
            len(set(usernames))
        )
        
        # Only return if meets minimum threshold
        if score < 0.3:
            return None
        
        return VerifiedLead(
            name=self._extract_name(signals[0].get("content", "")) if signals else None,
            username=usernames[0],
            email=emails[0] if emails else None,
            phone=phones[0] if phones else None,
            company=companies[0] if companies else None,
            location=locations[0] if locations else None,
            profile_urls=profile_urls,
            intent_signals=intent_signals[:5],  # Top 5
            verification_score=round(score, 3)
        )
    
    def _extract_email(self, text: str) -> Optional[str]:
        """Extract email from text"""
        match = self.EMAIL_PATTERN.search(text)
        return match.group(0) if match else None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number from text"""
        for pattern in self.PHONE_PATTERNS:
            match = pattern.search(text)
            if match:
                return match.group(0)
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location mentions from text"""
        # Common location patterns
        location_patterns = [
            r'in\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s*(Kenya|Nairobi|Mombasa|Kisumu)',
            r'located\s+in\s+([A-Z][a-z]+)',
            r'from\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)',
        ]
        
        for pattern in location_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        # Check for city names
        cities = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]
        for city in cities:
            if city.lower() in text.lower():
                return city
        
        return None
    
    def _extract_company(self, text: str) -> Optional[str]:
        """Extract company name from text"""
        # Patterns like "at Company Name" or "Company: XYZ"
        patterns = [
            r'at\s+([A-Z][\w\s&]+(?:Ltd|Limited|Inc|Corp|Company)?)',
            r'work(?:s|ing)?\s+(?:at|for)\s+([A-Z][\w\s&]+)',
            r'company[:\s]+([A-Z][\w\s&]+)',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Try to extract a person's name"""
        # Look for "I'm [Name]" or "My name is [Name]"
        patterns = [
            r"(?:i am|i'm|my name is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _calculate_verification_score(
        self,
        signal_count: int,
        email_count: int,
        phone_count: int,
        location_count: int,
        unique_usernames: int
    ) -> float:
        """Calculate verification score based on available data"""
        score = 0.0
        
        # Multiple signals = more reliable
        score += min(signal_count * 0.15, 0.4)
        
        # Contact info is valuable
        if email_count > 0:
            score += 0.25
        if phone_count > 0:
            score += 0.25
        
        # Location adds credibility
        if location_count > 0:
            score += 0.1
        
        # Consistent identity across platforms
        if unique_usernames == 1:
            score += 0.15  # Same user across sources
        
        return min(score, 1.0)
    
    def deduplicate_signals(self, signals: List[Dict]) -> List[Dict]:
        """Remove duplicate signals by external_id"""
        seen = set()
        unique = []
        
        for signal in signals:
            ext_id = signal.get("external_id")
            if ext_id and ext_id not in seen:
                seen.add(ext_id)
                unique.append(signal)
            elif not ext_id:
                unique.append(signal)
        
        return unique


# Singleton
_verification_service = None


def get_verification_service() -> LeadVerificationService:
    """Get or create the verification service"""
    global _verification_service
    if _verification_service is None:
        _verification_service = LeadVerificationService()
    return _verification_service
