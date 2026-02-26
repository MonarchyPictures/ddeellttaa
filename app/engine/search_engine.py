# app/engine/search_engine.py
# ============================================================
# SEARCH ENGINE — Updated with priority ordering + low confidence floor
# ============================================================

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
    CONFIDENCE_FLOOR, SCRAPER_PRIORITIES, SOURCE_RELIABILITY
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

    async def search(
        self,
        query: str,
        location: str = "Kenya",
        include_all: bool = False,
        min_score: float = 0.0,    # No minimum — confidence floor handles it
        allow_legacy_fallback: bool = True
    ) -> Dict[str, Any]:

        logger.info(f"🔍 ENGINE: '{query}' in '{location}'")

        # Cache
        cache_key = f"engine:v3:{hashlib.md5(f'{query}:{location}'.lower().encode()).hexdigest()}"
        cached = cache.get(cache_key)
        if cached:
            logger.info("✅ Cache hit")
            return cached

        # Generate search plan (platforms ordered by priority)
        plan = self.query_engine.generate_search_plan(query, location)

        # Sort platforms by priority from config
        sorted_platforms = sorted(
            plan.get("platforms", {}).keys(),
            key=lambda p: SCRAPER_PRIORITIES.get(p, 10),
            reverse=True
        )

        logger.info(f"📋 Platform order: {sorted_platforms}")

        # Reorder plan platforms
        ordered_platforms = {}
        for p in sorted_platforms:
            if p in plan["platforms"]:
                ordered_platforms[p] = plan["platforms"][p]
        plan["platforms"] = ordered_platforms

        # Execute search
        raw_results = await self.scraper.execute_search_plan(plan)
        logger.info(f"📊 Raw results: {len(raw_results)}")

        # Classify
        leads = []
        rejected = []
        seen_hashes = set()

        for raw in raw_results:
            text = raw.get("text", "")
            url = raw.get("url", "")
            source = raw.get("source", "")

            # Dedup
            text_hash = hashlib.md5(text.lower().strip()[:200].encode()).hexdigest()
            if text_hash in seen_hashes:
                continue
            seen_hashes.add(text_hash)

            # Classify
            # BuyerClassifier expects (text, source); passing url here raised runtime TypeError.
            signal = self.classifier.classify(text, source)

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

        # Metrics
        metrics = {
            "category": plan["category"],
            "platforms_searched": sorted_platforms,
            "platform_order": sorted_platforms,
            "total_queries": plan["total_queries"],
            "raw_results": len(raw_results),
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
        return response

    async def search_with_telegram(self, query, location="Kenya",
                                     include_telegram=True,
                                     telegram_hours_back=24, **kwargs):
        """Enhanced search with Telegram results merged in."""
        import asyncio

        tasks = [self.search(query, location, **kwargs)]

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
        Reduce listing/directory noise while preserving high recall across arbitrary products.
        """
        title = (raw.get("title") or "").lower()
        text = (raw.get("text") or "").lower()
        url = (raw.get("url") or "").lower()
        haystack = f"{title} {text} {url}"

        buyer_cues = [
            "looking for", "want to buy", "need", "wtb", "wanted",
            "natafuta", "nahitaji", "anyone selling", "where can i buy",
            "budget", "urgent"
        ]
        has_buyer_cue = any(cue in haystack for cue in buyer_cues)

        listing_noise_terms = [
            "classifieds", "marketplace", "shop", "category", "product",
            "for sale", "for rent", "listing"
        ]
        listing_noise_paths = ["/tag/", "/category/", "/product/", "/shop/", "/search?"]
        is_listing_noise = (
            any(term in haystack for term in listing_noise_terms) or
            any(path in url for path in listing_noise_paths)
        )

        query_tokens = [
            t for t in re.findall(r"[a-z0-9]+", query.lower())
            if len(t) >= 3 and t not in {"the", "for", "and", "with", "from", "kenya"}
        ]
        token_overlap = sum(1 for t in query_tokens if t in haystack)
        has_query_overlap = token_overlap >= max(1, min(2, len(query_tokens)))

        has_contact = bool(getattr(signal, "phone", "") or getattr(signal, "email", ""))
        if is_listing_noise and not has_buyer_cue and not has_contact and signal.intent_score < 0.65:
            return False
        if not has_query_overlap and signal.intent_score < 0.75:
            return False
        return True

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
