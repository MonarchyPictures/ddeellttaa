import time
import random
import logging
from typing import Callable, Any, Optional
from functools import wraps

logger = logging.getLogger(__name__)

class CircuitBreaker:
    """
    Circuit Breaker implementation to prevent cascading failures.
    States: CLOSED (Normal), OPEN (Failing), HALF_OPEN (Recovering).
    """
    def __init__(self, failure_threshold: int = 3, recovery_timeout: int = 60, name: str = "CircuitBreaker"):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"
        self.name = name

    def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == "OPEN":
            if time.time() - (self.last_failure_time or 0) > self.recovery_timeout:
                self.state = "HALF_OPEN"
                logger.info(f"🔌 Circuit Breaker '{self.name}' entering HALF_OPEN state.")
            else:
                raise Exception(f"🔌 Circuit Breaker '{self.name}' is OPEN. Request blocked.")

        try:
            result = func(*args, **kwargs)
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                logger.info(f"✅ Circuit Breaker '{self.name}' recovered to CLOSED state.")
            return result
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = time.time()
            logger.warning(f"⚠️ Circuit Breaker '{self.name}' failure {self.failure_count}/{self.failure_threshold}: {str(e)}")
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                logger.error(f"🔥 Circuit Breaker '{self.name}' OPENED due to failures.")
            
            raise e

def exponential_backoff(retries: int = 3, base_delay: float = 1.0, max_delay: float = 10.0, jitter: bool = True):
    """
    Decorator for exponential backoff with jitter.
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exception = None
            
            for attempt in range(retries + 1):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    if attempt == retries:
                        break
                    
                    sleep_time = min(delay * (2 ** attempt), max_delay)
                    if jitter:
                        sleep_time += random.uniform(0, sleep_time * 0.1)
                    
                    logger.warning(f"🔄 Retry {attempt + 1}/{retries} for {func.__name__} in {sleep_time:.2f}s due to: {str(e)}")
                    time.sleep(sleep_time)
            
            if last_exception is not None:
                raise last_exception
            raise RuntimeError("Unexpected error in exponential backoff")
        return wrapper
    return decorator

class ResilienceManager:
    _breakers = {}

    @classmethod
    def get_breaker(cls, name: str, threshold: int = 3, timeout: int = 60) -> CircuitBreaker:
        if name not in cls._breakers:
            cls._breakers[name] = CircuitBreaker(threshold, timeout, name)
        return cls._breakers[name]
