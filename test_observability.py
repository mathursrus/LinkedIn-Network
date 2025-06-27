import asyncio
import json
import os
import pytest
from datetime import datetime
from logger_config import logger, LogCategory, log_operation
from rate_limiter import rate_limiter
import time

def test_logger_initialization():
    """Test that logger is properly initialized"""
    assert logger is not None
    assert os.path.exists("logs")
    
    # Test log file creation
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = f"logs/linkedin_network_{current_date}.log"
    
    # Clear existing logs
    with open(log_file, 'w') as f:
        f.write('')
    
    # Create a test log
    test_message = "Test log message"
    logger.info(LogCategory.API, "test_operation", message=test_message)
    
    # Verify log file exists and contains the message
    assert os.path.exists(log_file)
    with open(log_file, 'r') as f:
        log_lines = f.readlines()
        assert len(log_lines) > 0
        last_log = log_lines[-1].strip()
        
        # Parse the JSON log entry
        log_entry = json.loads(last_log)
        assert log_entry['level'] == 'INFO'
        assert log_entry['category'] == 'API'
        assert log_entry['operation'] == 'test_operation'
        assert log_entry['message'] == test_message

def test_rate_limiter():
    """Test rate limiter functionality"""
    # Reset rate limiter state
    rate_limiter.rate_limits["linkedin_search"].requests.clear()
    
    # Test initial state
    assert rate_limiter.check_rate_limit("linkedin_search") == True
    
    # Test rate limiting
    for _ in range(30):  # Max requests for linkedin_search
        rate_limiter.record_request("linkedin_search")
    
    # Should be at limit now
    assert rate_limiter.check_rate_limit("linkedin_search") == False
    
    # Test rate limit info
    limit_info = rate_limiter.get_rate_limit_info("linkedin_search")
    assert limit_info['current_requests'] == 30
    assert limit_info['max_requests'] == 30
    assert limit_info['usage_percent'] == 100.0

@pytest.mark.asyncio
async def test_async_operation():
    """Test async operation logging"""
    # Get current log file
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = f"logs/linkedin_network_{current_date}.log"
    
    # Clear existing logs
    with open(log_file, 'w') as f:
        f.write('')
    
    # Define and run test async function
    @log_operation(LogCategory.API, "test_async_op")
    async def test_func():
        await asyncio.sleep(0.1)
        return "success"
    
    result = await test_func()
    assert result == "success"
    
    # Check logs
    with open(log_file, 'r') as f:
        log_content = f.readlines()[-1]  # Get last log entry
        log_entry = json.loads(log_content)
        
        assert log_entry['category'] == 'API'
        assert log_entry['operation'] == 'test_async_op'
        assert log_entry['status'] == 'success'
        assert 'duration_ms' in log_entry
        assert float(log_entry['duration_ms']) >= 100  # Should be at least 100ms due to sleep

def test_error_logging():
    """Test error logging functionality"""
    # Get current log file
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = f"logs/linkedin_network_{current_date}.log"
    
    # Clear existing logs
    with open(log_file, 'w') as f:
        f.write('')
    
    try:
        raise ValueError("Test error")
    except Exception as e:
        logger.error(LogCategory.API, "test_error", error=e)
        
    # Check error log
    with open(log_file, 'r') as f:
        log_content = f.readlines()[-1]  # Get last log entry
        log_entry = json.loads(log_content)
        
        assert log_entry['level'] == 'ERROR'
        assert log_entry['status'] == 'error'
        assert log_entry['error'] == 'Test error'
        assert log_entry['error_type'] == 'ValueError'

if __name__ == "__main__":
    pytest.main([__file__, "-v"]) 