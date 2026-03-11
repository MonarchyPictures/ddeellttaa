"""
DELTA-9 STARTUP SEQUENCE
Initializes all system components in the correct order
"""

import asyncio
import logging
import signal
import sys
from contextlib import asynccontextmanager

from app.core.system_guardian import get_guardian, SystemGuardian
from app.core.logging_system import StructuredLogger
from app.pipeline.lead_pipeline import get_pipeline, LeadPipeline
from app.scrapers.scraper_orchestrator import get_orchestrator, ScraperOrchestrator
from app.services.deduplication_service import get_dedupe_service, DeduplicationService

logger = StructuredLogger("startup")


class Delta9Application:
    """
    Main application lifecycle manager
    
    Handles startup, shutdown, and component coordination
    """
    
    def __init__(self):
        self.guardian: SystemGuardian = None
        self.pipeline: LeadPipeline = None
        self.orchestrator: ScraperOrchestrator = None
        self.dedupe: DeduplicationService = None
        self.running = False
        
        # Setup signal handlers
        signal.signal(signal.SIGTERM, self._signal_handler)
        signal.signal(signal.SIGINT, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.running = False
    
    async def startup(self):
        """
        Initialize all components
        
        Startup sequence:
        1. Logging system
        2. Deduplication service
        3. Lead pipeline
        4. System guardian
        5. Scraper orchestrator
        """
        logger.info("🚀 DELTA-9 STARTUP SEQUENCE INITIATED")
        logger.info("=" * 50)
        
        try:
            # Step 1: Initialize deduplication
            logger.info("[1/5] Initializing deduplication service...")
            self.dedupe = get_dedupe_service()
            logger.info("✅ Deduplication service ready")
            
            # Step 2: Initialize pipeline
            logger.info("[2/5] Initializing lead pipeline...")
            self.pipeline = get_pipeline()
            logger.info("✅ Lead pipeline ready")
            
            # Step 3: Initialize guardian
            logger.info("[3/5] Initializing system guardian...")
            self.guardian = get_guardian()
            self.guardian.start()
            logger.info("✅ System guardian started")
            
            # Step 4: Initialize orchestrator
            logger.info("[4/5] Initializing scraper orchestrator...")
            self.orchestrator = get_orchestrator()
            logger.info("✅ Scraper orchestrator ready")
            
            # Step 5: Start monitoring queries
            logger.info("[5/5] Starting query monitoring...")
            await self._start_default_queries()
            logger.info("✅ Query monitoring started")
            
            self.running = True
            logger.info("=" * 50)
            logger.info("🎉 DELTA-9 STARTUP COMPLETE")
            logger.info("All systems operational")
            
            return True
            
        except Exception as e:
            logger.critical(f"💥 STARTUP FAILED: {str(e)}", exc_info=True)
            await self.shutdown()
            return False
    
    async def _start_default_queries(self):
        """Start monitoring default queries"""
        default_queries = [
            "toyota vitz",
            "plumber",
            "iphone",
            "house for rent",
            "tires",
        ]
        
        for query in default_queries:
            try:
                await self.orchestrator.start_query(query)
                logger.info(f"  📡 Monitoring: {query}")
            except Exception as e:
                logger.error(f"Failed to start query '{query}': {e}")
    
    async def run(self):
        """Main run loop"""
        if not await self.startup():
            return 1
        
        # Keep running until shutdown signal
        try:
            while self.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        
        await self.shutdown()
        return 0
    
    async def shutdown(self):
        """Graceful shutdown"""
        logger.info("🛑 DELTA-9 SHUTDOWN INITIATED")
        
        # Stop orchestrator
        if self.orchestrator:
            logger.info("Stopping scraper orchestrator...")
            await self.orchestrator.shutdown()
        
        # Stop guardian
        if self.guardian:
            logger.info("Stopping system guardian...")
            self.guardian.stop()
        
        logger.info("👋 DELTA-9 SHUTDOWN COMPLETE")


@asynccontextmanager
async def lifespan(app):
    """
    FastAPI lifespan manager
    
    Usage:
        app = FastAPI(lifespan=lifespan)
    """
    # Startup
    delta9 = Delta9Application()
    success = await delta9.startup()
    
    if not success:
        raise RuntimeError("Delta-9 startup failed")
    
    # Store in app state
    app.state.delta9 = delta9
    
    yield
    
    # Shutdown
    await delta9.shutdown()


async def main():
    """Entry point for running Delta-9 standalone"""
    app = Delta9Application()
    exit_code = await app.run()
    sys.exit(exit_code)


if __name__ == "__main__":
    asyncio.run(main())
