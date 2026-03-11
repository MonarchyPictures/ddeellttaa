"""
DELTA-9 HARDENED SCRAPER BASE CLASS
Production-grade scraper with health monitoring and heartbeat

All scrapers must inherit from this base class.
Provides:
- Automatic heartbeat generation
- Health monitoring integration
- Error recovery
- Rate limiting
- Lead pipeline integration
"""

import asyncio
import logging
import time
import traceback
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Optional, Any, AsyncGenerator
from dataclasses import dataclass
import psutil

from app.core.system_guardian import SystemGuardian, ScraperHeartbeat, get_guardian
from app.pipeline.lead_pipeline import LeadPipeline, PipelineResult, get_pipeline

logger = logging.getLogger(__name__)


@dataclass
class ScraperConfig:
    """Scraper configuration"""
    scraper_id: str
    platform: str  # telegram, facebook, jiji, etc.
    query: str
    interval_seconds: int = 300  # 5 minutes default
    max_leads_per_run: int = 100
    timeout_seconds: int = 60
    retry_attempts: int = 3
    rate_limit_per_minute: int = 30


@dataclass
class RawLead:
    """Raw lead data from scraper"""
    text: str
    source_platform: str
    source_name: str
    source_url: str
    timestamp: datetime
    location: str = "Kenya"
    phone: Optional[str] = None
    query: str = ""
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class HardenedScraper(ABC):
    """
    Production-grade scraper base class
    
    Features:
    - Heartbeat monitoring
    - Automatic error recovery
    - Rate limiting
    - Lead pipeline integration
    - Health check integration
    """
    
    def __init__(self, config: ScraperConfig):
        self.config = config
        self.running = False
        self.leads_collected = 0
        self.errors_count = 0
        self.last_run: Optional[datetime] = None
        self.last_heartbeat: Optional[datetime] = None
        
        # Integrations
        self.guardian = get_guardian()
        self.pipeline = get_pipeline()
        
        # Rate limiting
        self.request_times: List[float] = []
        
        # Register with guardian
        self.guardian.register_service(
            config.scraper_id,
            self.restart,
            {'platform': config.platform, 'query': config.query}
        )
        
        logger.info(f"🔧 Scraper initialized: {config.scraper_id} ({config.platform})")
    
    @abstractmethod
    async def scrape(self) -> AsyncGenerator[RawLead, None]:
        """
        Main scraping method - must be implemented by subclass
        
        Yields RawLead objects
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if scraper can access its source
        Returns True if healthy
        """
        pass
    
    async def start(self):
        """Start the scraper loop"""
        if self.running:
            return
        
        self.running = True
        logger.info(f"🚀 Starting scraper: {self.config.scraper_id}")
        
        try:
            while self.running:
                try:
                    await self._run_once()
                except Exception as e:
                    logger.error(f"Scraper error: {str(e)}", exc_info=True)
                    self.errors_count += 1
                    await self._handle_error(e)
                
                # Wait before next run
                await asyncio.sleep(self.config.interval_seconds)
        
        except asyncio.CancelledError:
            logger.info(f"⏹️ Scraper cancelled: {self.config.scraper_id}")
        
        finally:
            self.running = False
    
    def stop(self):
        """Stop the scraper"""
        self.running = False
        logger.info(f"⏹️ Stopping scraper: {self.config.scraper_id}")
    
    def restart(self):
        """Restart the scraper (called by guardian)"""
        logger.info(f"🔄 Restarting scraper: {self.config.scraper_id}")
        self.stop()
        time.sleep(2)
        self.errors_count = 0
        asyncio.create_task(self.start())
    
    async def _run_once(self):
        """Execute one scraping run"""
        self.last_run = datetime.utcnow()
        
        # Check rate limit
        if not self._check_rate_limit():
            logger.warning(f"Rate limit hit for {self.config.scraper_id}")
            return
        
        # Pre-flight health check
        if not await self.health_check():
            logger.error(f"Health check failed for {self.config.scraper_id}")
            self.errors_count += 1
            return
        
        leads_this_run = 0
        
        try:
            async for raw_lead in self.scrape():
                if not self.running:
                    break
                
                # Add query context
                raw_lead.query = self.config.query
                
                # Process through pipeline
                result = await self._process_lead(raw_lead)
                
                if result.success:
                    self.leads_collected += 1
                    leads_this_run += 1
                    logger.info(f"✅ Lead accepted: {result.lead.phone}")
                else:
                    logger.debug(f"❌ Lead rejected: {result.rejection_reason}")
                
                # Send heartbeat periodically
                if leads_this_run % 5 == 0:
                    self._send_heartbeat()
                
                # Limit per run
                if leads_this_run >= self.config.max_leads_per_minute:
                    logger.info(f"Max leads reached for {self.config.scraper_id}")
                    break
        
        except Exception as e:
            logger.error(f"Scrape error: {str(e)}", exc_info=True)
            raise
        
        finally:
            self._send_heartbeat()
            logger.info(f"📊 Run complete: {self.config.scraper_id} collected {leads_this_run} leads")
    
    async def _process_lead(self, raw_lead: RawLead) -> PipelineResult:
        """Process raw lead through pipeline"""
        # Convert RawLead to dict for pipeline
        lead_data = {
            'text': raw_lead.text,
            'source_platform': raw_lead.source_platform,
            'source_name': raw_lead.source_name,
            'source_url': raw_lead.source_url,
            'timestamp': raw_lead.timestamp,
            'location': raw_lead.location,
            'phone': raw_lead.phone,
            'query': raw_lead.query,
            **raw_lead.metadata
        }
        
        return self.pipeline.process(lead_data)
    
    def _send_heartbeat(self):
        """Send heartbeat to guardian"""
        process = psutil.Process()
        
        heartbeat = ScraperHeartbeat(
            scraper_id=self.config.scraper_id,
            status="running" if self.running else "stopped",
            leads_collected=self.leads_collected,
            last_run=self.last_run or datetime.utcnow(),
            errors=self.errors_count,
            memory_mb=process.memory_info().rss / 1024 / 1024,
            cpu_percent=process.cpu_percent()
        )
        
        self.guardian.record_heartbeat(heartbeat)
        self.last_heartbeat = datetime.utcnow()
    
    def _check_rate_limit(self) -> bool:
        """Check if within rate limit"""
        now = time.time()
        
        # Remove old requests (older than 1 minute)
        cutoff = now - 60
        self.request_times = [t for t in self.request_times if t > cutoff]
        
        # Check limit
        if len(self.request_times) >= self.config.rate_limit_per_minute:
            return False
        
        # Record this request
        self.request_times.append(now)
        return True
    
    async def _handle_error(self, error: Exception):
        """Handle scraper error"""
        error_type = type(error).__name__
        
        logger.error(f"Error in {self.config.scraper_id}: {error_type}: {str(error)}")
        
        # Implement exponential backoff
        if self.errors_count > self.config.retry_attempts:
            logger.critical(f"Max retries exceeded for {self.config.scraper_id}")
            self.stop()
            return
        
        # Wait before retry
        wait_time = min(2 ** self.errors_count, 60)
        logger.info(f"Waiting {wait_time}s before retry...")
        await asyncio.sleep(wait_time)


class TelegramScraper(HardenedScraper):
    """Example implementation for Telegram"""
    
    async def scrape(self) -> AsyncGenerator[RawLead, None]:
        """Scrape Telegram groups for buyer posts"""
        # This would integrate with real Telegram MTProto client
        # For now, placeholder
        logger.info(f"Scraping Telegram for: {self.config.query}")
        
        # Simulate finding posts
        # In production, this would use telethon or similar
        yield RawLead(
            text="Looking for Toyota Vitz in Nairobi, budget ready. Call 0712345678",
            source_platform="telegram",
            source_name="Kenya Car Buyers",
            source_url="https://t.me/kenya_cars/12345",
            timestamp=datetime.utcnow(),
            location="Nairobi",
            query=self.config.query
        )
    
    async def health_check(self) -> bool:
        """Check Telegram connection"""
        # Would check Telegram API connectivity
        return True


class JijiScraper(HardenedScraper):
    """Example implementation for Jiji"""
    
    async def scrape(self) -> AsyncGenerator[RawLead, None]:
        """Scrape Jiji.co.ke for buyer requests"""
        logger.info(f"Scraping Jiji for: {self.config.query}")
        
        # In production, would use requests/Playwright to scrape
        yield RawLead(
            text="Natafuta Toyota Vitz 2015. Budget iko. 0723456789",
            source_platform="jiji",
            source_name="Jiji Kenya",
            source_url="https://jiji.co.ke/nairobi/cars/toyota-vitz",
            timestamp=datetime.utcnow(),
            location="Nairobi",
            query=self.config.query
        )
    
    async def health_check(self) -> bool:
        """Check Jiji website accessibility"""
        # Would check HTTP connectivity to jiji.co.ke
        return True


class RedditScraper(HardenedScraper):
    """Example implementation for Reddit"""
    
    async def scrape(self) -> AsyncGenerator[RawLead, None]:
        """Scrape Reddit for buyer posts"""
        logger.info(f"Scraping Reddit for: {self.config.query}")
        
        # In production, would use PRAW
        yield RawLead(
            text="[WANT] Looking for iPhone 14 Pro in Nairobi. PM me 0734567890",
            source_platform="reddit",
            source_name="r/KenyaMarket",
            source_url="https://reddit.com/r/KenyaMarket/comments/abc123",
            timestamp=datetime.utcnow(),
            location="Nairobi",
            query=self.config.query
        )
    
    async def health_check(self) -> bool:
        """Check Reddit API connectivity"""
        return True
