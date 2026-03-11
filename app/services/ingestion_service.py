
import logging
import uuid
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session
from ..db import models
from app.db.database import SessionLocal
from .market_classifier import calculate_kenyan_intent_score, is_valid_buyer
from ..intelligence_v2 import (
    calculate_final_intelligence_score,
    classify_lead_priority,
    extract_contact_info,
    FLOOR,
    STRICT_PUBLIC
)
from app.config.runtime import INTENT_POINTS_FLOOR
from ..utils.lead_validation import (
    LeadValidator, 
    FreshnessChecker, 
    LeadQualificationValidator,
    LeadFreshness
)
from ..utils.buyer_phone_extractor import BuyerPhoneExtractor
from ..utils.phone_verification import KenyaPhoneVerifier
from ..utils.intent_scorer import IntentScorer, LeadTemperature

logger = logging.getLogger(__name__)

def ingest_signal(db: Session, signal: Dict[str, Any], product_query: str = "Unknown"):
    """
    Standardized Ingestion Gate:
    1. Receives DUMB signal from scraper.
    2. VALIDATES: 5 mandatory fields (text, phone, source, url, timestamp)
    3. FRESHNESS CHECK: Discard if > 7 days old
    4. Runs Intelligence Layer (v2).
    5. Enforces FLOOR threshold.
    6. Maps to Lead schema.
    
    CORRECT LEAD INTELLIGENCE ARCHITECTURE:
    Every lead MUST have 5 mandatory fields: text, phone, source, url, timestamp
    If any are missing → discard lead immediately
    
    LEAD FRESHNESS FILTER:
    - Fresh = < 24 hours old
    - Warm = < 3 days old
    - Cold = < 7 days old
    - Discard = > 7 days old
    
    KENYA-ONLY: Rejects any signal that is not explicitly from Kenya.
    """
    from app.services.validation_service import VALIDATION_SERVICE
    
    # ═══════════════════════════════════════════════════════════════
    # STEP 0: MANDATORY FIELD + FRESHNESS VALIDATION
    # ═══════════════════════════════════════════════════════════════
    # Combined validation: checks 5 mandatory fields AND freshness
    validated_lead = LeadQualificationValidator.validate_or_discard(signal)
    if not validated_lead:
        return None
    
    # Extract freshness metadata
    freshness_metadata = validated_lead.get('_freshness', {})
    freshness_label = freshness_metadata.get('freshness_label', 'unknown')
    
    logger.info(
        f"[INGESTION] ✅ Lead qualified: source={signal.get('source')}, "
        f"freshness={freshness_label}"
    )
    
    raw_text = signal.get("text", "").strip()
    source = signal.get("source", "unknown").strip()
    source_url = signal.get("url", "").strip()
    location = signal.get("location", "Kenya")
    
    # --- KENYA LOCKING: STRICT LOCATION CHECK ---
    # Reject any signal not explicitly from Kenya
    if VALIDATION_SERVICE.is_foreign_content(raw_text, source_url):
        logger.info(f"SIGNAL REJECTED (Kenya-Only Policy): {source} - Content not from Kenya")
        return False
    
    # Also check location field
    if location and not any(loc in location.lower() for loc in ["kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret", "thika"]):
        logger.info(f"SIGNAL REJECTED (Kenya-Only Policy): Location '{location}' not in Kenya")
        return False
    
    # --- LAYER 1 & 4: STRICT PRE-FILTER ---
    # Before any scoring, check if this is a valid buyer signal
    if not is_valid_buyer(raw_text, source_url):
        logger.info(f"SIGNAL REJECTED (Strict Filter): {source} - {raw_text[:50]}...")
        return False
    
    # 1. 🧠 Intelligence Layer: Intent Detection (Kenyan Model)
    intent_points, details = calculate_kenyan_intent_score(raw_text)
    
    # Runtime-config threshold (single source of truth)
    if intent_points < INTENT_POINTS_FLOOR:
        logger.info(
            f"SIGNAL REJECTED: Score {intent_points} (<{INTENT_POINTS_FLOOR}) for source {source}"
        )
        return False
        
    # Normalize for DB (0.0 - 1.0)
    raw_intent = intent_points / 100.0
    if raw_intent > 1.0: raw_intent = 1.0
    
    # 2. 🧠 AI INTENT SCORING (NEW)
    # Score based on buying intent using NLP analysis
    intent_score_result = IntentScorer.calculate_score(raw_text)
    ai_intent_score = intent_score_result.score / 100.0  # Normalize to 0-1
    ai_temperature = intent_score_result.temperature.value
    
    logger.info(
        f"[INGESTION] AI Intent Score: {intent_score_result.score}/100 "
        f"({ai_temperature}) - {intent_score_result.reasoning}"
    )
    
    # Reject if AI score is too low (below COLD threshold)
    if intent_score_result.temperature == LeadTemperature.REJECT:
        logger.warning(
            f"[INGESTION] ❌ Lead discarded - AI Intent too low: "
            f"{intent_score_result.score}/100 - {intent_score_result.reasoning}"
        )
        return None
    
    # 3. 🧠 Intelligence Layer: Semantic/Confidence Scoring
    # Combine traditional scoring with AI intent score
    semantic_baseline = 0.5 
    
    # Blend traditional score with AI intent score (70% AI, 30% traditional)
    blended_intent = (ai_intent_score * 0.7) + (raw_intent * 0.3)
    
    final_score = calculate_final_intelligence_score(
        raw_intent_score=blended_intent,
        semantic_score=semantic_baseline,
        text=raw_text,
        source_name=source,
        lead_data={
            "location_raw": signal.get("location", "Kenya"),
            "contact_phone": signal.get("contact", {}).get("phone"),
            "buyer_request_snippet": raw_text
        }
    )
    
    # 4. 🚦 Threshold Enforcement (Double Check)
    if final_score < FLOOR:
        logger.info(f"SIGNAL REJECTED: Final Score {final_score} below floor {FLOOR}")
        return False

    # 4. 📞 Contact Extraction (BUYER-ONLY VALIDATION)
    # Re-validate that the phone came from a buyer post
    buyer_extraction = BuyerPhoneExtractor.validate_and_extract(raw_text, source)
    
    if not buyer_extraction['is_valid_buyer']:
        logger.warning(
            f"[INGESTION] ❌ Lead discarded - Not a valid buyer post: "
            f"{buyer_extraction['reason']}"
        )
        return None
    
    # Use the validated buyer phone
    phone = buyer_extraction['phone']
    
    # Also extract other contact info
    contacts = extract_contact_info(raw_text)
    signal_contacts = signal.get("contact", {})
    whatsapp = signal_contacts.get("whatsapp") or contacts.get("whatsapp")
    email = signal_contacts.get("email") or contacts.get("email")

    try:
        # Deduplication by URL (DISABLED for now to allow save)
        # source_url = signal.get("url")
        # if source_url:
        #    existing = db.query(models.Lead).filter(models.Lead.source_url == source_url).first()
        #    if existing:
        #        return False
        
        # Extract MANDATORY fields (already validated above)
        mandatory_text = signal.get("text", "").strip()
        mandatory_phone = signal.get("phone", "").strip()
        mandatory_source = signal.get("source", "").strip()
        mandatory_url = signal.get("url", "").strip()
        mandatory_timestamp = signal.get("timestamp", "").strip()
        
        # 5. 🗺️ Mapping to Lead schema
        lead_id = uuid.uuid4()
        priority = classify_lead_priority(final_score)
        
        contact_flag = "ok"
        if not phone and not email:
            contact_flag = "missing_contact"
        
        # Parse timestamp
        try:
            parsed_timestamp = datetime.fromisoformat(mandatory_timestamp.replace('Z', '+00:00'))
        except (ValueError, AttributeError):
            parsed_timestamp = datetime.utcnow()
        
        db_lead = models.Lead(
            id=lead_id,
            # ═══════════════════════════════════════════════════════════════
            # 5 MANDATORY FIELDS (Correct Lead Intelligence Architecture)
            # ═══════════════════════════════════════════════════════════════
            text=mandatory_text,
            phone=mandatory_phone,
            source=mandatory_source,
            url=mandatory_url,
            timestamp=parsed_timestamp,
            # ═══════════════════════════════════════════════════════════════
            # LEAD FRESHNESS (auto-calculated)
            # ═══════════════════════════════════════════════════════════════
            freshness=freshness_label,
            age_hours=age_hours,
            # ═══════════════════════════════════════════════════════════════
            # Additional fields
            buyer_name=signal.get("author") or "Market Signal",
            contact_phone=phone or mandatory_phone,  # Use mandatory phone as fallback
            contact_email=email,
            contact_flag=contact_flag,
            product_category=product_query,
            intent_score=blended_intent,  # Use AI-blended score
            ai_intent_score=intent_score_result.score,
            ai_temperature=ai_temperature,
            ai_score_reasoning=intent_score_result.reasoning,
            ai_score_breakdown=intent_score_result.breakdown,
            location_raw=signal.get("location", "Kenya"),
            source_platform=mandatory_source,
            request_timestamp=parsed_timestamp,
            whatsapp_link=whatsapp,
            source_url=mandatory_url,
            buyer_request_snippet=raw_text[:500], # Keep snippet manageable
            urgency_level=priority,
            confidence_score=final_score,
            contact_status="verified" if (phone or whatsapp or mandatory_phone) else "needs_outreach",
            is_hot_lead=1 if ai_temperature == "HOT" else 0,  # Use AI temperature
            tap_count=0,
            intent_type="BUYER"  # Explicitly mark as BUYER since we pre-filtered
        )
        
        db.add(db_lead)
        
        # Log Activity
        log = models.ActivityLog(
            event_type="SIGNAL_INGESTED",
            lead_id=lead_id,
            extra_metadata={
                "source": source,
                "score": final_score,
                "ai_score": intent_score_result.score,
                "ai_temperature": ai_temperature,
                "ai_reasoning": intent_score_result.reasoning,
                "priority": priority,
                "buyer_validated": True,
                "phone_source": "buyer_post",
                "extraction_reason": buyer_extraction.get('reason', '')
            }
        )
        db.add(log)
        
        db.commit()
        
        # Get freshness info for logging
        freshness_info = freshness_label.upper()
        age_hours = freshness_metadata.get('age_hours', 0)
        
        logger.info(
            f"SIGNAL ACCEPTED: {priority} lead saved from {mandatory_source} "
            f"| Score: {final_score:.3f} "
            f"| Freshness: {freshness_info} ({age_hours}h old) "
            f"| Fields: text={len(mandatory_text)}ch, phone={mandatory_phone[:4]}..."
        )
        return db_lead
        
    except Exception as e:
        db.rollback()
        logger.error(f"INGESTION ERROR: {str(e)}")
        return None

def ingest_lead(db: Session, lead_data: Dict[str, Any]):
    """Legacy wrapper for backward compatibility"""
    # Map old format to signal format if needed, or just redirect
    return ingest_signal(db, lead_data)

def ingest_leads(raw_results: List[Dict[str, Any]]) -> List[models.Lead]:
    db = SessionLocal()
    saved = []
    try:
        for signal in raw_results:
            if not isinstance(signal, dict):
                continue
            product_query = signal.get("query") or signal.get("product_category") or "Unknown"
            lead = ingest_signal(db, signal, product_query)
            if lead:
                saved.append(lead)
        return saved
    finally:
        db.close()
