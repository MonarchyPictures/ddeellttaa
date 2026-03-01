# app/services/deep_search_service.py
"""
DEEP SEARCH SERVICE — Anti-429 Hardened Background Mode
Discover Hidden Buyers (0.22 threshold)
20-60 seconds, 50+ leads
"""
import asyncio
import logging
from typing import List, Dict, Any
from datetime import datetime, timezone

from app.services.kenya_intent_engine import batch_score_leads, get_threshold_for_mode
from app.services.parallel_scraper_runner import run_scrapers_parallel
from app.services.lead_storage import save_leads_to_db_async
from app.services.search_config import SEARCH_CONFIG, get_intent_threshold
from app.services.rate_limiter import throttler, apply_delay

logger = logging.getLogger(__name__)

# Track deep search jobs
DEEP_SEARCH_JOBS: Dict[str, Dict] = {}

# Anti-429: Heavy scrapers with delays
HEAVY_SCRAPER_NAMES = [
    'TelegramScraper',
    'FacebookMarketplaceScraper',
    'TwitterScraper',
    'KenyanForumsScraper',
    'JijiScraper',
    'PigiameScraper',
    'GoogleMapsScraper'
]

# Anti-429: Lower concurrency for heavy scrapers
MAX_CONCURRENT_DEEP = 2


def get_deep_scrapers(all_scrapers: List) -> List:
    """Get heavy browser-based scrapers."""
    scrapers = [s for s in all_scrapers if any(name in s.__class__.__name__ for name in HEAVY_SCRAPER_NAMES)]
    return scrapers[:5]  # Anti-429: Max 5 scrapers


def generate_deep_queries(product: str, location: str) -> List[str]:
    """
    Anti-429: Moderate expansion (6 queries)
    Cast wide net but don't overload
    """
    return [
        f'"{product}" "{location}" (natafuta OR nahitaji OR "looking for" OR need OR wtb)',
        f'"{product}" "{location}" budget',
        f'site:t.me "{product}" "{location}"',
        f'site:facebook.com "{product}" "{location}" (natafuta OR "looking for")',
        f'site:jiji.co.ke "{product}" "{location}"',
        f'"{product}" "{location}" urgently',
    ]


async def run_deep_search(
    query: str,
    location: str,
    scrapers: List = None,
    all_scrapers: List = None,
    job_id: str = None
) -> Dict[str, Any]:
    """
    DEEP MODE: Background intelligence sweep with Anti-429 hardening.
    
    Anti-429 Measures:
    - Random delays between requests
    - Per-domain throttling
    - Lower concurrency (2)
    - Per-scraper delays (2-5s)
    - Jitter (0-0.5s)
    
    Intent Threshold: 0.22 (discover hidden buyers)
    Target Time: 20-60 seconds
    Target Leads: 50+
    """
    start_time = datetime.now(timezone.utc)
    intent_threshold = get_intent_threshold("deep")
    
    if scrapers is None and all_scrapers:
        scrapers = get_deep_scrapers(all_scrapers)
    
    if not scrapers:
        logger.warning("No deep scrapers available")
        return {"status": "no_scrapers", "leads_found": 0}
    
    if job_id:
        DEEP_SEARCH_JOBS[job_id] = {
            "status": "running",
            "started_at": start_time.isoformat(),
            "query": query,
            "location": location,
            "new_leads": [],
            "intent_threshold": intent_threshold
        }
    
    logger.info(f"🔍 DEEP: '{query}' | {len(scrapers)} scrapers | threshold: {intent_threshold}")
    
    # Generate queries
    deep_queries = generate_deep_queries(query, location)
    logger.info(f"Deep: {len(deep_queries)} queries × {len(scrapers)} scrapers (concurrency: {MAX_CONCURRENT_DEEP})")
    
    # Execute with Anti-429 throttling
    all_results = []
    semaphore = asyncio.Semaphore(MAX_CONCURRENT_DEEP)
    
    async def run_one(query: str, scraper) -> List[Dict]:
        async with semaphore:
            # Anti-429: Apply throttling
            scraper_name = scraper.__class__.__name__
            await throttler.throttle(scraper_name)
            
            # Anti-429: Random delay between requests
            await apply_delay(1.0, 3.0)
            
            try:
                return await run_scrapers_parallel([scraper], query, location, hours=48)
            except Exception as e:
                logger.error(f"Deep query failed: {e}")
                return []
    
    # Create tasks
    tasks = []
    for q in deep_queries:
        for scraper in scrapers:
            tasks.append(asyncio.create_task(run_one(q, scraper)))
    
    # Process all (no early stopping - we want everything)
    completed_tasks = await asyncio.gather(*tasks, return_exceptions=True)
    
    for result in completed_tasks:
        if isinstance(result, list):
            all_results.extend(result)
    
    logger.info(f"Deep raw: {len(all_results)} total results")
    
    # Score with Kenya Intent Engine (lower threshold for deep mode)
    scored_leads = batch_score_leads(all_results, location)
    deep_leads = [lead for lead in scored_leads if lead.get('intent_score', 0) >= intent_threshold]
    
    # Save to DB
    if deep_leads:
        saved_count = await save_leads_to_db_async(deep_leads, query)
        
        if job_id:
            DEEP_SEARCH_JOBS[job_id]["new_leads"] = deep_leads
            DEEP_SEARCH_JOBS[job_id]["status"] = "completed"
        
        logger.info(f"💾 Deep: Saved {saved_count}/{len(deep_leads)} leads (threshold: {intent_threshold})")
    
    duration = (datetime.now(timezone.utc) - start_time).total_seconds()
    logger.info(f"🔍 DEEP complete: {len(deep_leads)} leads in {duration:.1f}s")
    
    return {
        "job_id": job_id,
        "status": "completed",
        "raw_count": len(all_results),
        "leads_found": len(deep_leads),
        "intent_threshold": intent_threshold,
        "duration_seconds": duration
    }


def get_new_leads_since(query: str, since_timestamp: str) -> List[Dict]:
    """Poll for new leads from deep search."""
    for job_id, job in DEEP_SEARCH_JOBS.items():
        if job.get("query") == query and job.get("status") == "completed":
            return job.get("new_leads", [])
    return []


def get_deep_search_status(query: str) -> Dict:
    """Get deep search status."""
    for job_id, job in DEEP_SEARCH_JOBS.items():
        if job.get("query") == query:
            return {
                "job_id": job_id,
                "status": job.get("status"),
                "started_at": job.get("started_at"),
                "new_leads_count": len(job.get("new_leads", [])),
                "intent_threshold": job.get("intent_threshold", 0.22)
            }
    return {"status": "not_found"}
