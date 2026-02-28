# app/engine/search_engine.py
# ============================================================
# SEARCH ENGINE — Updated with priority ordering + low confidence floor
# ============================================================

import asyncio
import logging
import hashlib
import re
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.engine.query_intelligence import QUERY_ENGINE
from app.engine.multi_source_scraper import MULTI_SCRAPER
from app.engine.buyer_classifier import BUYER_CLASSIFIER
from app.services.cache_service import cache
from app.services.market_classifier import is_valid_buyer
from app.config.runtime import (
    CONFIDENCE_FLOOR, SCRAPER_PRIORITIES, SOURCE_RELIABILITY,
    KENYA_ONLY, ALLOWED_LOCATIONS
)

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS
except Exception:
    DDGS = None


class SearchEngine:
    """Universal buyer-finding search engine with priority-ordered sources."""

    def __init__(self):
        self.query_engine = QUERY_ENGINE
        self.scraper = MULTI_SCRAPER
        self.classifier = BUYER_CLASSIFIER

    def _validate_kenya_location(self, location: str) -> bool:
        """Validate that location is in Kenya."""
        if not KENYA_ONLY:
            return True
        if not location:
            return True  # Default will be Kenya
        loc_lower = location.lower().strip()
        return any(allowed in loc_lower for allowed in ALLOWED_LOCATIONS)

    async def search(
        self,
        query: str,
        location: str = "Kenya",
        include_all: bool = False,
        min_score: float = 0.0,    # No minimum — confidence floor handles it
        allow_legacy_fallback: bool = True
    ) -> Dict[str, Any]:

        # KENYA-ONLY VALIDATION
        if not self._validate_kenya_location(location):
            logger.warning(f"🚫 KENYA-ONLY POLICY: Rejected location '{location}'")
            return {
                "results": [],
                "leads": [],
                "metrics": {"error": f"Location '{location}' not supported. Kenya only.", "kenya_only": True},
                "count": 0,
                "total_signals_captured": 0,
                "total_signals_scanned": 0,
                "buyers_found": 0,
                "status": "kenya_only_policy",
                "message": f"Location '{location}' is not supported. This system only supports Kenya locations."
            }

        logger.info(f"🔍 ENGINE: '{query}' in '{location}'")
        logger.info(f"ENGINE_SEARCH_START: {query}")
        
        try:
            # Cache - DISABLED for debugging
        cache_key = f"engine:v6:{hashlib.md5(f'{query}:{location}'.lower().encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            logger.info("✅ Cache hit - but running anyway for debug")
            logger.info(f"CACHE_HIT: Would return {len(cached.get('leads', []))} leads")
            # return cached  # DISABLED - run full search for debugging

        # FAST: Try DDG first for quick results
        logger.info("ENGINE: Starting _fast_ddg_search...")
        raw_results = await self._fast_ddg_search(query, location)
        logger.info(f"ENGINE: _fast_ddg_search returned {len(raw_results)} results")
        
        # Generate search plan for additional sources
        plan = self.query_engine.generate_search_plan(query, location)
        sorted_platforms = sorted(
            plan.get("platforms", {}).keys(),
            key=lambda p: SCRAPER_PRIORITIES.get(p, 10),
            reverse=True
        )
        logger.info(f"📋 Platform order: {sorted_platforms}")

        # Only run scrapers if we don't have enough results from DDG
        if len(raw_results) < 5:
            ordered_platforms = {}
            for p in sorted_platforms:
                if p in plan["platforms"]:
                    ordered_platforms[p] = plan["platforms"][p]
            plan["platforms"] = ordered_platforms

            try:
                scraper_results = await asyncio.wait_for(
                    self.scraper.execute_search_plan(plan),
                    timeout=15
                )
                raw_results.extend(scraper_results)
                logger.info(f"📊 Total raw results: {len(raw_results)}")
            except asyncio.TimeoutError:
                logger.warning("⏰ Scraper timeout - using DDG results only")

        # Classify
        leads = []
        rejected = []
        seen_hashes = set()
        
        logger.info(f"🔍 Classifying {len(raw_results)} raw results")
        logger.info(f"ENGINE_RAW_RESULTS: {len(raw_results)}")
        
        if not raw_results:
            logger.info("ENGINE_NO_RAW_RESULTS - returning empty")
            return {
                "results": [],
                "leads": [],
                "metrics": {"error": "No raw results from scrapers"},
                "count": 0,
                "total_signals_captured": 0,
                "total_signals_scanned": 0,
                "buyers_found": 0,
                "status": "no_results",
                "message": "No results found. Try different keywords."
            }

        for raw in raw_results:
            text = raw.get("text", "")
            url = raw.get("url", "")
            source = raw.get("source", "")
            
            if not text:
                continue

            # Dedup
            text_hash = hashlib.md5(text.lower().strip()[:200].encode()).hexdigest()
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            # Classify
            try:
                signal = self.classifier.classify(text, source)
            except Exception as e:
                logger.error(f"Classifier error: {e}")
                continue

            if not self._passes_precision_filter(raw, signal, query):
                rejected.append({
                    "url": url,
                    "reason": "listing_noise_or_low_buyer_signal",
                })
                continue

            # Hard buyer validation gate: avoid surfacing seller/listing noise.
            if not is_valid_buyer(text, url):
                rejected.append({
                    "url": url,
                    "reason": "market_classifier_rejected_non_buyer",
                })
                continue

            # Buyer-first inclusion: include_all can still expose non-buyer
            # diagnostics, but only when explicitly requested.
            if signal.is_buyer or include_all:
                if signal.confidence >= CONFIDENCE_FLOOR:
                    lead = self._build_lead(raw, signal, query)
                    leads.append(lead)
                else:
                    rejected.append({
                        "url": url,
                        "reason": f"Confidence {signal.confidence:.2f} < {CONFIDENCE_FLOOR}",
                    })
            else:
                rejected.append({
                    "url": url,
                    "reason": "Classified as seller",
                })
        
        logger.info(f"✅ {len(leads)} leads passed, {len(rejected)} rejected")
        logger.info(f"ENGINE_LEADS_PASSED: {len(leads)}")
        logger.info(f"ENGINE_REJECTED: {len(rejected)}")
        
        # Show first 3 rejection reasons
        for r in rejected[:3]:
            print(f"  REJECTED: {r.get('reason')} - {r.get('url', '')[:50]}...")

        # Sort: Source reliability + intent score
        leads.sort(key=lambda x: (
            x.get("source_reliability", 0.5) * 0.3 +
            x.get("intent_score", 0) * 0.4 +
            x.get("urgency_score", 0) * 0.15 +
            x.get("confidence", 0) * 0.15
        ), reverse=True)

        # Fallback: if new engine returns no leads, run legacy search pipeline.
        if not leads and allow_legacy_fallback:
            try:
                from app.services.search_service import search as legacy_search
                legacy_resp = await legacy_search(query=query, location=location)
                legacy_leads = legacy_resp.get("results") or legacy_resp.get("leads") or []
                if legacy_leads:
                    logger.info(f"Legacy fallback recovered {len(legacy_leads)} leads")
                    leads = legacy_leads
            except Exception as e:
                logger.warning(f"Legacy fallback failed: {e}")
        
        # RAW RESULTS FALLBACK: if we have raw results but no leads, return them as unclassified
        if not leads and raw_results:
            print(f"ENGINE_RAW_FALLBACK: Using {len(raw_results)} raw results")
            logger.warning(f"Returning {len(raw_results)} raw results as unclassified leads")
            for raw in raw_results[:10]:  # Limit to top 10
                leads.append({
                    "id": hashlib.md5(raw.get("url", "").encode()).hexdigest()[:16],
                    "buyer_name": "Unknown",
                    "title": raw.get("title", "")[:100] or raw.get("text", "")[:100],
                    "price": "Contact for Price",
                    "location": raw.get("location", location),
                    "phone": "",
                    "contact_phone": "",
                    "email": "",
                    "contact_email": "",
                    "source": raw.get("source", "unknown"),
                    "url": raw.get("url", ""),
                    "source_url": raw.get("url", ""),
                    "intent_score": 0.5,
                    "intent_strength": 0.5,
                    "buyer_match_score": 0.5,
                    "confidence": 0.5,
                    "confidence_score": 0.5,
                    "urgency_score": 0.5,
                    "ranked_score": 0.5,
                    "rank_score": 0.5,
                    "source_reliability": 0.5,
                    "buyer_request_snippet": raw.get("text", "")[:300],
                    "buyer_intent_quote": raw.get("text", "")[:200],
                    "snippet": raw.get("text", "")[:200],
                    "intent": raw.get("text", "")[:150],
                    "market_side": "unknown",
                    "badge": "WARM",
                    "verification_flag": "unverified",
                    "intent_type": "UNKNOWN",
                    "persona": "unknown",
                    "timeline": "unknown",
                    "status": "NEW",
                    "is_hot_lead": False,
                    "geo_score": 0.5,
                    "geo_strength": "medium",
                    "geo_region": raw.get("location", location),
                    "whatsapp_url": "",
                    "whatsapp_link": "",
                    "created_at": raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
                    "query": query,
                    "product": raw.get("title", query),
                    "ui_filter_status": "shown",
                    "tap_count": 0
                })
        
        # Buyer-intent web probe fallback: avoids no-result dead end when heavy sources timeout.
        if not leads:
            probe_leads = self._high_intent_ddg_fallback(query, location)
            if probe_leads:
                logger.info(f"High-intent DDG probe recovered {len(probe_leads)} leads")
                leads = probe_leads

        # Metrics
        metrics = {
            "category": plan["category"],
            "platforms_searched": sorted_platforms,
            "platform_order": sorted_platforms,
            "total_queries": plan["total_queries"],
            "raw_results": len(raw_results),
            "total_signals_scanned": len(raw_results),
            "buyers_found": len(leads),
            "rejected": len(rejected),
            "confidence_floor": CONFIDENCE_FLOOR,
            "top_sources": self._count_sources(leads)
        }

        response = {
            "results": leads,
            "leads": leads,
            "metrics": metrics,
            "count": len(leads),
            "total_signals_captured": len(raw_results),
            "total_signals_scanned": len(raw_results),
            "buyers_found": len(leads),
            "category": plan["category"],
            "rejected_sample": rejected[:5],
            "status": "success" if leads else "no_results",
            "message": (
                f"Found {len(leads)} potential buyers across {len(sorted_platforms)} platforms"
                if leads else
                f"No buyers found for '{query}'. Try broader terms."
            )
        }

        if leads:
            cache.set(cache_key, response, ttl_seconds=1200)

        logger.info(f"🏁 {len(leads)} leads, {len(rejected)} rejected")
        logger.info(f"ENGINE_RETURNING: {len(leads)} leads")
        logger.info(f"ENGINE_STATUS: {response['status']}")
        return response
        
        except Exception as e:
            import traceback
            logger.error(f"ENGINE_ERROR: {str(e)}")
            logger.error(f"ENGINE_TRACEBACK: {traceback.format_exc()}")
            return {
                "results": [],
                "leads": [],
                "metrics": {"error": str(e)},
                "count": 0,
                "total_signals_captured": 0,
                "total_signals_scanned": 0,
                "buyers_found": 0,
                "status": "error",
                "message": f"Search engine error: {str(e)}"
            }

    def _high_intent_ddg_fallback(self, query: str, location: str) -> List[Dict[str, Any]]:
        """
        Last-resort buyer probe using explicit buyer-intent phrasing.
        Keeps the same precision + buyer gates to avoid seller noise.
        """
        if DDGS is None:
            return []

        probes = [
            f'"looking for" "{query}" "{location}"',
            f'"want to buy" "{query}" "{location}"',
            f'"need to buy" "{query}" "{location}"',
            f'"wtb" "{query}" "{location}"',
            f'"natafuta" "{query}" "{location}"',
            f'"nahitaji" "{query}" "{location}"',
        ]
        leads: List[Dict[str, Any]] = []
        seen_urls = set()

        try:
            with DDGS() as ddgs:
                for q in probes:
                    rows = list(ddgs.text(q, region="ke-en", timelimit="m", max_results=12))
                    for row in rows:
                        url = row.get("href", "")
                        if not url or url in seen_urls:
                            continue
                        seen_urls.add(url)
                        text = f"{row.get('title', '')} {row.get('body', '')}".strip()
                        raw = {
                            "url": url,
                            "source": "ddg_buyer_probe",
                            "title": row.get("title", ""),
                            "text": text,
                            "location": location,
                            "timestamp": datetime.now(timezone.utc).isoformat(),
                        }
                        signal = self.classifier.classify(text, "ddg_buyer_probe")
                        if not signal.is_buyer:
                            continue
                        if signal.confidence < CONFIDENCE_FLOOR:
                            continue
                        if not self._passes_precision_filter(raw, signal, query):
                            continue
                        if not is_valid_buyer(text, url):
                            continue
                        leads.append(self._build_lead(raw, signal, query))
                        if len(leads) >= 20:
                            return leads
        except Exception as e:
            logger.debug(f"High-intent DDG probe failed: {e}")

        return leads

    async def _fast_ddg_search(self, query: str, location: str) -> List[Dict[str, Any]]:
        """
        Fast DDG search that runs first to ensure we always get some results.
        Runs in thread pool to not block.
        """
        if DDGS is None:
            return []
        
        leads = []
        seen = set()
        
        try:
            loop = asyncio.get_event_loop()
            
            def do_ddg_search():
                results = []
                try:
                    with DDGS() as ddgs:
                        # Simple buyer-focused query
                        ddg_query = f'"looking for" OR "want to buy" OR "natafuta" "{query}" "{location}"'
                        rows = list(ddgs.text(ddg_query, region="ke-en", timelimit="m", max_results=10))
                        
                        for row in rows:
                            url = row.get("href", "")
                            if not url or url in seen:
                                continue
                            seen.add(url)
                            text = f"{row.get('title', '')} {row.get('body', '')}".strip()
                            results.append({
                                "url": url,
                                "source": "duckduckgo",
                                "title": row.get("title", ""),
                                "text": text,
                                "body": row.get("body", ""),
                                "location": location,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            })
                except Exception as e:
                    logger.debug(f"Fast DDG search error: {e}")
                return results
            
            # Run in thread with timeout
            leads = await asyncio.wait_for(
                loop.run_in_executor(None, do_ddg_search),
                timeout=8
            )
            logger.info(f"Fast DDG: {len(leads)} results")
            
        except asyncio.TimeoutError:
            logger.warning("Fast DDG search timed out")
        except Exception as e:
            logger.debug(f"Fast DDG search failed: {e}")
        
        return leads

    async def search_with_telegram(self, query, location="Kenya",
                                     include_telegram=True,
                                     telegram_hours_back=24, **kwargs):
        """Enhanced search with Telegram results merged in."""
        import asyncio

        # KENYA-ONLY VALIDATION
        if not self._validate_kenya_location(location):
            logger.warning(f"🚫 KENYA-ONLY POLICY: Rejected location '{location}'")
            return {
                "results": [],
                "leads": [],
                "metrics": {"error": f"Location '{location}' not supported. Kenya only.", "kenya_only": True},
                "count": 0,
                "status": "kenya_only_policy",
                "message": f"Location '{location}' is not supported. This system only supports Kenya locations."
            }

        # Wrap search in try/except to catch actual errors
        async def safe_search():
            try:
                return await self.search(query, location, **kwargs)
            except Exception as e:
                logger.error(f"Search failed with error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Return empty result instead of crashing
                return {
                    "results": [],
                    "leads": [],
                    "metrics": {"error": str(e)},
                    "count": 0,
                    "status": "error",
                    "message": f"Search error: {str(e)}"
                }

        tasks = [safe_search()]

        if include_telegram:
            try:
                from app.telegram.service import TELEGRAM_SERVICE
                if TELEGRAM_SERVICE.is_available:
                    category = self.query_engine.detect_category(query)
                    tasks.append(
                        TELEGRAM_SERVICE.search_buyers(
                            query=query, category=category,
                            hours_back=telegram_hours_back, max_groups=10
                        )
                    )
            except ImportError:
                pass

        results = await asyncio.gather(*tasks, return_exceptions=True)

        web_error = None
        if isinstance(results[0], Exception):
            web_error = str(results[0])
            web_result = {
                "results": [],
                "leads": [],
                "metrics": {"error": web_error},
                "count": 0,
                "status": "error",
                "message": "Web search failed"
            }
        else:
            web_result = results[0]

        telegram_leads = []
        if len(results) > 1 and not isinstance(results[1], Exception):
            telegram_leads = results[1]

        if include_telegram and not telegram_leads:
            telegram_leads = self._telegram_web_fallback(query, location)

        all_leads = list(web_result.get("results", []))
        for tl in telegram_leads:
            tl["_from_telegram"] = True
            tl["source_reliability"] = SOURCE_RELIABILITY.get("telegram", 0.95)
            all_leads.append(tl)

        # Re-sort with Telegram leads included
        all_leads.sort(key=lambda x: (
            x.get("source_reliability", 0.5) * 0.3 +
            x.get("intent_score", 0) * 0.4 +
            x.get("urgency_score", 0) * 0.15 +
            x.get("confidence", 0) * 0.15
        ), reverse=True)

        web_result["results"] = all_leads
        web_result["leads"] = all_leads
        web_result["count"] = len(all_leads)
        metrics = web_result.get("metrics", {})
        metrics["telegram_results"] = len(telegram_leads)
        if web_error:
            metrics["web_error"] = web_error
        web_result["metrics"] = metrics
        web_result["status"] = "success" if all_leads else web_result.get("status", "no_results")
        if all_leads:
            web_result["message"] = (
                f"Found {len(all_leads)} buyers "
                f"({len(telegram_leads)} from Telegram)"
            )
        else:
            web_result["message"] = web_result.get(
                "message",
                f"No buyers found for '{query}'. Try broader terms."
            )

        return web_result

    def _telegram_web_fallback(self, query: str, location: str) -> List[Dict[str, Any]]:
        """
        Lightweight fallback when Telegram API polling yields zero results.
        Uses web-discoverable t.me pages to recover likely buyer posts.
        """
        if DDGS is None:
            return []

        leads: List[Dict[str, Any]] = []
        seen = set()
        ddg_query = (
            f'site:t.me "{query}" "{location}" '
            f'("looking for" OR "want to buy" OR "need" OR "wtb" OR "natafuta" OR "nahitaji")'
        )

        try:
            with DDGS() as ddgs:
                rows = list(ddgs.text(ddg_query, region="ke-en", timelimit="w", max_results=8))
            for row in rows:
                url = row.get("href", "")
                if not url or url in seen:
                    continue
                seen.add(url)
                text = f"{row.get('title', '')} {row.get('body', '')}".strip()
                if not is_valid_buyer(text, url):
                    continue
                signal = self.classifier.classify(text, "telegram")
                if not signal.is_buyer:
                    continue
                raw = {
                    "url": url,
                    "source": "telegram",
                    "title": row.get("title", ""),
                    "text": text,
                    "location": location,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
                leads.append(self._build_lead(raw, signal, query))
        except Exception as e:
            logger.debug(f"Telegram web fallback failed: {e}")

        return leads

    def _passes_precision_filter(self, raw: Dict[str, Any], signal, query: str) -> bool:
        """
        Strict buyer precision gate:
        - Must match searched product terms
        - Must show explicit buyer intent (not informational/seller copy)
        - Must reject generic directory/info pages
        """
        title = (raw.get("title") or "").lower()
        text = (raw.get("text") or "").lower()
        url = (raw.get("url") or "").lower()
        haystack = f"{title} {text} {url}"

        # 1) Exact product relevance
        product_terms = self._extract_product_terms(query)
        has_product_match = any(term in haystack for term in product_terms)
        if not has_product_match:
            return False

        # 2) Explicit buyer intent only (avoid second-person marketing copy)
        if (
            "are you looking for" in haystack
            or "looking for information" in haystack
            or re.search(r"\b(if\s+)?you(\s+are|\s*'re)?\s+looking\s+for\b", haystack)
        ):
            return False
        buyer_cues = [
            "looking to buy", "want to buy", "need to buy", "wtb", "wanted",
            "where can i buy", "ready to buy", "cash buyer",
            "natafuta", "nahitaji", "nataka kununua", "ninatafuta",
            "my budget", "budget is"
        ]
        has_explicit_buyer_cue = any(cue in haystack for cue in buyer_cues)
        has_first_person = bool(
            re.search(r"\b(i|i'm|im|my|me|we|our|natafuta|nahitaji|nataka|ninatafuta)\b", haystack)
        )
        has_buyer_cue = has_explicit_buyer_cue or (has_first_person and "looking for" in haystack)
        if not has_buyer_cue:
            return False

        # 3) Remove seller/listing/directory noise
        listing_noise_terms = [
            "classifieds", "marketplace", "shop", "category", "product",
            "for sale", "for rent", "listing", "order now", "add to cart", "checkout"
        ]
        listing_noise_paths = ["/tag/", "/category/", "/product/", "/shop/", "/search?"]
        is_listing_noise = (
            any(term in haystack for term in listing_noise_terms) or
            any(path in url for path in listing_noise_paths)
        )

        # 4) Drop informational/travel/general pages that are not buyer requests
        info_noise_terms = [
            "things to do", "tripadvisor", "attractions", "travel guide", "hotel",
            "price guide", "best electronics shops", "forum rules", "wikipedia"
        ]
        if any(term in haystack for term in info_noise_terms):
            return False

        # 5) Hard reject seller-promotional and hiring content
        seller_promo_terms = [
            "looking for your perfect", "book an inspection", "check out this",
            "visit our showroom", "call us", "dm for price", "official dealer",
            "stock available", "we supply", "we sell", "available now"
        ]
        hiring_terms = [
            "job", "hiring", "vacancy", "apply now", "career", "recruit",
            "parts advisor", "store clerk"
        ]
        if any(term in haystack for term in seller_promo_terms):
            return False
        if any(term in haystack for term in hiring_terms):
            return False
        if "/reel/" in url or "/jobs/" in url or "job-" in url:
            return False

        # 6) Enforce geo relevance using content only (not raw.location, which may be defaulted).
        requested_loc = (raw.get("location") or "").lower()
        geo_context = f"{title} {text} {url}"
        foreign_markers = [
            "tanzania", "uganda", "nigeria", "ghana", "zambia", "india", "pakistan",
            "usa", "united states", "uk", "united kingdom", ".co.tz", ".co.ug", ".co.in",
        ]
        kenya_markers = [
            "kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret",
            ".co.ke", "countryke", "ksh", "kes", "+254"
        ]
        if any(marker in geo_context for marker in foreign_markers) and not any(
            marker in geo_context for marker in kenya_markers
        ):
            return False
        # Kenya query safety: require at least one Kenya-local signal to avoid irrelevant global chatter.
        if ("kenya" in requested_loc or requested_loc == "") and not any(
            marker in geo_context for marker in kenya_markers
        ):
            # Allow posts with Kenyan phone style even if marker words are absent.
            if not re.search(r"(\+254|(?:\b0[17]\d{8}\b))", geo_context):
                return False

        has_contact = bool(getattr(signal, "phone", "") or getattr(signal, "email", ""))
        if is_listing_noise and not has_contact:
            return False
        if signal.intent_score < 0.2:
            return False
        return True

    def _extract_product_terms(self, query: str) -> List[str]:
        """Extract product-focused unigram/bigram terms from the search query."""
        q = query.lower()
        tokens = re.findall(r"[a-z0-9]+", q)
        stop = {
            "looking", "for", "to", "buy", "want", "need", "wanted", "wtb",
            "ready", "cash", "budget", "urgent", "urgently", "where", "can",
            "i", "we", "my", "our", "anyone", "selling", "who", "has",
            "in", "at", "near", "the", "a", "an", "and", "or", "with", "from",
            "kenya", "nairobi", "mombasa", "kisumu", "nakuru", "eldoret",
            "ref", "gate", "pass2", "gate2", "gate3"
        }
        core = [t for t in tokens if len(t) >= 3 and t not in stop]
        terms = list(core)
        for i in range(len(core) - 1):
            terms.append(f"{core[i]} {core[i+1]}")
        return list(dict.fromkeys(terms))

    def _build_lead(self, raw, signal, query):
        """Build frontend-ready lead dict."""
        url = raw.get("url", "")
        source = raw.get("source", "")
        title = raw.get("title", "")
        text = raw.get("text", "")
        source_rel = SOURCE_RELIABILITY.get(source.lower(), 0.5)

        phone = signal.phone or ""
        email = signal.email or ""
        location = signal.location or raw.get("location", "Kenya")

        whatsapp_url = signal.whatsapp or ""
        if phone and not whatsapp_url:
            clean = phone.replace("+", "").replace(" ", "").replace("-", "")
            if clean.startswith("0"):
                clean = "254" + clean[1:]
            whatsapp_url = f"https://wa.me/{clean}"

        ranked_score = round(
            signal.intent_score * 0.35 +
            signal.urgency_score * 0.20 +
            signal.confidence * 0.20 +
            source_rel * 0.25,
            3
        )

        if signal.intent_score > 0.7 and signal.urgency_score > 0.6:
            badge = "HOT"
        elif signal.intent_score > 0.4 or signal.confidence > 0.4:
            badge = "WARM"
        else:
            badge = "COLD"

        return {
            "id": hashlib.md5(url.encode()).hexdigest()[:16],
            "buyer_name": signal.buyer_name,
            "title": title[:200] if title else text[:200],
            "price": signal.budget or "Contact for Price",
            "location": location,
            "phone": phone, "contact_phone": phone,
            "email": email, "contact_email": email,
            "source": source, "url": url, "source_url": url,
            "intent_score": signal.intent_score,
            "intent_strength": signal.intent_score,
            "buyer_match_score": ranked_score,
            "confidence": signal.confidence,
            "confidence_score": signal.confidence,
            "urgency_score": signal.urgency_score,
            "ranked_score": ranked_score, "rank_score": ranked_score,
            "source_reliability": source_rel,
            "buyer_request_snippet": signal.specific_need[:500],
            "buyer_intent_quote": signal.specific_need[:300],
            "snippet": signal.specific_need[:300],
            "intent": signal.specific_need[:200],
            "market_side": "demand",
            "badge": badge,
            "verification_flag": "verified" if phone else "unverified",
            "intent_type": "BUYER",
            "persona": signal.persona,
            "timeline": signal.timeline,
            "status": "NEW",
            "is_hot_lead": badge == "HOT",
            "geo_score": 1.0 if signal.location else 0.5,
            "geo_strength": "high" if signal.location else "medium",
            "geo_region": location,
            "whatsapp_url": whatsapp_url, "whatsapp_link": whatsapp_url,
            "created_at": raw.get("timestamp", datetime.now(timezone.utc).isoformat()),
            "query": query, "product": title or query,
            "score_details": signal.score_details,
            "ui_filter_status": "shown", "tap_count": 0
        }

    def _count_sources(self, leads):
        counts = {}
        for lead in leads:
            source = lead.get("source", "unknown")
            counts[source] = counts.get(source, 0) + 1
        return dict(sorted(counts.items(), key=lambda x: x[1], reverse=True))


SEARCH_ENGINE = SearchEngine()
