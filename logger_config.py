import logging
import json
import time
import asyncio
from datetime import datetime, UTC
from enum import Enum
from functools import wraps
import os
from typing import Optional, Any, Dict

# Create logs directory if it doesn't exist
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

class LogCategory(Enum):
    NETWORK = "NETWORK"
    CACHE = "CACHE"
    BROWSER = "BROWSER"
    API = "API"

class StructuredLogger:
    def __init__(self):
        self.logger = logging.getLogger("linkedin_network")
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Console handler with custom formatter
            console_handler = logging.StreamHandler()
            console_handler.setFormatter(self._get_formatter())
            self.logger.addHandler(console_handler)
            
            # File handler for detailed logging
            file_handler = logging.FileHandler(
                os.path.join(LOGS_DIR, f"linkedin_network_{datetime.now().strftime('%Y%m%d')}.log")
            )
            file_handler.setFormatter(self._get_formatter())
            self.logger.addHandler(file_handler)

    def _get_formatter(self):
        return logging.Formatter('%(message)s')

    def _format_log(self, level: str, category: LogCategory, operation_name: str, 
                   duration_ms: Optional[float] = None, status: str = "success",
                   cache_hit: Optional[bool] = None, **kwargs) -> str:
        log_data = {
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ"),
            "level": level,
            "category": category.value,
            "operation": operation_name,
            "status": status
        }
        
        if duration_ms is not None:
            log_data["duration_ms"] = round(duration_ms, 2)
        if cache_hit is not None:
            log_data["cache_hit"] = cache_hit
            
        # Add any additional kwargs to the log data
        log_data.update(kwargs)
        
        return json.dumps(log_data)

    def info(self, category: LogCategory, operation_name: str, **kwargs):
        self.logger.info(self._format_log("INFO", category, operation_name, **kwargs))

    def error(self, category: LogCategory, operation_name: str, error: Exception = None, **kwargs):
        error_kwargs = kwargs.copy()
        if error:
            error_kwargs["error"] = str(error)
            error_kwargs["error_type"] = error.__class__.__name__
        self.logger.error(self._format_log("ERROR", category, operation_name, status="error", **error_kwargs))

    def warning(self, category: LogCategory, operation_name: str, **kwargs):
        self.logger.warning(self._format_log("WARNING", category, operation_name, **kwargs))

    def debug(self, category: LogCategory, operation_name: str, **kwargs):
        self.logger.debug(self._format_log("DEBUG", category, operation_name, **kwargs))

# Create a global logger instance
logger = StructuredLogger()

def log_operation(category: LogCategory, operation_name: str):
    """
    Decorator to log function execution time and status
    
    Example:
    @log_operation(LogCategory.NETWORK, "fetch_profile")
    async def fetch_profile(url: str):
        ...
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(category, operation_name, duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(category, operation_name, error=e, duration_ms=duration_ms)
                raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000
                logger.info(category, operation_name, duration_ms=duration_ms)
                return result
            except Exception as e:
                duration_ms = (time.time() - start_time) * 1000
                logger.error(category, operation_name, error=e, duration_ms=duration_ms)
                raise

        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper
    return decorator 