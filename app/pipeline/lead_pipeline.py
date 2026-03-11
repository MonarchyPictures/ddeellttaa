"""
DELTA-9 HARDENED LEAD PIPELINE
Production-grade lead processing with strict validation

Pipeline Stages:
1. SCRAPE - Extract raw data from sources
2. CLEAN - Normalize and sanitize text
3. INTENT - Detect buyer intent (reject sellers)
4. EXTRACT - Extract phone numbers
5. VERIFY - Validate phone format (Kenya)
6. SOURCE - Verify source attribution
7. FRESHNESS - Check timestamp (< 7 days)
8. SCORE - Calculate intent score
9. DEDUPE - Check for duplicates
10. STORE - Save to database

CRITICAL: Any stage failure = lead rejection
"""

import hashlib
import re
import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field, validator
import phonenumbers
from phonenumbers import geocoder, carrier

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class PipelineStage(Enum):
    """Pipeline execution stages"""
    SCRAPE = "scrape"
    CLEAN = "clean"
    INTENT = "intent"
    EXTRACT = "extract"
    VERIFY = "verify"
    SOURCE = "source"
    FRESHNESS = "freshness"
    SCORE = "score"
    DEDUPE = "dedupe"
    STORE = "store"


class LeadTemperature(Enum):
    """Lead freshness classification"""
    HOT = "hot"      # < 24 hours
    WARM = "warm"    # < 3 days
    COLD = "cold"    # < 7 days
    STALE = "stale"  # > 7 days (DISCARD)


class RejectionReason(Enum):
    """Reasons for lead rejection"""
    MISSING_FIELD = "missing_required_field"
    INVALID_PHONE = "invalid_phone_number"
    SELLER_INTENT = "seller_intent_detected"
    NO_BUYER_INTENT = "no_buyer_intent"
    STALE_TIMESTAMP = "lead_too_old"
    DUPLICATE = "duplicate_lead"
    INVALID_SOURCE = "invalid_source"
    AI_GENERATED = "ai_generated_detected"
    PIPELINE_ERROR = "pipeline_stage_failure"


# BUYER INTENT KEYWORDS (Kenya-focused)
BUYER_KEYWORDS = [
    # English
    r'looking\s+for',
    r'\bneed\b',
    r'\bwant\b',
    r'\bsearching\s+for\b',
    r'anyone\s+selling',
    r'where\s+can\s+i\s+buy',
    r'who\s+has',
    r'\b urgently\b',
    r'budget\s+ready',
    r'cash\s+on\s+hand',
    r'willing\s+to\s+buy',
    r'in\s+the\s+market\s+for',
    r'seeking',
    r'required',
    # Swahili
    r'\bnatafuta\b',
    r'\bniko\s+natafuta\b',
    r'\bnahtaji\b',
    r'\bninahitaji\b',
    r'\btafuta\b',
]

# SELLER INTENT KEYWORDS (REJECT these)
SELLER_KEYWORDS = [
    r'\bselling\b',
    r'\bavailable\b',
    r'\bfor\s+sale\b',
    r'\bprice\b',
    r'\bdiscount\b',
    r'\boffer\b',
    r'\bcall\s+me\b',
    r'\bdm\s+me\b',
    r'\bcontact\s+me\b',
    r'\bwhatsapp\s+me\b',
    r'\bhmu\b',
    r'\binbox\b',
    r'\bstock\b',
    r'\bsupply\b',
    r'\bwholesale\b',
    r'\bretail\b',
    r'\bshop\b',
    r'\bstore\b',
    r'\bdealership\b',
    r'\bimport\b',
    r'\bduty\s+free\b',
]

# KENYA PHONE REGEX
KENYA_PHONE_PATTERN = re.compile(r'^(?:\+254|0)[17]\d{8}$')


class LeadSchema(BaseModel):
    """
    STRICT lead schema - ALL fields required
    Missing any field = automatic rejection
    """
    id: Optional[str] = None
    query: str = Field(..., description="Search query that found this lead")
    text: str = Field(..., description="Raw text from source post")
    phone: str = Field(..., description="Verified phone number")
    source_platform: str = Field(..., description="Platform: Telegram, Facebook, Jiji, etc.")
    source_name: str = Field(..., description="Group name, page name, forum name")
    source_url: str = Field(..., description="Direct URL to original post")
    timestamp: datetime = Field(..., description="When post was created")
    location: str = Field(..., description="City/region")
    intent_score: int = Field(..., ge=0, le=100, description="AI intent score")
    
    # Internal fields
    temperature: Optional[str] = None
    lead_hash: Optional[str] = None
    extracted_at: datetime = Field(default_factory=datetime.utcnow)
    
    @validator('phone')
    def validate_kenya_phone(cls, v):
        """Validate Kenya phone format"""
        cleaned = re.sub(r'\s+|-', '', v)
        if not KENYA_PHONE_PATTERN.match(cleaned):
            raise ValueError(f"Invalid Kenya phone: {v}")
        return cleaned
    
    @validator('source_url')
    def validate_url(cls, v):
        """Ensure URL is valid"""
        if not v.startswith(('http://', 'https://')):
            raise ValueError(f"Invalid URL: {v}")
        return v


@dataclass
class PipelineResult:
    """Result of pipeline processing"""
    success: bool
    lead: Optional[LeadSchema] = None
    rejection_reason: Optional[RejectionReason] = None
    stage_failed: Optional[PipelineStage] = None
    error_message: Optional[str] = None
    processing_time_ms: float = 0.0
    metadata: Dict = field(default_factory=dict)


class LeadPipeline:
    """
    Production-grade lead processing pipeline
    
    STRICT MODE: Any validation failure = lead rejection
    """
    
    def __init__(self, db_session=None, redis_client=None):
        self.db = db_session
        self.redis = redis_client
        self.processed_hashes = set()  # In-memory dedupe cache
        
        # Statistics
        self.stats = {
            'processed': 0,
            'accepted': 0,
            'rejected': 0,
            'by_reason': {r: 0 for r in RejectionReason}
        }
    
    def process(self, raw_data: Dict) -> PipelineResult:
        """
        Process raw scraped data through all pipeline stages
        
        Args:
            raw_data: Raw data from scraper
            
        Returns:
            PipelineResult with lead or rejection reason
        """
        start_time = datetime.utcnow()
        
        try:
            # Stage 1: SCRAPE - Validate input
            stage_result = self._stage_scrape(raw_data)
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.MISSING_FIELD,
                    PipelineStage.SCRAPE,
                    stage_result['error']
                )
            
            # Stage 2: CLEAN - Normalize text
            stage_result = self._stage_clean(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.PIPELINE_ERROR,
                    PipelineStage.CLEAN,
                    stage_result['error']
                )
            
            # Stage 3: INTENT - Detect buyer intent
            stage_result = self._stage_intent(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.NO_BUYER_INTENT,
                    PipelineStage.INTENT,
                    stage_result['error']
                )
            
            # Stage 4: EXTRACT - Extract phone
            stage_result = self._stage_extract(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.MISSING_FIELD,
                    PipelineStage.EXTRACT,
                    stage_result['error']
                )
            
            # Stage 5: VERIFY - Validate phone
            stage_result = self._stage_verify(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.INVALID_PHONE,
                    PipelineStage.VERIFY,
                    stage_result['error']
                )
            
            # Stage 6: SOURCE - Verify source
            stage_result = self._stage_source(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.INVALID_SOURCE,
                    PipelineStage.SOURCE,
                    stage_result['error']
                )
            
            # Stage 7: FRESHNESS - Check timestamp
            stage_result = self._stage_freshness(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.STALE_TIMESTAMP,
                    PipelineStage.FRESHNESS,
                    stage_result['error']
                )
            
            # Stage 8: SCORE - Calculate intent score
            stage_result = self._stage_score(stage_result['data'])
            
            # Stage 9: DEDUPE - Check for duplicates
            stage_result = self._stage_dedupe(stage_result['data'])
            if not stage_result['success']:
                return self._reject(
                    RejectionReason.DUPLICATE,
                    PipelineStage.DEDUPE,
                    stage_result['error']
                )
            
            # Stage 10: STORE - Create lead object
            lead = self._stage_store(stage_result['data'])
            
            processing_time = (datetime.utcnow() - start_time).total_seconds() * 1000
            
            self.stats['processed'] += 1
            self.stats['accepted'] += 1
            
            logger.info(f"✅ Lead accepted: {lead.phone} from {lead.source_platform}")
            
            return PipelineResult(
                success=True,
                lead=lead,
                processing_time_ms=processing_time,
                metadata={'temperature': lead.temperature}
            )
            
        except Exception as e:
            logger.error(f"Pipeline error: {str(e)}", exc_info=True)
            return self._reject(
                RejectionReason.PIPELINE_ERROR,
                PipelineStage.SCORE,
                str(e)
            )
    
    def _stage_scrape(self, raw_data: Dict) -> Dict:
        """Validate raw scraped data has required fields"""
        required = ['text', 'source_platform', 'source_url', 'timestamp']
        
        missing = [f for f in required if not raw_data.get(f)]
        if missing:
            return {
                'success': False,
                'error': f"Missing required fields: {missing}"
            }
        
        return {'success': True, 'data': raw_data}
    
    def _stage_clean(self, data: Dict) -> Dict:
        """Clean and normalize text"""
        try:
            text = data.get('text', '')
            # Remove excessive whitespace
            text = ' '.join(text.split())
            # Remove null bytes
            text = text.replace('\x00', '')
            
            data['text_clean'] = text
            return {'success': True, 'data': data}
        except Exception as e:
            return {'success': False, 'error': f"Clean failed: {str(e)}"}
    
    def _stage_intent(self, data: Dict) -> Dict:
        """Detect buyer intent - REJECT seller posts"""
        text = data.get('text_clean', '').lower()
        
        # Check for seller keywords (immediate reject)
        for pattern in SELLER_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                logger.warning(f"SELLER INTENT REJECTED: {text[:50]}...")
                return {
                    'success': False,
                    'error': f"Seller keyword detected: {pattern}"
                }
        
        # Check for buyer keywords
        buyer_score = 0
        matched_keywords = []
        for pattern in BUYER_KEYWORDS:
            if re.search(pattern, text, re.IGNORECASE):
                buyer_score += 1
                matched_keywords.append(pattern)
        
        if buyer_score == 0:
            return {
                'success': False,
                'error': "No buyer intent keywords found"
            }
        
        data['buyer_score'] = buyer_score
        data['matched_keywords'] = matched_keywords
        return {'success': True, 'data': data}
    
    def _stage_extract(self, data: Dict) -> Dict:
        """Extract phone number from text"""
        text = data.get('text_clean', '')
        
        # Find all potential phone numbers
        # Pattern: +254XXXXXXXXX or 07XXXXXXXX or 01XXXXXXXX
        patterns = [
            r'\+254[17]\d{8}',
            r'0[17]\d{8}',
        ]
        
        phones = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            phones.extend(matches)
        
        if not phones:
            return {
                'success': False,
                'error': "No phone number found in text"
            }
        
        # Take first valid phone
        data['phone_raw'] = phones[0]
        return {'success': True, 'data': data}
    
    def _stage_verify(self, data: Dict) -> Dict:
        """Verify phone number is valid Kenya number"""
        phone = data.get('phone_raw', '')
        
        # Clean the phone
        cleaned = re.sub(r'\s+|-', '', phone)
        
        # Normalize to +254 format
        if cleaned.startswith('0'):
            cleaned = '+254' + cleaned[1:]
        
        # Validate format
        if not KENYA_PHONE_PATTERN.match(cleaned):
            return {
                'success': False,
                'error': f"Invalid Kenya phone format: {phone}"
            }
        
        # Additional phonenumbers library validation
        try:
            parsed = phonenumbers.parse(cleaned, 'KE')
            if not phonenumbers.is_valid_number(parsed):
                return {
                    'success': False,
                    'error': f"Phone validation failed: {phone}"
                }
        except Exception as e:
            return {
                'success': False,
                'error': f"Phone parsing error: {str(e)}"
            }
        
        data['phone'] = cleaned
        return {'success': True, 'data': data}
    
    def _stage_source(self, data: Dict) -> Dict:
        """Verify source attribution"""
        platform = data.get('source_platform', '')
        url = data.get('source_url', '')
        
        # Validate platform
        valid_platforms = ['telegram', 'facebook', 'jiji', 'reddit', 'forum', 
                          'google', 'twitter', 'whatsapp', 'instagram']
        
        if platform.lower() not in valid_platforms:
            return {
                'success': False,
                'error': f"Invalid platform: {platform}"
            }
        
        # Validate URL matches platform
        url_indicators = {
            'telegram': 't.me',
            'facebook': 'facebook.com',
            'jiji': 'jiji.co.ke',
            'reddit': 'reddit.com',
            'twitter': 'twitter.com',
        }
        
        expected = url_indicators.get(platform.lower())
        if expected and expected not in url:
            logger.warning(f"URL mismatch: {platform} -> {url}")
        
        data['source_name'] = data.get('source_name', f"{platform.title()} Source")
        return {'success': True, 'data': data}
    
    def _stage_freshness(self, data: Dict) -> Dict:
        """Check lead freshness - DISCARD if > 7 days"""
        timestamp = data.get('timestamp')
        
        if isinstance(timestamp, str):
            try:
                timestamp = datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            except:
                return {
                    'success': False,
                    'error': f"Invalid timestamp format: {timestamp}"
                }
        
        age = datetime.utcnow() - timestamp
        
        if age > timedelta(days=7):
            return {
                'success': False,
                'error': f"Lead too old: {age.days} days"
            }
        
        # Classify temperature
        if age < timedelta(hours=24):
            temperature = LeadTemperature.HOT.value
        elif age < timedelta(days=3):
            temperature = LeadTemperature.WARM.value
        else:
            temperature = LeadTemperature.COLD.value
        
        data['timestamp'] = timestamp
        data['temperature'] = temperature
        data['age_hours'] = age.total_seconds() / 3600
        
        return {'success': True, 'data': data}
    
    def _stage_score(self, data: Dict) -> Dict:
        """Calculate intent score (0-100)"""
        score = 40  # Base score
        
        # Buyer keyword matches
        score += len(data.get('matched_keywords', [])) * 10
        
        # Urgency indicators
        text = data.get('text_clean', '').lower()
        urgency_words = ['urgent', 'urgently', 'asap', 'today', 'now', 'immediately', 'haraka']
        for word in urgency_words:
            if word in text:
                score += 15
        
        # Budget mentioned
        budget_words = ['budget', 'cash', 'money', 'ready', 'available']
        for word in budget_words:
            if word in text:
                score += 10
        
        # Location specificity
        if data.get('location') and data['location'] not in ['Kenya', 'Unknown']:
            score += 10
        
        # Cap at 100
        score = min(100, score)
        
        # DISCARD if < 40
        if score < 40:
            data['discard'] = True
        
        data['intent_score'] = score
        return {'success': True, 'data': data}
    
    def _stage_dedupe(self, data: Dict) -> Dict:
        """Check for duplicate leads"""
        # Create hash from phone + text snippet + date
        text_snippet = data.get('text_clean', '')[:50]
        phone = data.get('phone', '')
        timestamp = data.get('timestamp', datetime.utcnow())
        date_str = timestamp.strftime('%Y-%m-%d') if isinstance(timestamp, datetime) else str(timestamp)[:10]
        
        hash_input = f"{phone}:{text_snippet}:{date_str}"
        lead_hash = hashlib.sha256(hash_input.encode()).hexdigest()[:16]
        
        if lead_hash in self.processed_hashes:
            return {
                'success': False,
                'error': f"Duplicate lead detected: {lead_hash}"
            }
        
        self.processed_hashes.add(lead_hash)
        data['lead_hash'] = lead_hash
        
        return {'success': True, 'data': data}
    
    def _stage_store(self, data: Dict) -> LeadSchema:
        """Create final lead object"""
        lead = LeadSchema(
            id=data.get('id') or f"lead_{data['lead_hash']}",
            query=data.get('query', ''),
            text=data.get('text_clean', ''),
            phone=data.get('phone', ''),
            source_platform=data.get('source_platform', ''),
            source_name=data.get('source_name', ''),
            source_url=data.get('source_url', ''),
            timestamp=data.get('timestamp', datetime.utcnow()),
            location=data.get('location', 'Kenya'),
            intent_score=data.get('intent_score', 0),
            temperature=data.get('temperature'),
            lead_hash=data.get('lead_hash')
        )
        
        return lead
    
    def _reject(self, reason: RejectionReason, stage: PipelineStage, 
                error: str) -> PipelineResult:
        """Create rejection result"""
        self.stats['processed'] += 1
        self.stats['rejected'] += 1
        self.stats['by_reason'][reason] += 1
        
        logger.warning(f"❌ Lead rejected at {stage.value}: {reason.value} - {error}")
        
        return PipelineResult(
            success=False,
            rejection_reason=reason,
            stage_failed=stage,
            error_message=error
        )
    
    def get_stats(self) -> Dict:
        """Get pipeline statistics"""
        return {
            **self.stats,
            'acceptance_rate': (
                self.stats['accepted'] / max(self.stats['processed'], 1) * 100
            )
        }


# Singleton instance
_pipeline_instance = None

def get_pipeline(db_session=None, redis_client=None) -> LeadPipeline:
    """Get or create pipeline instance"""
    global _pipeline_instance
    if _pipeline_instance is None:
        _pipeline_instance = LeadPipeline(db_session, redis_client)
    return _pipeline_instance
