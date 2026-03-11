"""
DELTA-9 SYSTEM GUARDIAN
Self-healing watchdog service

Responsibilities:
1. Monitor scraper health (heartbeats)
2. Monitor database connectivity
3. Monitor pipeline performance
4. Detect failures and auto-recover
5. Restart stuck services
6. Alert on critical failures

Runs every 60 seconds
"""

import asyncio
import logging
import psutil
import time
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Callable
from dataclasses import dataclass, field
import threading
import os
import signal

logger = logging.getLogger(__name__)


class ServiceStatus(Enum):
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    DEAD = "dead"
    UNKNOWN = "unknown"


class GuardianAction(Enum):
    RESTART = "restart"
    FLUSH_QUEUE = "flush_queue"
    CLEAR_CACHE = "clear_cache"
    ALERT = "alert"
    NO_ACTION = "no_action"


@dataclass
class HealthCheck:
    """Health check result"""
    service: str
    status: ServiceStatus
    last_heartbeat: Optional[datetime] = None
    metrics: Dict = field(default_factory=dict)
    error_count: int = 0
    action_taken: Optional[str] = None


@dataclass
class ScraperHeartbeat:
    """Scraper heartbeat data"""
    scraper_id: str
    status: str
    leads_collected: int
    last_run: datetime
    errors: int = 0
    memory_mb: float = 0.0
    cpu_percent: float = 0.0


class SystemGuardian:
    """
    Production-grade self-healing system monitor
    
    Monitors all critical components and auto-recovers from failures
    """
    
    # Thresholds
    HEARTBEAT_TIMEOUT_SECONDS = 120  # 2 minutes
    MAX_QUEUE_SIZE = 10000
    MAX_MEMORY_PERCENT = 85
    MAX_CPU_PERCENT = 90
    MAX_ERROR_RATE = 10  # errors per minute
    
    def __init__(self, check_interval: int = 60):
        self.check_interval = check_interval
        self.running = False
        self.check_thread: Optional[threading.Thread] = None
        
        # Health tracking
        self.heartbeats: Dict[str, ScraperHeartbeat] = {}
        self.health_history: List[HealthCheck] = []
        self.max_history = 1000
        
        # Service registry
        self.registered_services: Dict[str, Dict] = {}
        self.restart_callbacks: Dict[str, Callable] = {}
        
        # Recovery tracking
        self.restart_count: Dict[str, int] = {}
        self.last_restart: Dict[str, datetime] = {}
        
        # Stats
        self.stats = {
            'checks_performed': 0,
            'failures_detected': 0,
            'auto_recovers': 0,
            'alerts_sent': 0
        }
        
        logger.info("🛡️ System Guardian initialized")
    
    def register_service(self, service_id: str, restart_callback: Callable,
                        metadata: Optional[Dict] = None):
        """Register a service for monitoring"""
        self.registered_services[service_id] = {
            'restart_callback': restart_callback,
            'metadata': metadata or {},
            'registered_at': datetime.utcnow()
        }
        self.restart_count[service_id] = 0
        logger.info(f"✅ Service registered: {service_id}")
    
    def record_heartbeat(self, heartbeat: ScraperHeartbeat):
        """Record a scraper heartbeat"""
        self.heartbeats[heartbeat.scraper_id] = heartbeat
        logger.debug(f"💓 Heartbeat from {heartbeat.scraper_id}: {heartbeat.status}")
    
    def start(self):
        """Start the guardian monitoring loop"""
        if self.running:
            return
        
        self.running = True
        self.check_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.check_thread.start()
        logger.info("🛡️ System Guardian started")
    
    def stop(self):
        """Stop the guardian"""
        self.running = False
        if self.check_thread:
            self.check_thread.join(timeout=5)
        logger.info("🛡️ System Guardian stopped")
    
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.running:
            try:
                self._perform_health_check()
                self.stats['checks_performed'] += 1
            except Exception as e:
                logger.error(f"Guardian error: {str(e)}", exc_info=True)
            
            time.sleep(self.check_interval)
    
    def _perform_health_check(self):
        """Perform comprehensive health check"""
        checks = []
        
        # 1. Check scraper heartbeats
        checks.extend(self._check_scrapers())
        
        # 2. Check system resources
        checks.append(self._check_system_resources())
        
        # 3. Check pipeline queue
        checks.append(self._check_pipeline_queue())
        
        # 4. Check database connectivity
        checks.append(self._check_database())
        
        # 5. Check API health
        checks.append(self._check_api_health())
        
        # Store results
        self.health_history.extend(checks)
        if len(self.health_history) > self.max_history:
            self.health_history = self.health_history[-self.max_history:]
        
        # Take actions
        for check in checks:
            if check.status in [ServiceStatus.CRITICAL, ServiceStatus.DEAD]:
                self._handle_failure(check)
    
    def _check_scrapers(self) -> List[HealthCheck]:
        """Check scraper health from heartbeats"""
        checks = []
        now = datetime.utcnow()
        
        for scraper_id, heartbeat in self.heartbeats.items():
            # Check heartbeat age
            age = (now - heartbeat.last_run).total_seconds()
            
            if age > self.HEARTBEAT_TIMEOUT_SECONDS:
                status = ServiceStatus.DEAD
                error_count = heartbeat.errors + 1
            elif age > self.HEARTBEAT_TIMEOUT_SECONDS / 2:
                status = ServiceStatus.WARNING
                error_count = heartbeat.errors
            else:
                status = ServiceStatus.HEALTHY
                error_count = heartbeat.errors
            
            check = HealthCheck(
                service=f"scraper:{scraper_id}",
                status=status,
                last_heartbeat=heartbeat.last_run,
                metrics={
                    'age_seconds': age,
                    'leads_collected': heartbeat.leads_collected,
                    'memory_mb': heartbeat.memory_mb,
                    'cpu_percent': heartbeat.cpu_percent
                },
                error_count=error_count
            )
            checks.append(check)
        
        return checks
    
    def _check_system_resources(self) -> HealthCheck:
        """Check CPU and memory usage"""
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        
        if cpu > self.MAX_CPU_PERCENT or memory.percent > self.MAX_MEMORY_PERCENT:
            status = ServiceStatus.CRITICAL
        elif cpu > self.MAX_CPU_PERCENT * 0.8 or memory.percent > self.MAX_MEMORY_PERCENT * 0.8:
            status = ServiceStatus.WARNING
        else:
            status = ServiceStatus.HEALTHY
        
        return HealthCheck(
            service="system:resources",
            status=status,
            metrics={
                'cpu_percent': cpu,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / 1024 / 1024
            }
        )
    
    def _check_pipeline_queue(self) -> HealthCheck:
        """Check pipeline queue size"""
        # This would integrate with Redis/RabbitMQ
        # For now, simulate with in-memory tracking
        queue_size = self._get_queue_size()
        
        if queue_size > self.MAX_QUEUE_SIZE:
            status = ServiceStatus.CRITICAL
        elif queue_size > self.MAX_QUEUE_SIZE * 0.8:
            status = ServiceStatus.WARNING
        else:
            status = ServiceStatus.HEALTHY
        
        return HealthCheck(
            service="pipeline:queue",
            status=status,
            metrics={'queue_size': queue_size}
        )
    
    def _check_database(self) -> HealthCheck:
        """Check database connectivity"""
        try:
            # Would perform actual DB ping here
            # For now, assume healthy if no exceptions
            status = ServiceStatus.HEALTHY
        except Exception as e:
            logger.error(f"Database check failed: {str(e)}")
            status = ServiceStatus.CRITICAL
        
        return HealthCheck(
            service="database:postgres",
            status=status,
            metrics={'last_check': datetime.utcnow().isoformat()}
        )
    
    def _check_api_health(self) -> HealthCheck:
        """Check API responsiveness"""
        # Would perform actual health check HTTP call
        status = ServiceStatus.HEALTHY
        
        return HealthCheck(
            service="api:fastapi",
            status=status,
            metrics={'endpoint': '/health'}
        )
    
    def _handle_failure(self, check: HealthCheck):
        """Handle detected failure with auto-recovery"""
        service = check.service
        self.stats['failures_detected'] += 1
        
        logger.error(f"🚨 FAILURE DETECTED: {service} is {check.status.value}")
        
        # Determine action
        action = self._determine_action(check)
        
        if action == GuardianAction.RESTART:
            self._restart_service(service)
        elif action == GuardianAction.FLUSH_QUEUE:
            self._flush_queue()
        elif action == GuardianAction.CLEAR_CACHE:
            self._clear_cache()
        elif action == GuardianAction.ALERT:
            self._send_alert(check)
        
        check.action_taken = action.value
    
    def _determine_action(self, check: HealthCheck) -> GuardianAction:
        """Determine recovery action based on failure type"""
        service = check.service
        
        # Check restart backoff
        if service in self.last_restart:
            time_since_restart = (datetime.utcnow() - self.last_restart[service]).total_seconds()
            if time_since_restart < 300:  # 5 minutes
                logger.warning(f"Restart backoff for {service}, alerting instead")
                return GuardianAction.ALERT
        
        # Service-specific actions
        if service.startswith("scraper:"):
            return GuardianAction.RESTART
        elif service == "pipeline:queue":
            return GuardianAction.FLUSH_QUEUE
        elif service == "system:resources":
            return GuardianAction.CLEAR_CACHE
        elif check.status == ServiceStatus.DEAD:
            return GuardianAction.RESTART
        
        return GuardianAction.ALERT
    
    def _restart_service(self, service: str):
        """Restart a failed service"""
        logger.info(f"🔄 Restarting service: {service}")
        
        self.restart_count[service] = self.restart_count.get(service, 0) + 1
        self.last_restart[service] = datetime.utcnow()
        
        try:
            if service.startswith("scraper:"):
                scraper_id = service.split(":")[1]
                if scraper_id in self.registered_services:
                    callback = self.registered_services[scraper_id]['restart_callback']
                    callback()
                    logger.info(f"✅ Scraper {scraper_id} restarted")
            
            self.stats['auto_recovers'] += 1
            
        except Exception as e:
            logger.error(f"Failed to restart {service}: {str(e)}")
            self._send_alert(None, f"Restart failed for {service}: {str(e)}")
    
    def _flush_queue(self):
        """Flush stuck pipeline queue"""
        logger.warning("🧹 Flushing pipeline queue")
        # Would integrate with actual queue system
        self.stats['auto_recovers'] += 1
    
    def _clear_cache(self):
        """Clear system cache"""
        logger.warning("🧹 Clearing system cache")
        # Would clear Redis/memory cache
        self.stats['auto_recovers'] += 1
    
    def _send_alert(self, check: Optional[HealthCheck], message: Optional[str] = None):
        """Send critical alert"""
        alert_msg = message or f"CRITICAL: {check.service} is {check.status.value}"
        logger.critical(f"🚨 ALERT: {alert_msg}")
        
        # Would send to Slack/PagerDuty/email here
        self.stats['alerts_sent'] += 1
    
    def _get_queue_size(self) -> int:
        """Get current queue size"""
        # Would integrate with Redis/RabbitMQ
        return 0
    
    def get_health_summary(self) -> Dict:
        """Get overall health summary"""
        recent_checks = [c for c in self.health_history 
                        if c.last_heartbeat and 
                        (datetime.utcnow() - c.last_heartbeat).seconds < 300]
        
        critical_count = sum(1 for c in recent_checks if c.status == ServiceStatus.CRITICAL)
        dead_count = sum(1 for c in recent_checks if c.status == ServiceStatus.DEAD)
        
        return {
            'overall_status': 'healthy' if dead_count == 0 and critical_count == 0 else 'degraded',
            'services_monitored': len(self.registered_services),
            'scrapers_active': len(self.heartbeats),
            'recent_failures': critical_count + dead_count,
            'auto_recovers': self.stats['auto_recovers'],
            'alerts_sent': self.stats['alerts_sent'],
            'restart_counts': self.restart_count,
            'last_check': datetime.utcnow().isoformat()
        }
    
    def get_service_health(self, service_id: str) -> Optional[HealthCheck]:
        """Get health for specific service"""
        for check in reversed(self.health_history):
            if check.service == service_id or check.service == f"scraper:{service_id}":
                return check
        return None
    
    def get_scraper_status(self) -> List[Dict]:
        """Get status of all registered scrapers"""
        status = []
        
        for scraper_id in self.registered_services:
            if not scraper_id.startswith("scraper:"):
                continue
                
            scraper_name = scraper_id.replace("scraper:", "")
            metadata = self.registered_services[scraper_id].get('metadata', {})
            
            # Get heartbeat if available
            heartbeat = self.heartbeats.get(scraper_name)
            guardian_health = self.get_service_health(scraper_name)
            
            status.append({
                'id': scraper_name,
                'platform': metadata.get('platform', 'unknown'),
                'running': heartbeat.status == "running" if heartbeat else False,
                'leads_collected': heartbeat.leads_collected if heartbeat else 0,
                'errors': heartbeat.errors if heartbeat else 0,
                'last_run': heartbeat.last_run.isoformat() if heartbeat and heartbeat.last_run else None,
                'last_heartbeat': self.last_heartbeat.isoformat() if self.last_heartbeat else None,
                'health': guardian_health.status.value if guardian_health else 'unknown'
            })
        
        return status


# Singleton instance
_guardian_instance = None

def get_guardian() -> SystemGuardian:
    """Get or create guardian instance"""
    global _guardian_instance
    if _guardian_instance is None:
        _guardian_instance = SystemGuardian()
    return _guardian_instance
