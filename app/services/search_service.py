# app/services/search_service.py
# ============================================================
# SEARCH SERVICE â€” Runs scrapers in priority order
# ============================================================
# Execution order:
# 1. SerpAPI (priority 1000)
# 2. Google CSE (priority 950)
# 3. Telegram (priority 900)
# 4. Facebook Groups (priority 800)
# 5. ... other scrapers ...
# 6. DuckDuckGo (priority 100) â€” LAST
# ============================================================

import logging
import hashlib
import asyncio
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.scrapers.registry import get_active_scrapers_sorted, get_scraper_name
from app.db.database import SessionLocal
from app.config.runtime import (
    INTENT_THRESHOLD, INTENT_POINTS_FLOOR, CONFIDENCE_FLOOR,
    HIGH_RECALL_MODE, ENABLE_CELERY,
    SOURCE_RELIABILITY, SCRAPER_TIMEOUTS, SCRAPER_MAX_RESULTS
)
from app.services.intent_engine import calculate_intent_score
from app.services.market_classifier import classify_market_side, is_valid_buyer
from app.services.urgency_ranker import calculate_urgency_score
from app.services.persona_detector import detect_persona
from app.services.confidence_engine import calculate_confidence
from app.services.page_enricher import enrich_lead_data
from app.services.cache_service import cache
from app.services.validation_service import VALIDATION_SERVICE
from app.engine.buyer_classifier import BUYER_CLASSIFIER
from app.engine.search_engine import SEARCH_ENGINE

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except Exception:
    DDGS = None


async def _run_scraper_with_timeout(scraper, query: str, location: str, timeout_seconds: int):
    """Run one scraper with timeout and standard error isolation."""
    return await asyncio.wait_for(scraper.search(query, location), timeout=timeout_seconds)


def _fallback_platform_search(scraper_name: str, query: str, location: str) -> List[Dict[str, Any]]:
    """DDG fallback when Playwright-heavy sources timeout."""
    if DDGS is None:
        return []

    source_key = (scraper_name or "").lower()
    site_prefix = ""
    if "facebook" in source_key:
        site_prefix = "site:facebook.com/groups"
    elif "kenyan_forums" in source_key or "forum" in source_key:
        site_prefix = "site:kenyatalk.com OR site:wazua.co.ke OR site:jamiiforums.com"
    elif "twitter" in source_key:
        site_prefix = "site:x.com OR site:twitter.com"
    else:
        return []

    buyer_query = (
        f'{site_prefix} "{query}" "{location}" '
        f'("looking for" OR "want to buy" OR "need" OR "wtb" OR "natafuta" OR "nahitaji")'
    )

    fallback_results: List[Dict[str, Any]] = []
    try:
        with DDGS() as ddgs:
            rows = list(ddgs.text(buyer_query, region="ke-en", timelimit="w", max_results=10))
        for item in rows:
            url = item.get("href", "")
            if not url:
                continue
            fallback_results.append({
                "source": scraper_name,
                "url": url,
                "title": item.get("title", ""),
                "text": f"{item.get('title', '')} {item.get('body', '')}".strip(),
                "location": location,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
    except Exception as e:
        logger.debug(f"{scraper_name} fallback failed: {e}")

    return fallback_results


def _get_source_reliability(source: str) -> float:
    """Get source reliability from config."""
    source_lower = source.lower().replace(" ", "_")
    # Check exact match first, then partial
    if source_lower in SOURCE_RELIABILITY:
        return SOURCE_RELIABILITY[source_lower]
    for key, value in SOURCE_RELIABILITY.items():
        if key in source_lower or source_lower in key:
            return value
    return 0.5  # Default


def _process_raw_result(r: dict, query: str, location: str) -> dict:
    """Convert raw scraper result to UI-ready lead dict."""
    title = r.get("title") or r.get("text") or ""
    text = r.get("text") or r.get("snippet") or r.get("title") or ""
    url = r.get("url") or r.get("link") or ""
    source = r.get("source") or "Unknown"

    if not text and not title:
        return None
    if not url:
        return None

    # Calculate scores
    try:
        intent_score = calculate_intent_score(text)
    except Exception:
        intent_score = 0.3

    try:
        urgency = calculate_urgency_score(text)
    except Exception:
        urgency = 0.2

    try:
        persona = detect_persona(text, source)
    except Exception:
        persona = "End User"

    source_rel = _get_source_reliability(source)

    try:
        confidence = calculate_confidence(intent_score, urgency, source_rel)
    except Exception:
        confidence = max(0.3, CONFIDENCE_FLOOR)

    try:
        market_side = classify_market_side(text)
    except Exception:
        market_side = "unknown"

    # Badge
    if intent_score > 0.7 and urgency > 0.6:
        badge = "HOT"
    elif intent_score > 0.4 or confidence > 0.5:
        badge = "WARM"
    else:
        badge = "COLD"

    # Contact extraction
    phone = r.get("phone") or ""
    email = r.get("email") or ""
    if not phone:
        contact = r.get("contact", {})
        if isinstance(contact, dict):
            phone = contact.get("phone") or ""
            email = email or contact.get("email") or ""

    # WhatsApp
    whatsapp_url = ""
    if phone:
        clean = phone.replace("+", "").replace(" ", "").replace("-", "")
        if clean.startswith("0") and len(clean) == 10:
            clean = "254" + clean[1:]
        elif not clean.startswith("254") and len(clean) == 9:
            clean = "254" + clean
        whatsapp_url = f"https://wa.me/{clean}"

    # Ranked score (source reliability affects ranking)
    ranked_score = round(
        intent_score * 0.35 +
        urgency * 0.20 +
        confidence * 0.20 +
        source_rel * 0.25,  # Source quality matters for ranking
        3
    )

    return {
        "id": hashlib.md5(url.encode()).hexdigest()[:16],
        "buyer_name": r.get("author") or r.get("buyer_name") or r.get("user") or "Market Signal",
        "title": (title[:200] if title else text[:200]) if (title or text) else "Lead",
        "price": r.get("price") or "Contact for Price",
        "location": r.get("location") or location,
        "phone": phone,
        "contact_phone": phone,
        "email": email,
        "contact_email": email,
        "source": source,
        "url": url,
        "source_url": url,

        # Scores
        "intent_score": intent_score,
        "intent_strength": intent_score,
        "buyer_match_score": ranked_score,
        "confidence": confidence,
        "confidence_score": confidence,
        "urgency_score": urgency,
        "ranked_score": ranked_score,
        "rank_score": ranked_score,
        "source_reliability": source_rel,

        # Display
        "buyer_request_snippet": text[:500] if text else "",
        "buyer_intent_quote": text[:300] if text else "",
        "snippet": text[:300] if text else "",
        "intent": text[:200] if text else "",

        # Metadata
        "market_side": market_side,
        "badge": badge,
        "verification_flag": "verified" if phone else "unverified",
        "intent_type": "BUYER",
        "persona": persona,
        "status": "NEW",
        "is_hot_lead": badge == "HOT",
        "geo_score": 1.0 if "kenya" in (r.get("location") or location).lower() else 0.5,
        "geo_strength": "high" if "kenya" in (r.get("location") or location).lower() else "medium",
        "geo_region": location,

        # WhatsApp
        "whatsapp_url": whatsapp_url,
        "whatsapp_link": whatsapp_url,

        # Timestamps
        "created_at": r.get("timestamp") or datetime.now(timezone.utc).isoformat(),
        "query": query,
        "product": title or query,
        "score_details": [],
        "ui_filter_status": "shown",
        "tap_count": 0
    }


async def search(query: str, location: str):
    """
    Main search. Runs scrapers in PRIORITY ORDER:
    SerpAPI â†’ Google CSE â†’ Telegram â†’ Facebook â†’ Forums â†’ ... â†’ DuckDuckGo
    """

    # â”€â”€ VALIDATION â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    is_valid, error = VALIDATION_SERVICE.validate_search_request(query, location)
    if not is_valid:
        logger.warning(f"ðŸš« Validation Failed: {error}")
        return {
            "results": [], "leads": [],
            "metrics": {"error": error},
            "message": error, "count": 0,
            "status": "validation_failed"
        }

    metrics = {
        "scrapers_run": [],
        "scraper_results": {},
        "total_found": 0,
        "total_processed": 0,
        "total_shown": 0,
        "execution_order": [],
        "processing_mode": "direct"
    }

    if len(query.strip()) < 2:
        return {
            "results": [], "leads": [],
            "metrics": metrics,
            "message": "Query too short", "count": 0,
            "status": "skipped"
        }

    # â”€â”€ CACHE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    cache_key = f"search:v6:{hashlib.md5(f'{query}:{location}'.lower().encode()).hexdigest()}"
    cached = cache.get(cache_key)
    if cached:
        logger.info(f"✅ Cache hit for '{query}'")
        return cached

    # Use engine as single source of truth so legacy and engine paths are identical.
    try:
        engine_resp = await SEARCH_ENGINE.search(
            query=query,
            location=location,
            include_all=False,
            allow_legacy_fallback=False,
        )
        leads = engine_resp.get("results") or engine_resp.get("leads") or []
        response = {
            "results": leads,
            "leads": leads,
            "metrics": {
                **(engine_resp.get("metrics") or {}),
                "processing_mode": "engine_delegate",
            },
            "count": len(leads),
            "total_signals_captured": engine_resp.get("total_signals_captured", 0),
            "total_signals_scanned": engine_resp.get(
                "total_signals_scanned",
                (engine_resp.get("metrics") or {}).get("total_signals_scanned", 0),
            ),
            "buyers_found": len(leads),
            "status": engine_resp.get("status", "success" if leads else "no_results"),
            "message": engine_resp.get(
                "message",
                f"Found {len(leads)} leads" if leads else "No leads found. Try different keywords.",
            ),
        }
        if leads:
            cache.set(cache_key, response, ttl_seconds=1200)
        return response
    except Exception as e:
        logger.warning(f"Engine delegation failed; using legacy path: {e}")

    # â”€â”€ RUN SCRAPERS IN PRIORITY ORDER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    scrapers = get_active_scrapers_sorted()

    if not scrapers:
        logger.error("ðŸš¨ No active scrapers!")
        return {
            "results": [], "leads": [],
            "metrics": {**metrics, "error": "No scrapers configured"},
            "message": "No scrapers available", "count": 0,
            "status": "config_error"
        }

    raw_results = []
    max_parallel = 6
    semaphore = asyncio.Semaphore(max_parallel)

    async def run_one(idx: int, scraper):
        scraper_name = get_scraper_name(scraper) or scraper.__class__.__name__
        timeout_seconds = SCRAPER_TIMEOUTS.get(scraper_name, 15)
        metrics["scrapers_run"].append(scraper_name)
        metrics["execution_order"].append({
            "position": idx + 1,
            "name": scraper_name,
            "priority": timeout_seconds
        })
        logger.info(f"ðŸ”„ [{idx+1}/{len(scrapers)}] Running: {scraper_name} (timeout={timeout_seconds}s)")

        async with semaphore:
            try:
                results = await _run_scraper_with_timeout(scraper, query, location, timeout_seconds)
                return scraper_name, results or [], None
            except asyncio.TimeoutError:
                return scraper_name, [], f"TIMEOUT>{timeout_seconds}s"
            except Exception as e:
                return scraper_name, [], str(e)

    run_tasks = [run_one(idx, scraper) for idx, scraper in enumerate(scrapers)]
    run_results = await asyncio.gather(*run_tasks, return_exceptions=False)

    for scraper_name, results, err in run_results:
        if err:
            logger.error(f"  âŒ {scraper_name} failed: {err}")
            fallback_results = _fallback_platform_search(scraper_name, query, location)
            if fallback_results:
                logger.info(f"  â†ªï¸ {scraper_name} fallback recovered {len(fallback_results)} results")
                metrics["scraper_results"][scraper_name] = f"FALLBACK:{len(fallback_results)} ({err[:30]})"
                metrics["total_found"] += len(fallback_results)
                for r in fallback_results:
                    if not r.get("source"):
                        r["source"] = scraper_name
                    raw_results.append(r)
            else:
                metrics["scraper_results"][scraper_name] = f"ERROR: {err[:50]}"
            continue

        count = len(results)
        logger.info(f"  âœ… {scraper_name}: {count} results")
        metrics["total_found"] += count
        metrics["scraper_results"][scraper_name] = count
        for r in results:
            if not r.get("source"):
                r["source"] = scraper_name
            raw_results.append(r)

    logger.info(f"ðŸ“Š Total raw results: {len(raw_results)}")

    # â”€â”€ PROCESS RESULTS â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    processed_leads = []
    seen_urls = set()
    seen_text_hashes = set()

    for r in raw_results:
        url = r.get("url") or r.get("link") or ""

        # URL dedup
        if url in seen_urls:
            continue
        seen_urls.add(url)

        # Text dedup (fuzzy â€” first 100 chars)
        text = r.get("text") or r.get("title") or ""
        text_hash = hashlib.md5(text.lower().strip()[:100].encode()).hexdigest()
        if text_hash in seen_text_hashes:
            continue
        seen_text_hashes.add(text_hash)

        # Process
        try:
            # Align with engine behavior: classifier-first buyer gate + market validator.
            source = r.get("source") or "Unknown"
            signal = BUYER_CLASSIFIER.classify(text, source)
            if not signal.is_buyer:
                continue
            if signal.confidence < CONFIDENCE_FLOOR:
                continue
            if not is_valid_buyer(text, url):
                continue
            if not SEARCH_ENGINE._passes_precision_filter(r, signal, query):
                continue

            lead = SEARCH_ENGINE._build_lead(r, signal, query)
            if lead:
                lead["market_side"] = "demand"
                lead["intent_type"] = "BUYER"
                # Only filter if confidence is below the VERY low floor
                if lead.get("confidence", 0) >= CONFIDENCE_FLOOR:
                    processed_leads.append(lead)
                    metrics["total_processed"] += 1
        except Exception as e:
            logger.error(f"Processing error: {e}")

    # â”€â”€ SORT BY RANKED SCORE (Source quality matters) â”€â”€
    processed_leads.sort(
        key=lambda x: x.get("ranked_score", 0),
        reverse=True
    )

    metrics["total_shown"] = len(processed_leads)

    # If legacy path still yields no leads, use engine logic directly (without recursion).
    if not processed_leads:
        try:
            engine_resp = await SEARCH_ENGINE.search(
                query=query,
                location=location,
                include_all=False,
                allow_legacy_fallback=False,
            )
            engine_leads = engine_resp.get("results") or engine_resp.get("leads") or []
            if engine_leads:
                processed_leads = engine_leads
                metrics["processing_mode"] = "engine_fallback"
                metrics["total_processed"] = len(processed_leads)
                metrics["total_shown"] = len(processed_leads)
        except Exception as e:
            logger.debug(f"Engine fallback unavailable: {e}")

    # â”€â”€ OPTIONAL: Background DB save with fallback â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    if ENABLE_CELERY and raw_results:
        try:
            from app.core.celery_app import send_task
            result = send_task("ingest_leads_task", raw_results)
            if result.get("status") == "queued":
                logger.info(f"ðŸ“¨ Sent to Celery for background DB save (Task ID: {result.get('task_id')})")
            elif result.get("status") == "completed_direct":
                logger.info("âœ… Ingestion completed directly (Celery unavailable)")
            else:
                logger.warning(f"Ingestion status: {result.get('status')}")
        except Exception as e:
            logger.debug(f"Background save unavailable: {e}")

    # â”€â”€ RESPONSE â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    response = {
        "results": processed_leads,
        "leads": processed_leads,
        "metrics": metrics,
        "count": len(processed_leads),
        "total_signals_captured": metrics["total_found"],
        "total_signals_scanned": metrics["total_found"],
        "buyers_found": len(processed_leads),
        "status": "success" if processed_leads else "no_results",
        "message": (
            f"Found {len(processed_leads)} leads from {len(metrics['scrapers_run'])} scrapers "
            f"(Top: {metrics['scrapers_run'][0] if metrics['scrapers_run'] else 'none'})"
            if processed_leads else
            "No leads found. Try different keywords."
        )
    }

    # Cache for 20 minutes
    if processed_leads:
        cache.set(cache_key, response, ttl_seconds=1200)

    logger.info(f"ðŸ Returning {len(processed_leads)} leads for '{query}'")
    return response

