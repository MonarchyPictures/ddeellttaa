"""
DELTA-9 SCRAPER ORCHESTRATOR
Manages all scrapers and coordinates lead collection

Responsibilities:
- Start/stop scrapers based on queries
- Monitor scraper health
- Distribute queries across scrapers
- Handle scraper lifecycle
- Aggregate lead streams
"""

import asyncio
import logging
from typing import Dict, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from app.scrapers.base_hardened import (
    HardenedScraper, TelegramScraper, JijiScraper, RedditScraper,
    ScraperConfig, RawLead
)
from app.core.system_guardian import get_guardian

logger = logging.getLogger(__name__)


@dataclass
class ActiveQuery:
    """Active query being monitored"""
    query: str
    scrapers: List[str]
    started_at: datetime
    leads_collected: int = 0


class ScraperOrchestrator:
    """
    Central orchestrator for all scrapers
    
    Manages:
    - Multiple concurrent scrapers
    - Query distribution
    - Resource allocation
    - Lead aggregation
    """
    
    def __init__(self):
        self.scrapers: Dict[str, HardenedScraper] = {}
        self.active_queries: Dict[str, ActiveQuery] = {}
        self.running_tasks: Dict[str, asyncio.Task] = {}
        self.guardian = get_guardian()
        
        # Statistics
        self.total_leads = 0
        self.started_at = datetime.utcnow()
        
        logger.info("🎼 Scraper Orchestrator initialized")
    
    def create_scrapers_for_query(self, query: str) -> List[HardenedScraper]:
        """
        Create scraper instances for a query across all platforms
        
        Args:
            query: Search query (e.g., "toyota vitz", "plumber")
            
        Returns:
            List of configured scraper instances
        """
        scrapers = []
        
        # Define platforms and their configurations
        platforms = [
            {
                'id': f'telegram_{query.replace(" ", "_")}',
                'platform': 'telegram',
                'class': TelegramScraper,
                'interval': 300  # 5 min
            },
            {
                'id': f'jiji_{query.replace(" ", "_")}',
                'platform': 'jiji',
                'class': JijiScraper,
                'interval': 600  # 10 min
            },
            {
                'id': f'reddit_{query.replace(" ", "_")}',
                'platform': 'reddit',
                'class': RedditScraper,
                'interval': 900  # 15 min
            },
        ]
        
        for plat in platforms:
            config = ScraperConfig(
                scraper_id=plat['id'],
                platform=plat['platform'],
                query=query,
                interval_seconds=plat['interval']
            )
            
            scraper = plat['class'](config)
            scrapers.append(scraper)
        
        return scrapers
    
    async def start_query(self, query: str) -> ActiveQuery:
        """
        Start monitoring a query across all platforms
        
        Args:
            query: Search query to monitor
            
        Returns:
            ActiveQuery object
        """
        if query in self.active_queries:
            logger.warning(f"Query already active: {query}")
            return self.active_queries[query]
        
        logger.info(f"🚀 Starting query monitoring: {query}")
        
        # Create scrapers
        scrapers = self.create_scrapers_for_query(query)
        scraper_ids = []
        
        for scraper in scrapers:
            self.scrapers[scraper.config.scraper_id] = scraper
            scraper_ids.append(scraper.config.scraper_id)
            
            # Start scraper as background task
            task = asyncio.create_task(
                self._run_scraper_with_recovery(scraper),
                name=scraper.config.scraper_id
            )
            self.running_tasks[scraper.config.scraper_id] = task
        
        # Track active query
        active = ActiveQuery(
            query=query,
            scrapers=scraper_ids,
            started_at=datetime.utcnow()
        )
        self.active_queries[query] = active
        
        logger.info(f"✅ Query started: {query} with {len(scrapers)} scrapers")
        return active
    
    async def stop_query(self, query: str):
        """Stop monitoring a query"""
        if query not in self.active_queries:
            logger.warning(f"Query not active: {query}")
            return
        
        logger.info(f"⏹️ Stopping query: {query}")
        
        active = self.active_queries[query]
        
        # Stop all scrapers for this query
        for scraper_id in active.scrapers:
            if scraper_id in self.scrapers:
                self.scrapers[scraper_id].stop()
                del self.scrapers[scraper_id]
            
            # Cancel task
            if scraper_id in self.running_tasks:
                task = self.running_tasks[scraper_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.running_tasks[scraper_id]
        
        del self.active_queries[query]
        logger.info(f"✅ Query stopped: {query}")
    
    async def _run_scraper_with_recovery(self, scraper: HardenedScraper):
        """Run scraper with automatic recovery"""
        scraper_id = scraper.config.scraper_id
        
        while True:
            try:
                await scraper.start()
            except asyncio.CancelledError:
                logger.info(f"Scraper cancelled: {scraper_id}")
                break
            except Exception as e:
                logger.error(f"Scraper crashed: {scraper_id} - {str(e)}")
                
                # Wait before restart
                await asyncio.sleep(10)
                
                # Restart if not explicitly stopped
                if scraper.running:
                    logger.info(f"Restarting scraper: {scraper_id}")
                    continue
                else:
                    break
    
    def get_stats(self) -> Dict:
        """Get orchestrator statistics"""
        return {
            'active_queries': len(self.active_queries),
            'active_scrapers': len(self.scrapers),
            'running_tasks': len(self.running_tasks),
            'total_leads': self.total_leads,
            'uptime_seconds': (datetime.utcnow() - self.started_at).total_seconds(),
            'queries': [
                {
                    'query': q.query,
                    'scrapers': len(q.scrapers),
                    'leads': q.leads_collected,
                    'duration_minutes': (datetime.utcnow() - q.started_at).total_seconds() / 60
                }
                for q in self.active_queries.values()
            ]
        }
    
    def get_scraper_status(self) -> List[Dict]:
        """Get status of all scrapers"""
        status = []
        
        for scraper_id, scraper in self.scrapers.items():
            guardian_health = self.guardian.get_service_health(scraper_id)
            
            status.append({
                'id': scraper_id,
                'platform': scraper.config.platform,
                'running': scraper.running,
                'leads_collected': scraper.leads_collected,
                'errors': scraper.errors_count,
                'last_run': scraper.last_run.isoformat() if scraper.last_run else None,
                'last_heartbeat': scraper.last_heartbeat.isoformat() if scraper.last_heartbeat else None,
                'health': guardian_health.status.value if guardian_health else 'unknown'
            })
        
        return status
    
    async def shutdown(self):
        """Graceful shutdown of all scrapers"""
        logger.info("🛑 Orchestrator shutting down...")
        
        # Stop all queries
        for query in list(self.active_queries.keys()):
            await self.stop_query(query)
        
        # Wait for all tasks
        if self.running_tasks:
            await asyncio.gather(*self.running_tasks.values(), return_exceptions=True)
        
        logger.info("✅ Orchestrator shutdown complete")


# Singleton instance
_orchestrator_instance = None

def get_orchestrator() -> ScraperOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator_instance
    if _orchestrator_instance is None:
        _orchestrator_instance = ScraperOrchestrator()
    return _orchestrator_instance
