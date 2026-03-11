"""
DELTA-9 COMPREHENSIVE LOGGING SYSTEM
Production-grade logging with structured output

Features:
- Structured JSON logging
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL
- Separate log files for different components
- Log rotation
- Searchable logs
- Performance metrics
- Audit trail
"""

import logging
import logging.handlers
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from dataclasses import dataclass, asdict
import traceback


# Log directory
LOG_DIR = Path("logs")
LOG_DIR.mkdir(exist_ok=True)


class JSONFormatter(logging.Formatter):
    """JSON formatter for structured logging"""
    
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            'timestamp': datetime.utcnow().isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno,
        }
        
        # Add extra fields
        if hasattr(record, 'lead_id'):
            log_data['lead_id'] = record.lead_id
        if hasattr(record, 'scraper_id'):
            log_data['scraper_id'] = record.scraper_id
        if hasattr(record, 'query'):
            log_data['query'] = record.query
        if hasattr(record, 'phone'):
            log_data['phone'] = record.phone
        if hasattr(record, 'source'):
            log_data['source'] = record.source
        if hasattr(record, 'extra_data'):
            log_data.update(record.extra_data)
        
        # Add exception info
        if record.exc_info:
            log_data['exception'] = traceback.format_exception(*record.exc_info)
        
        return json.dumps(log_data, default=str)


class StructuredLogger:
    """
    Production-grade structured logger
    
    Usage:
        logger = StructuredLogger("scraper.telegram")
        logger.info("Lead found", lead_id="123", phone="0712345678")
    """
    
    def __init__(self, name: str):
        self.name = name
        self.logger = logging.getLogger(name)
        self._setup_handlers()
    
    def _setup_handlers(self):
        """Setup log handlers"""
        if self.logger.handlers:
            return
        
        self.logger.setLevel(logging.DEBUG)
        
        # Console handler (for development)
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console_fmt = logging.Formatter(
            '%(asctime)s [%(levelname)s] %(name)s: %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console.setFormatter(console_fmt)
        self.logger.addHandler(console)
        
        # File handler with rotation (JSON for production)
        file_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "delta9.log",
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=10
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(file_handler)
        
        # Error log (separate file for errors)
        error_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "errors.log",
            maxBytes=10 * 1024 * 1024,
            backupCount=10
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(error_handler)
    
    def _log(self, level: int, message: str, **kwargs):
        """Internal log method"""
        extra = {'extra_data': kwargs}
        
        # Extract known fields
        for field in ['lead_id', 'scraper_id', 'query', 'phone', 'source']:
            if field in kwargs:
                extra[field] = kwargs[field]
        
        self.logger.log(level, message, extra=extra)
    
    def debug(self, message: str, **kwargs):
        self._log(logging.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs):
        self._log(logging.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        self._log(logging.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs):
        self._log(logging.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        self._log(logging.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Log exception with traceback"""
        self.logger.exception(message, extra={'extra_data': kwargs})


# Specialized loggers for different components
class ScraperLogger(StructuredLogger):
    """Logger for scraper operations"""
    
    def __init__(self, scraper_id: str):
        super().__init__(f"scraper.{scraper_id}")
        self.scraper_id = scraper_id
    
    def lead_found(self, text: str, phone: str, source: str, **kwargs):
        """Log when lead is found"""
        self.info(
            "Lead found",
            scraper_id=self.scraper_id,
            phone=phone,
            source=source,
            text_preview=text[:100],
            **kwargs
        )
    
    def lead_rejected(self, text: str, reason: str, **kwargs):
        """Log when lead is rejected"""
        self.warning(
            "Lead rejected",
            scraper_id=self.scraper_id,
            reason=reason,
            text_preview=text[:100],
            **kwargs
        )
    
    def heartbeat(self, status: str, leads_collected: int, **kwargs):
        """Log scraper heartbeat"""
        self.debug(
            "Heartbeat",
            scraper_id=self.scraper_id,
            status=status,
            leads_collected=leads_collected,
            **kwargs
        )
    
    def error(self, message: str, exception: Optional[Exception] = None, **kwargs):
        """Log scraper error"""
        if exception:
            self.exception(
                message,
                scraper_id=self.scraper_id,
                error_type=type(exception).__name__,
                error_message=str(exception),
                **kwargs
            )
        else:
            super().error(message, scraper_id=self.scraper_id, **kwargs)


class PipelineLogger(StructuredLogger):
    """Logger for pipeline operations"""
    
    def __init__(self):
        super().__init__("pipeline")
    
    def lead_accepted(self, lead: Dict, **kwargs):
        """Log accepted lead"""
        self.info(
            "Lead accepted",
            lead_id=lead.get('id'),
            phone=lead.get('phone'),
            source_platform=lead.get('source_platform'),
            intent_score=lead.get('intent_score'),
            temperature=lead.get('temperature'),
            **kwargs
        )
    
    def lead_rejected(self, text: str, reason: str, stage: str, **kwargs):
        """Log rejected lead"""
        self.warning(
            "Lead rejected",
            reason=reason,
            stage=stage,
            text_preview=text[:100],
            **kwargs
        )
    
    def stage_complete(self, stage: str, lead_id: str, **kwargs):
        """Log pipeline stage completion"""
        self.debug(
            f"Stage complete: {stage}",
            stage=stage,
            lead_id=lead_id,
            **kwargs
        )


class GuardianLogger(StructuredLogger):
    """Logger for system guardian"""
    
    def __init__(self):
        super().__init__("guardian")
    
    def health_check(self, service: str, status: str, **kwargs):
        """Log health check result"""
        level = logging.INFO if status == 'healthy' else logging.WARNING
        self._log(level, f"Health check: {service} is {status}", 
                  service=service, status=status, **kwargs)
    
    def failure_detected(self, service: str, status: str, **kwargs):
        """Log detected failure"""
        self.error(
            f"Failure detected: {service}",
            service=service,
            status=status,
            **kwargs
        )
    
    def action_taken(self, service: str, action: str, **kwargs):
        """Log recovery action"""
        self.info(
            f"Action taken: {action} on {service}",
            service=service,
            action=action,
            **kwargs
        )
    
    def restart_service(self, service: str, **kwargs):
        """Log service restart"""
        self.warning(
            f"Restarting service: {service}",
            service=service,
            **kwargs
        )


class AuditLogger(StructuredLogger):
    """
    Audit logger for compliance and tracking
    
    Records:
    - Lead exports
    - User actions
    - System changes
    """
    
    def __init__(self):
        super().__init__("audit")
        
        # Separate audit log file
        audit_handler = logging.handlers.RotatingFileHandler(
            LOG_DIR / "audit.log",
            maxBytes=50 * 1024 * 1024,  # 50 MB
            backupCount=20
        )
        audit_handler.setFormatter(JSONFormatter())
        self.logger.addHandler(audit_handler)
    
    def lead_exported(self, lead_ids: list, user: str, format: str, **kwargs):
        """Log lead export"""
        self.info(
            "Leads exported",
            event_type="export",
            lead_count=len(lead_ids),
            lead_ids=lead_ids,
            user=user,
            format=format,
            **kwargs
        )
    
    def lead_contacted(self, lead_id: str, phone: str, method: str, user: str, **kwargs):
        """Log when lead is contacted"""
        self.info(
            "Lead contacted",
            event_type="contact",
            lead_id=lead_id,
            phone=phone,
            method=method,
            user=user,
            **kwargs
        )
    
    def user_action(self, action: str, user: str, details: Dict, **kwargs):
        """Log user action"""
        self.info(
            f"User action: {action}",
            event_type="user_action",
            action=action,
            user=user,
            details=details,
            **kwargs
        )
    
    def system_change(self, change_type: str, details: Dict, **kwargs):
        """Log system configuration change"""
        self.info(
            f"System change: {change_type}",
            event_type="system_change",
            change_type=change_type,
            details=details,
            **kwargs
        )


# Global logger instances
scrapers_logger = StructuredLogger("scrapers")
pipeline_logger = PipelineLogger()
guardian_logger = GuardianLogger()
audit_logger = AuditLogger()


def get_logger(name: str) -> StructuredLogger:
    """Get a structured logger by name"""
    return StructuredLogger(name)


def get_scraper_logger(scraper_id: str) -> ScraperLogger:
    """Get a scraper-specific logger"""
    return ScraperLogger(scraper_id)


def search_logs(query: str, log_file: str = "delta9.log", 
                limit: int = 100) -> list:
    """
    Search logs for specific query
    
    Args:
        query: Search string
        log_file: Log file to search
        limit: Maximum results
        
    Returns:
        List of matching log entries
    """
    results = []
    log_path = LOG_DIR / log_file
    
    if not log_path.exists():
        return results
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                if query.lower() in line.lower():
                    try:
                        entry = json.loads(line)
                        results.append(entry)
                        if len(results) >= limit:
                            break
                    except json.JSONDecodeError:
                        # Handle non-JSON lines
                        results.append({'raw': line.strip()})
    except Exception as e:
        print(f"Error searching logs: {e}")
    
    return results


def get_recent_errors(minutes: int = 60) -> list:
    """
    Get recent errors from error log
    
    Args:
        minutes: Time window in minutes
        
    Returns:
        List of recent errors
    """
    from datetime import timedelta
    
    cutoff = datetime.utcnow() - timedelta(minutes=minutes)
    errors = []
    
    log_path = LOG_DIR / "errors.log"
    if not log_path.exists():
        return errors
    
    try:
        with open(log_path, 'r') as f:
            for line in f:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.fromisoformat(entry['timestamp'])
                    if entry_time > cutoff:
                        errors.append(entry)
                except (json.JSONDecodeError, KeyError):
                    continue
    except Exception as e:
        print(f"Error reading errors: {e}")
    
    return errors
