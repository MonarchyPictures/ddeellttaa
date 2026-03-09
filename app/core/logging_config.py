"""
Structured logging configuration.

Provides consistent logging across the application.
Supports both JSON (for production) and console (for development) formats.
"""

import json
import logging
import sys
from typing import Any, Dict

from app.core.config import settings


def configure_logging() -> None:
    """
    Configure logging for the application.
    
    Sets up:
    - Standard library logging with appropriate formatting
    - JSON formatting for production, console for development
    """
    if settings.LOG_FORMAT == "json":
        formatter = JsonFormatter()
    else:
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
    
    # Configure root logger
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, settings.LOG_LEVEL.upper()))
    root_logger.handlers = []  # Clear existing handlers
    root_logger.addHandler(handler)


class JsonFormatter(logging.Formatter):
    """JSON formatter for structured logging."""
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": self.formatTime(record),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        
        # Add extra fields if present
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        
        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        return json.dumps(log_data, default=str)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance.
    
    Args:
        name: The logger name (usually __name__)
        
    Returns:
        A configured logger
    """
    return logging.getLogger(name)


class RequestIdFilter(logging.Filter):
    """
    Add request ID to log records.
    
    This filter can be used with standard library logging
    to include request IDs in log output.
    """
    
    def __init__(self, name: str = ""):
        super().__init__(name)
        self.request_id: str = ""
    
    def filter(self, record: logging.LogRecord) -> bool:
        """Add request_id to the log record."""
        record.request_id = getattr(self, "request_id", "")
        return True


def bind_request_context(**kwargs: Any) -> None:
    """
    Bind context variables to the current thread's logger.
    
    Note: This is a simplified version. In production with structlog,
    this would use structlog.contextvars.
    
    Args:
        **kwargs: Key-value pairs to bind to the context
    """
    # Placeholder for structured context binding
    pass


def clear_request_context() -> None:
    """Clear all context variables from the current thread."""
    # Placeholder for structured context clearing
    pass
