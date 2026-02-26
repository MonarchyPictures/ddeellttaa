import logging
import json
import time
from typing import Any, Dict, Optional
from datetime import datetime

class JSONFormatter(logging.Formatter):
    """
    Formatter that outputs JSON strings after parsing the LogRecord.
    """
    def format(self, record):
        log_obj = {
            "timestamp": datetime.fromtimestamp(record.created).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "line": record.lineno
        }
        if record.exc_info:
            log_obj["exception"] = self.formatException(record.exc_info)
        return json.dumps(log_obj)

class StructuredLogger:
    def __init__(self, name: str):
        self.logger = logging.getLogger(name)
        self.name = name

    def _format(self, message: str, context: Optional[Dict[str, Any]] = None) -> str:
        # If the root logger is already using JSONFormatter, this double-encodes.
        # But this class seems designed to enforce structure manually.
        # We'll keep it compatible but prefer the root formatter approach for global consistency.
        data = {
            "timestamp": time.time(),
            "logger": self.name,
            "message": message,
            "context": context or {}
        }
        return json.dumps(data)

    def info(self, message: str, **kwargs):
        self.logger.info(message, extra=kwargs)

    def error(self, message: str, **kwargs):
        self.logger.error(message, extra=kwargs)

    def warning(self, message: str, **kwargs):
        self.logger.warning(message, extra=kwargs)

    def debug(self, message: str, **kwargs):
        self.logger.debug(message, extra=kwargs)

def get_logger(name: str):
    return logging.getLogger(name)

def setup_logging():
    """
    Configures the root logger to use JSON formatting for structured logging.
    Call this once at application startup.
    """
    handler = logging.StreamHandler()
    handler.setFormatter(JSONFormatter())
    
    # Reset root logger handlers
    root_logger = logging.getLogger()
    root_logger.handlers = []
    root_logger.addHandler(handler)
    root_logger.setLevel(logging.INFO)
