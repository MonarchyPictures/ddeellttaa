"""
Lead Enrichment Service
Turns raw signals into sales-ready leads

Combines:
- Scraping
- APIs (email finder, company data)
- AI detection
- Enrichment (LinkedIn, location, company)

Example raw lead → enriched lead:
  username: "john_buyer"
  text: "Looking for CRM"
  ↓ ENRICHMENT ↓
  name: "John Smith"
  email: "john@abcplumbing.com"
  company: "ABC Plumbing"
  title: "Owner"
  location: "Chicago, IL"
  linkedin: "linkedin.com/in/johnsmith"
  phone: "+1-555-123-4567"
  company_size: "10-50"
  industry: "Construction"
"""
import os
import re
import json
from typing import Dict, Optional, List
from dataclasses import dataclass
from datetime import datetime

import httpx


@dataclass
class EnrichedLead:
    """Fully enriched lead ready for sales"""
    # Identity
    name: Optional[str]
    first_name: Optional[str]
    last_name: Optional[str]
    username: str
    
    # Contact
    email: Optional[str]
    phone: Optional[str]
    
    # Company
    company: Optional[str]
    title: Optional[str]
    company_size: Optional[str]
    industry: Optional[str]
    company_website: Optional[str]
    
    # Location
    location: Optional[str]
    city: Optional[str]
    state: Optional[str]
    country: Optional[str]
    
    # Social
    linkedin_url: Optional[str]
    twitter_url: Optional[str]
    
    # Intent (from original signal)
    intent_text: str
    intent_score: float
    buying_urgency: str
    
    # Enrichment metadata
    enrichment_sources: List[str]
    enrichment_confidence: float
    enriched_at: str


class EmailFinderService:
    """
    Find email addresses using multiple strategies:
    1. Pattern guessing (firstname@company.com)
    2. Hunter.io API
    3. Clearbit API
    4. Signal text extraction
    """
    
    def __init__(self):
        self.hunter_api_key = os.getenv("HUNTER_API_KEY")
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def find_email(
        self,
        name: str,
        company_domain: str,
        signal_text: str = ""
    ) -> Optional[Dict]:
        """
        Find email using all available methods
        
        Returns:
            {
                "email": "john@company.com",
                "confidence": 85,
                "source": "hunter",
                "type": "work"
            }
        """
        # Method 1: Extract from signal text
        email = self._extract_from_text(signal_text)
        if email:
            return {
                "email": email,
                "confidence": 100,
                "source": "signal_text",
                "type": "unknown"
            }
        
        # Method 2: Hunter.io
        if self.hunter_api_key and company_domain:
            hunter_result = await self._hunter_lookup(name, company_domain)
            if hunter_result:
                return hunter_result
        
        # Method 3: Pattern guessing
        if name and company_domain:
            guessed = self._pattern_guess(name, company_domain)
            if guessed:
                return guessed
        
        return None
    
    def _extract_from_text(self, text: str) -> Optional[str]:
        """Extract email from signal text"""
        pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        match = re.search(pattern, text)
        return match.group(0) if match else None
    
    async def _hunter_lookup(self, name: str, domain: str) -> Optional[Dict]:
        """Lookup email via Hunter.io"""
        try:
            url = f"https://api.hunter.io/v2/email-finder"
            params = {
                "domain": domain,
                "first_name": name.split()[0] if name else "",
                "last_name": name.split()[-1] if name and len(name.split()) > 1 else "",
                "api_key": self.hunter_api_key,
            }
            
            response = await self.client.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("data", {}).get("email"):
                    return {
                        "email": data["data"]["email"],
                        "confidence": data["data"].get("score", 50),
                        "source": "hunter",
                        "type": "work"
                    }
        except Exception as e:
            print(f"[EmailFinder] Hunter error: {e}")
        
        return None
    
    def _pattern_guess(self, name: str, domain: str) -> Optional[Dict]:
        """Guess email using common patterns"""
        if not name or not domain:
            return None
        
        parts = name.lower().split()
        if len(parts) < 1:
            return None
        
        first = parts[0]
        last = parts[-1] if len(parts) > 1 else ""
        
        patterns = [
            f"{first}@{domain}",
            f"{first}.{last}@{domain}" if last else None,
            f"{first[0]}{last}@{domain}" if last else None,
            f"{first}_{last}@{domain}" if last else None,
        ]
        
        # Return first non-null pattern with low confidence
        for pattern in patterns:
            if pattern:
                return {
                    "email": pattern,
                    "confidence": 30,  # Low confidence for guesses
                    "source": "pattern_guess",
                    "type": "work"
                }
        
        return None
    
    async def close(self):
        await self.client.aclose()


class CompanyEnrichmentService:
    """
    Enrich company data using APIs:
    - Clearbit
    - ZoomInfo
    - LinkedIn Sales Navigator
    """
    
    def __init__(self):
        self.clearbit_api_key = os.getenv("CLEARBIT_API_KEY")
        self.zoominfo_api_key = os.getenv("ZOOMINFO_API_KEY")
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def enrich_company(self, company_name: str, website: Optional[str] = None) -> Optional[Dict]:
        """
        Enrich company data
        
        Returns:
            {
                "name": "ABC Plumbing",
                "domain": "abcplumbing.com",
                "industry": "Construction",
                "size": "10-50",
                "location": "Chicago, IL",
                "linkedin": "linkedin.com/company/abc-plumbing",
                "revenue": "$5M-$10M",
            }
        """
        # Try Clearbit first
        if website and self.clearbit_api_key:
            clearbit_data = await self._clearbit_company(website)
            if clearbit_data:
                return clearbit_data
        
        # Fallback: pattern matching / local DB
        return self._local_company_lookup(company_name)
    
    async def _clearbit_company(self, domain: str) -> Optional[Dict]:
        """Lookup company via Clearbit"""
        try:
            url = f"https://company.clearbit.com/v2/companies/find"
            headers = {"Authorization": f"Bearer {self.clearbit_api_key}"}
            params = {"domain": domain}
            
            response = await self.client.get(url, headers=headers, params=params)
            if response.status_code == 200:
                data = response.json()
                return {
                    "name": data.get("name"),
                    "domain": data.get("domain"),
                    "industry": data.get("category", {}).get("industry"),
                    "size": data.get("metrics", {}).get("employeesRange"),
                    "location": f"{data.get('geo', {}).get('city', '')}, {data.get('geo', {}).get('state', '')}",
                    "linkedin": data.get("linkedin", {}).get("handle"),
                    "revenue": data.get("metrics", {}).get("estimatedAnnualRevenue"),
                    "source": "clearbit",
                }
        except Exception as e:
            print(f"[CompanyEnrichment] Clearbit error: {e}")
        
        return None
    
    def _local_company_lookup(self, company_name: str) -> Optional[Dict]:
        """Fallback: infer from company name patterns"""
        # This would typically query your company database
        # For now, return basic structure
        return {
            "name": company_name,
            "domain": None,
            "industry": "Unknown",
            "size": "Unknown",
            "location": None,
            "source": "inferred",
        }
    
    async def close(self):
        await self.client.aclose()


class LinkedInEnrichmentService:
    """
    Find LinkedIn profiles from username/name
    """
    
    def __init__(self):
        self.client = httpx.AsyncClient(timeout=10.0)
    
    async def find_linkedin(
        self,
        name: Optional[str] = None,
        username: Optional[str] = None,
        company: Optional[str] = None,
        location: Optional[str] = None
    ) -> Optional[Dict]:
        """
        Find LinkedIn profile URL
        
        Returns:
            {
                "url": "linkedin.com/in/john-smith-123",
                "title": "Owner at ABC Plumbing",
                "company": "ABC Plumbing",
                "location": "Chicago, IL",
                "connections": 500,
            }
        """
        # Try LinkedIn Sales Navigator API if available
        # For now, construct URL from name
        
        if name:
            # Construct likely LinkedIn URL
            linkedin_slug = name.lower().replace(" ", "-")
            return {
                "url": f"https://linkedin.com/in/{linkedin_slug}",
                "confidence": 50,
                "source": "pattern_match",
            }
        
        if username:
            return {
                "url": f"https://linkedin.com/in/{username}",
                "confidence": 30,
                "source": "username_guess",
            }
        
        return None
    
    async def close(self):
        await self.client.aclose()


class LeadEnrichmentService:
    """
    Main enrichment orchestrator
    
    Takes a raw lead and enriches it with all available data sources
    """
    
    def __init__(self):
        self.email_finder = EmailFinderService()
        self.company_enrichment = CompanyEnrichmentService()
        self.linkedin_enrichment = LinkedInEnrichmentService()
    
    async def enrich(
        self,
        lead_data: Dict,
        signal_text: str
    ) -> EnrichedLead:
        """
        Enrich a lead with all available data
        
        Args:
            lead_data: Raw lead from database
            signal_text: Original signal text
            
        Returns:
            EnrichedLead with full contact/company data
        """
        username = lead_data.get("username", "")
        company_hint = lead_data.get("company") or self._extract_company(signal_text)
        location_hint = lead_data.get("location") or self._extract_location(signal_text)
        
        # Extract name from signal text
        name = self._extract_name(signal_text) or username
        
        # Build company domain
        company_domain = None
        if company_hint:
            company_domain = self._guess_domain(company_hint)
        
        # 1. Find email
        email_result = await self.email_finder.find_email(
            name=name,
            company_domain=company_domain,
            signal_text=signal_text
        )
        
        # 2. Enrich company
        company_result = await self.company_enrichment.enrich_company(
            company_name=company_hint or "",
            website=company_domain
        ) if company_hint else None
        
        # 3. Find LinkedIn
        linkedin_result = await self.linkedin_enrichment.find_linkedin(
            name=name,
            username=username,
            company=company_hint,
            location=location_hint
        )
        
        # 4. Extract phone
        phone = self._extract_phone(signal_text)
        
        # Build enriched lead
        enrichment_sources = []
        if email_result:
            enrichment_sources.append(f"email:{email_result['source']}")
        if company_result:
            enrichment_sources.append(f"company:{company_result.get('source', 'unknown')}")
        if linkedin_result:
            enrichment_sources.append(f"linkedin:{linkedin_result.get('source', 'unknown')}")
        
        # Calculate confidence
        confidence_scores = []
        if email_result:
            confidence_scores.append(email_result.get("confidence", 0))
        if company_result and company_result.get("source") != "inferred":
            confidence_scores.append(80)
        if linkedin_result:
            confidence_scores.append(linkedin_result.get("confidence", 0))
        
        avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 50
        
        # Split name
        first_name, last_name = self._split_name(name)
        
        return EnrichedLead(
            name=name,
            first_name=first_name,
            last_name=last_name,
            username=username,
            email=email_result.get("email") if email_result else None,
            phone=phone,
            company=company_result.get("name") if company_result else company_hint,
            title=lead_data.get("job_title"),
            company_size=company_result.get("size") if company_result else None,
            industry=company_result.get("industry") if company_result else None,
            company_website=company_domain,
            location=location_hint,
            city=None,  # Could geocode
            state=None,
            country=lead_data.get("country", "Kenya"),
            linkedin_url=linkedin_result.get("url") if linkedin_result else None,
            twitter_url=f"https://twitter.com/{username}" if username else None,
            intent_text=signal_text[:300],
            intent_score=lead_data.get("intent_score", 0),
            buying_urgency=lead_data.get("buying_urgency", "unknown"),
            enrichment_sources=enrichment_sources,
            enrichment_confidence=avg_confidence / 100,
            enriched_at=datetime.utcnow().isoformat()
        )
    
    def _extract_name(self, text: str) -> Optional[str]:
        """Extract name from text patterns"""
        patterns = [
            r"(?:i am|i'm|my name is)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)",
            r"(?:from)\s+([A-Z][a-z]+(?:\s[A-Z][a-z]+)?)\s+(?:at|@)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_company(self, text: str) -> Optional[str]:
        """Extract company from text"""
        patterns = [
            r"(?:at|from)\s+([A-Z][\w\s&]+(?:Ltd|Limited|Inc|Corp|LLC)?)",
            r"(?:work(?:s|ing)?\s+(?:at|for))\s+([A-Z][\w\s&]+)",
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1).strip()
        
        return None
    
    def _extract_location(self, text: str) -> Optional[str]:
        """Extract location from text"""
        # Cities in Kenya/Nairobi focus
        cities = ["Nairobi", "Mombasa", "Kisumu", "Nakuru", "Eldoret"]
        text_lower = text.lower()
        
        for city in cities:
            if city.lower() in text_lower:
                return city
        
        return None
    
    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone from text"""
        patterns = [
            r'\+?\d{1,3}[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}',
            r'\+254[\s-]?\d{9}',
            r'0\d{9}',
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(0)
        
        return None
    
    def _guess_domain(self, company_name: str) -> Optional[str]:
        """Guess company domain from name"""
        # Simple guess - real implementation would use company DB
        cleaned = company_name.lower().replace(" ", "").replace("&", "and")
        return f"{cleaned}.com"
    
    def _split_name(self, name: Optional[str]) -> tuple:
        """Split full name into first/last"""
        if not name:
            return None, None
        
        parts = name.split()
        if len(parts) == 1:
            return parts[0], None
        return parts[0], parts[-1]
    
    async def close(self):
        await self.email_finder.close()
        await self.company_enrichment.close()
        await self.linkedin_enrichment.close()


# Singleton
_enrichment_service = None


def get_enrichment_service() -> LeadEnrichmentService:
    """Get or create enrichment service"""
    global _enrichment_service
    if _enrichment_service is None:
        _enrichment_service = LeadEnrichmentService()
    return _enrichment_service
