import time
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Deque
from logger_config import logger, LogCategory

@dataclass
class RateLimit:
    max_requests: int
    time_window: int  # in seconds
    requests: Deque[float]

class RateLimiter:
    def __init__(self):
        # Define rate limits for different operations
        self.rate_limits: Dict[str, RateLimit] = {
            "linkedin_profile": RateLimit(max_requests=20, time_window=60, requests=deque()),
            "linkedin_search": RateLimit(max_requests=30, time_window=60, requests=deque()),
            "browser_init": RateLimit(max_requests=5, time_window=60, requests=deque()),
            "api_request": RateLimit(max_requests=100, time_window=60, requests=deque())
        }
    
    def _clean_old_requests(self, operation: str):
        """Remove requests older than the time window"""
        rate_limit = self.rate_limits[operation]
        current_time = time.time()
        
        while (rate_limit.requests and 
               current_time - rate_limit.requests[0] > rate_limit.time_window):
            rate_limit.requests.popleft()
    
    def check_rate_limit(self, operation: str) -> bool:
        """
        Check if an operation would exceed rate limits
        Returns True if operation is allowed, False if it would exceed limits
        """
        if operation not in self.rate_limits:
            logger.warning(LogCategory.API, "rate_limit_check",
                         message=f"Unknown operation: {operation}",
                         operation=operation)
            return True
        
        rate_limit = self.rate_limits[operation]
        self._clean_old_requests(operation)
        
        # Check if we're at the limit
        if len(rate_limit.requests) >= rate_limit.max_requests:
            logger.warning(LogCategory.API, "rate_limit_exceeded",
                         operation=operation,
                         current_requests=len(rate_limit.requests),
                         max_requests=rate_limit.max_requests,
                         time_window=rate_limit.time_window)
            return False
        
        return True
    
    def record_request(self, operation: str):
        """Record that a request was made"""
        if operation not in self.rate_limits:
            logger.warning(LogCategory.API, "rate_limit_record",
                         message=f"Unknown operation: {operation}",
                         operation=operation)
            return
        
        rate_limit = self.rate_limits[operation]
        current_time = time.time()
        
        # Clean old requests first
        self._clean_old_requests(operation)
        
        # Add the new request
        rate_limit.requests.append(current_time)
        
        # Log current usage
        usage_percent = (len(rate_limit.requests) / rate_limit.max_requests) * 100
        logger.info(LogCategory.API, "rate_limit_usage",
                   operation=operation,
                   current_requests=len(rate_limit.requests),
                   max_requests=rate_limit.max_requests,
                   usage_percent=round(usage_percent, 2))
    
    def get_rate_limit_info(self, operation: str) -> dict:
        """Get current rate limit information for an operation"""
        if operation not in self.rate_limits:
            return {
                "error": f"Unknown operation: {operation}",
                "timestamp": datetime.now().isoformat()
            }
        
        rate_limit = self.rate_limits[operation]
        self._clean_old_requests(operation)
        
        return {
            "operation": operation,
            "current_requests": len(rate_limit.requests),
            "max_requests": rate_limit.max_requests,
            "time_window_seconds": rate_limit.time_window,
            "usage_percent": round((len(rate_limit.requests) / rate_limit.max_requests) * 100, 2),
            "timestamp": datetime.now().isoformat()
        }

# Create a global rate limiter instance
rate_limiter = RateLimiter() 