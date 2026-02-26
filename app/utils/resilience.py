import asyncio
import logging
import time
from functools import wraps
from typing import Callable, Any, Type, Tuple

logger = logging.getLogger("Resilience")

def retry_async(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry an async function with exponential backoff.
    """
    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {str(e)}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )
                    await asyncio.sleep(current_delay)
                    current_delay *= backoff
            return await func(*args, **kwargs)
        return wrapper
    return decorator

def retry_sync(
    retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: Tuple[Type[Exception], ...] = (Exception,)
):
    """
    Retry a sync function with exponential backoff.
    """
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt == retries - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {str(e)}")
                        raise
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {str(e)}. "
                        f"Retrying in {current_delay:.2f}s..."
                    )
                    time.sleep(current_delay)
                    current_delay *= backoff
            return func(*args, **kwargs)
        return wrapper
    return decorator

class CircuitBreaker:
    """
    Simple circuit breaker to stop calls to failing services.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failures = 0
        self.last_failure_time = 0
        self.state = "CLOSED" # CLOSED, OPEN, HALF-OPEN

    def call(self, func: Callable, *args, **kwargs):
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF-OPEN"
                logger.info(f"Circuit Breaker: HALF-OPEN state for {func.__name__}")
            else:
                logger.warning(f"Circuit Breaker: OPEN state, skipping call to {func.__name__}")
                return None

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF-OPEN":
                logger.info(f"Circuit Breaker: CLOSED state for {func.__name__} after successful call")
                self.state = "CLOSED"
                self.failures = 0
            return result
        except Exception as e:
            self.failures += 1
            self.last_failure_time = time.time()
            logger.error(f"Circuit Breaker: Call failed ({self.failures}/{self.failure_threshold}): {str(e)}")
            
            if self.failures >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"Circuit Breaker: OPEN state for {func.__name__}")
            
            raise e
