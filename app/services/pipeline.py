import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import List, Dict, Any, Optional
from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
import asyncio
from app.db.database import SessionLocal
from app.scrapers import run_scrapers
from app.services.ingestion_service import ingest_leads
from app.intelligence.query_expander import get_expanded_queries
from app.nlp.intent_service import BuyingIntentNLP

from ..db import models
from ..utils.playwright_helpers import get_page_content
from ..utils.lead_validation import LeadValidator, LeadValidationError
from ..services.market_classifier import is_valid_buyer, calculate_kenyan_intent_score
from ..intelligence.verification import verify_leads as cross_source_verify
from ..config import PIPELINE_MODE, PROD_STRICT, PIPELINE_CATEGORY
from app.config.runtime import REQUIRE_VERIFICATION, INTENT_POINTS_FLOOR
from app.scrapers.verifier import is_verified_signal
from app.services.matching_service import MatchingService

logger = logging.getLogger(__name__)

async def run_pipeline_for_query(query: str, location: str = "Kenya") -> List[models.Lead]:
    """
    Orchestrates the search pipeline:
    1. Expands query into multiple targeted variations (Intent x Location x Property x Budget).
    2. Executes searches in batches (async).
    3. Processes raw results into Lead objects.
    4. Returns list of new leads.
    """
    try:
        # 1️⃣ Expand Query
        expanded_queries = get_expanded_queries(query, location)
        if not expanded_queries:
            expanded_queries = [query]
            
        logger.info(f"Running pipeline for {len(expanded_queries)} queries (Base: '{query}')")
        
        # 2️⃣ Run Scrapers (Batched)
        all_raw_results = []
        batch_size = 5 # Avoid rate limits
        
        for i in range(0, len(expanded_queries), batch_size):
            batch = expanded_queries[i:i + batch_size]
            logger.info(f"Executing batch {i//batch_size + 1}: {batch}")
            
            tasks = [run_scrapers(q, location) for q in batch]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for res in batch_results:
                if isinstance(res, list):
                    all_raw_results.extend(res)
                elif isinstance(res, Exception):
                    logger.error(f"Error in batch query execution: {res}")
            
            # Brief pause between batches if not last batch
            if i + batch_size < len(expanded_queries):
                await asyncio.sleep(1)

        logger.info(f"Total raw results fetched: {len(all_raw_results)}")

        # 3️⃣ Ingest & deduplicate (sync blocking call moved to thread)
        verified_leads = await asyncio.to_thread(ingest_leads, all_raw_results)

        # 4️⃣ Return for DB saving
        return verified_leads
        
    except Exception as e:
        logger.error(f"Pipeline execution failed for query '{query}': {e}")
        return []

class LeadPipeline:
    def __init__(self, db: Session):
        self.db = db
        self.scorer = BuyingIntentNLP()
        self.matching_service = MatchingService(db)

    def verify_leads(self, leads: List[Dict[str, Any]], strict_mode: bool = True): 
        """
        Verification Layer: Filter leads based on confidence score and cross-source verification.
        The brain in app.scrapers.verifier now handles adaptive thresholds.
        """
        # First apply cross-source and adaptive threshold verification
        verified_leads_with_reasons = cross_source_verify(leads)
        
        verified = [] 
        warnings = [] 
        from app.services.validation_service import ValidationService
        validator = ValidationService()
        
        for lead in verified_leads_with_reasons: 
            # 1. KENYA LOCKING: DB INSERT VALIDATION
            # Strict rejection of non-Kenyan content before it enters the system
            # Combine title + snippet + url for checking
            content_text = f"{lead.get('title', '')} {lead.get('snippet', '')} {lead.get('text', '')}"
            url = lead.get('url', '')
            
            if validator.is_foreign_content(content_text, url):
                # Helper _reject needs to be called on self
                url = lead.get('url', 'No URL')
                logger.info(f"[REJECTED] {url} | Reason: Foreign Content (Non-Kenyan)")
                continue
                
            # The verifier brain now sets 'verified' based on trust, cross-match, OR adaptive thresholds
            is_verified = lead.get('verified', False)
            
            # ALWAYS append, just annotate if unverified
            verified.append(lead)
            
            if not is_verified:
                warnings.append(f"Unverified signal from {lead.get('source', 'Unknown')} ({lead.get('verification_reason', 'low_confidence')})") 
                
        return verified, warnings

    def _reject(self, lead_data: Dict[str, Any], reason: str):
        """
        Helper to log rejection reasons clearly.
        """
        url = lead_data.get('url', 'No URL')
        logger.info(f"[REJECTED] {url} | Reason: {reason}")
        return None

        
    def normalize_lead(self, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normalize raw lead data into a standard dictionary.
        Requested by user to ensure consistent fields.
        """
        text = raw_data.get('text') or raw_data.get('snippet', '')
        source = raw_data.get('source', 'Web')
        
        # Ensure extraction logic is consistent
        contact_info = raw_data.get('contact', {})
        phone = raw_data.get('phone') or contact_info.get('phone') or self._extract_phone(text)
        buyer_name = raw_data.get('name') or self._extract_name(text, source)
        
        return {
            "buyer_name": buyer_name,
            "title": raw_data.get('title') or text[:50], # Fallback title
            "price": raw_data.get('price'),
            "location": raw_data.get('location') or "Kenya",
            "phone": phone,
            "source": source,
            "intent_score": raw_data.get('intent_score', 0.4),
            "url": raw_data.get('url'),
            # Helpers for internal use
            "raw_data": raw_data,
            "text": text
        }

    def process_raw_lead(self, raw_data: Dict[str, Any]) -> Optional[models.Lead]:
        """
        Process a single standardized raw lead from a "dumb" scraper.
        The Engine ("smart") decides if this is a buyer and extracts details.
        STRICT MODE: Enforces Kenyan Buyer Validation.
        
        CORRECT LEAD INTELLIGENCE ARCHITECTURE:
        Every lead MUST have 5 mandatory fields: text, phone, source, url, timestamp
        If any are missing → lead is discarded immediately
        """
        from app.services.validation_service import VALIDATION_SERVICE

        # ═══════════════════════════════════════════════════════════════
        # STEP 0: MANDATORY FIELD VALIDATION (Correct Lead Architecture)
        # ═══════════════════════════════════════════════════════════════
        # Every lead must have: text, phone, source, url, timestamp
        # If any are missing → discard immediately
        is_valid, error = LeadValidator.validate(raw_data)
        if not is_valid:
            return self._reject(raw_data, f"Mandatory field validation failed: {error}")
        
        # Extract mandatory fields
        mandatory_text = raw_data.get('text', '').strip()
        mandatory_phone = raw_data.get('phone', '').strip()
        mandatory_source = raw_data.get('source', '').strip()
        mandatory_url = raw_data.get('url', '').strip()
        mandatory_timestamp = raw_data.get('timestamp', '').strip()
        
        logger.info(f"[LeadValidator] ✅ Mandatory fields validated for source: {mandatory_source}")

        # Normalize first (keeping mandatory fields)
        normalized = self.normalize_lead(raw_data)
        url = normalized['url'] or mandatory_url
        text = normalized['text'] or mandatory_text

        if not text or not url:
            return self._reject(raw_data, "Missing required fields (text or url)")

        # --- LAYER 1: STRICT PRE-FILTER (The Bulletproof Wall) ---
        # 1. Domain Block, Seller Block, Business Entity, Buyer Phrase, First Person
        if not is_valid_buyer(text, url):
             return self._reject(raw_data, "Rejected by is_valid_buyer (Seller/Foreign/NoIntent)")

        # 0. Validation Layer (Post-Scrape)
        is_valid, error = VALIDATION_SERVICE.validate_lead_data(raw_data)
        if not is_valid:
            return self._reject(raw_data, f"Validation Failed: {error}")
            
        # 0.5. Enrichment Layer (Phone/Email Validation)
        normalized = VALIDATION_SERVICE.enrich_lead_data(normalized)
        
        # --- LAYER 2: SCORING (The Quality Gate) ---
        # 2. Scoring & Readiness (Smart Engine Logic)
        # Pass query context for bonus points
        intent_points, details = calculate_kenyan_intent_score(text, raw_data.get('query'))
        
        # Runtime-config threshold (single source of truth)
        if intent_points < INTENT_POINTS_FLOOR:
            return self._reject(
                raw_data,
                f"Score {intent_points} (<{INTENT_POINTS_FLOOR}). Details: {details}"
            )

        # Normalize score for DB (0.0 - 1.0)
        intent_score = intent_points / 100.0
        if intent_score > 1.0: intent_score = 1.0

        readiness_level, readiness_score = self.scorer.analyze_readiness(text)

        # 3. Extraction (Smart Engine Logic)
        phone = normalized['phone']
        email = raw_data.get('email')
        buyer_name = normalized['buyer_name']
        urgency = self._parse_urgency(text)
        
        # 4. Normalization
        lead_id = uuid.uuid5(uuid.NAMESPACE_URL, url)
        
        # Check if exists (Re-enabled with logging)
        existing = self.db.query(models.Lead).filter(models.Lead.url == url).first()
        if existing:
            return self._reject(raw_data, "Duplicate lead (already in DB)")

        # Determine product category dynamically from raw_data or query
        product_category = raw_data.get('product_category') or PIPELINE_CATEGORY or "General"
        
        # Ensure Title is populated
        title = normalized.get('title')
        logger.info(f"DEBUG: Processing lead title: '{title}' (repr: {repr(title)})")
        
        if not title or str(title).strip().lower() == 'general' or str(title).strip() == '':
            logger.info("DEBUG: Detected generic title. Attempting fallback.")
            # Fallback to truncated text/snippet if title is generic
            title = (text[:60] + "...") if len(text) > 60 else text
            logger.info(f"Replacing generic/empty title with snippet: {title}")
            
        # Contact Flagging (Relaxed Requirement)
        contact_flag = "ok"
        if not phone and not email:
            contact_flag = "missing_contact"
            logger.info(f"Lead missing contact info: {url} (Flagged as {contact_flag})")
            
        logger.info(f"DEBUG: Creating Lead object. title='{title}', product_category='{product_category}'")
        
        # FORCE TITLE for debugging
        # title = "FORCED_TITLE_DEBUG" 
        
        # Create DB Model
        lead = models.Lead(
            id=lead_id,
            buyer_name=buyer_name,
            title=title,  # Explicitly set title
            contact_phone=phone,
            contact_email=email,
            contact_flag=contact_flag,
            product_category=product_category,
            intent_score=intent_score,
            location_raw=normalized['location'],
            source_platform=normalized['source'],
            request_timestamp=datetime.now(timezone.utc),
            source_url=url,
            url=url, # Ensure both are populated
            buyer_request_snippet=text[:500],
            urgency_level=readiness_level, # Map readiness to urgency level string if needed
            confidence_score=readiness_score, # Use readiness as confidence for now
            contact_status="verified" if phone else "needs_outreach",
            is_hot_lead=1 if intent_score >= 0.7 else 0, # 70+ is hot
            tap_count=0,
            intent_type="BUYER"
        )
        
        return lead



    def save_leads(self, leads: List[models.Lead]):
        """Bulk save leads to database and trigger IMMEDIATE MATCHING."""
        if not leads:
            return
            
        try:
            saved_leads = []
            for lead in leads:
                try:
                    self.db.add(lead)
                    self.db.commit()
                    self.db.refresh(lead)
                    saved_leads.append(lead)
                except IntegrityError:
                    # Duplicate URLs should not abort the whole batch.
                    self.db.rollback()
                    logger.info(f"Skipping duplicate lead URL: {lead.url}")
                except Exception as save_err:
                    self.db.rollback()
                    logger.error(f"Error saving lead {lead.url}: {save_err}")
             
            # TRIGGER IMMEDIATE MATCHING
            count_matches = 0
            for lead in saved_leads:
                try:
                    matches = self.matching_service.process_lead(lead)
                    if matches:
                        count_matches += 1
                except Exception as match_err:
                    logger.error(f"Error matching lead {lead.source_url}: {match_err}")

            logger.info(f"Pipeline: Saved {len(leads)} new leads. Triggered {count_matches} matches.")
        except Exception as e:
            logger.error(f"Pipeline: Error saving leads: {e}")
            self.db.rollback()

    def _extract_phone(self, text: str) -> Optional[str]:
        import re
        # Generalized phone extraction: looks for + followed by digits, or common formats
        # Supports international formats (+1, +44, +254, etc.)
        phone_patterns = [
            r'\+(\d{1,3})\s?(\d{3})\s?(\d{3})\s?(\d{3,4})', # +254 712 345 678
            r'\+(\d{1,15})',                                 # +254712345678
            r'(?<!\d)(07\d{8}|01\d{8})(?!\d)',               # Kenyan local 07... or 01...
            r'(?<!\d)(\d{10,15})(?!\d)'                      # Long digit strings
        ]
        
        for pattern in phone_patterns:
            match = re.search(pattern, text)
            if match:
                found = match.group(0).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                if found.startswith('0') and len(found) == 10:
                    return '254' + found[1:]
                if found.startswith('+'):
                    return found.replace('+', '')
                return found
        return None

    def _extract_name(self, text: str, source: str) -> str:
        import re
        name_patterns = [
            r"Post by\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Contact:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
            r"Name:\s+([A-Z][a-z]+\s+[A-Z][a-z]+)",
        ]
        for pattern in name_patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)
        return "Verified Market Signal"

    def _parse_urgency(self, text: str) -> str:
        text = text.lower()
        high = ["asap", "urgently", "urgent", "immediately", "now", "today"]
        if any(kw in text for kw in high):
            return "high"
        return "medium"

    def _generate_whatsapp_link(self, phone: str, product: str) -> Optional[str]:
        if not phone:
            return None
        import urllib.parse
        message = f"Hello, I saw your request for {product}. I can help you with that!"
        return f"https://wa.me/{phone}?text={urllib.parse.quote(message)}"
