import os
import json
import pytest
import asyncio
from datetime import datetime
from logger_config import logger, LogCategory, log_operation

@pytest.fixture
def setup_logs():
    """Setup and cleanup log directory"""
    log_dir = "logs"
    os.makedirs(log_dir, exist_ok=True)
    
    # Get current log file
    current_date = datetime.now().strftime('%Y%m%d')
    log_file = f"logs/linkedin_network_{current_date}.log"
    
    # Clear existing logs
    with open(log_file, 'w') as f:
        f.write('')
    
    yield log_file
    
    # Cleanup test logs
    try:
        os.remove(log_file)
    except:
        pass

def test_logger_basic_operations(setup_logs):
    """Test basic logging operations"""
    log_file = setup_logs
    
    # Test info logging
    test_message = "Test info message"
    logger.info(LogCategory.API, "test_operation", message=test_message)
    
    # Test warning logging
    test_warning = "Test warning message"
    logger.warning(LogCategory.API, "test_warning", message=test_warning)
    
    # Test error logging
    test_error = "Test error message"
    logger.error(LogCategory.API, "test_error", error=test_error)
    
    # Verify logs
    with open(log_file, 'r') as f:
        logs = f.readlines()
        assert len(logs) == 3
        
        # Check info log
        info_log = json.loads(logs[0])
        assert info_log['level'] == 'INFO'
        assert info_log['category'] == 'API'
        assert info_log['operation'] == 'test_operation'
        assert info_log['message'] == test_message
        
        # Check warning log
        warning_log = json.loads(logs[1])
        assert warning_log['level'] == 'WARNING'
        assert warning_log['category'] == 'API'
        assert warning_log['operation'] == 'test_warning'
        assert warning_log['message'] == test_warning
        
        # Check error log
        error_log = json.loads(logs[2])
        assert error_log['level'] == 'ERROR'
        assert error_log['category'] == 'API'
        assert error_log['operation'] == 'test_error'
        assert error_log['error'] == test_error

def test_log_categories():
    """Test all log categories are valid"""
    for category in LogCategory:
        assert isinstance(category.value, str)
        assert len(category.value) > 0

@pytest.mark.asyncio
async def test_log_operation_decorator(setup_logs):
    """Test the log_operation decorator"""
    log_file = setup_logs
    
    # Test successful async operation
    @log_operation(LogCategory.API, "test_async_success")
    async def test_success():
        await asyncio.sleep(0.1)
        return "success"
    
    result = await test_success()
    assert result == "success"
    
    # Test failed async operation
    @log_operation(LogCategory.API, "test_async_failure")
    async def test_failure():
        await asyncio.sleep(0.1)
        raise ValueError("Test error")
    
    with pytest.raises(ValueError):
        await test_failure()
    
    # Test sync operation
    @log_operation(LogCategory.API, "test_sync")
    def test_sync():
        return "sync success"
    
    result = test_sync()
    assert result == "sync success"
    
    # Verify logs
    with open(log_file, 'r') as f:
        logs = [json.loads(line) for line in f.readlines()]
        
        # Check successful async operation log
        success_log = next(log for log in logs if log['operation'] == 'test_async_success')
        assert success_log['level'] == 'INFO'
        assert success_log['status'] == 'success'
        assert 'duration_ms' in success_log
        assert float(success_log['duration_ms']) >= 100  # At least 100ms due to sleep
        
        # Check failed async operation log
        failure_log = next(log for log in logs if log['operation'] == 'test_async_failure')
        assert failure_log['level'] == 'ERROR'
        assert failure_log['status'] == 'error'
        assert failure_log['error_type'] == 'ValueError'
        assert failure_log['error'] == 'Test error'
        
        # Check sync operation log
        sync_log = next(log for log in logs if log['operation'] == 'test_sync')
        assert sync_log['level'] == 'INFO'
        assert sync_log['status'] == 'success'
        assert 'duration_ms' in sync_log

def test_log_formatting(setup_logs):
    """Test log message formatting and structure"""
    log_file = setup_logs
    
    # Test with various data types
    logger.info(
        LogCategory.API,
        "test_formatting",
        string="test",
        number=42,
        boolean=True,
        none_value=None,
        list_value=["a", "b"],
        dict_value={"key": "value"}
    )
    
    # Verify log format
    with open(log_file, 'r') as f:
        log = json.loads(f.readline())
        
        # Check required fields
        assert 'timestamp' in log
        assert 'level' in log
        assert 'category' in log
        assert 'operation' in log
        
        # Check data type handling
        assert log['string'] == "test"
        assert log['number'] == 42
        assert log['boolean'] is True
        assert log['none_value'] is None
        assert log['list_value'] == ["a", "b"]
        assert log['dict_value'] == {"key": "value"}
        
        # Verify timestamp format
        datetime.fromisoformat(log['timestamp'].replace('Z', '+00:00'))

def test_log_error_handling(setup_logs):
    """Test error logging with different error types"""
    log_file = setup_logs
    
    # Test different types of errors
    try:
        raise ValueError("Test ValueError")
    except Exception as e:
        logger.error(LogCategory.API, "test_value_error", error=e)
    
    try:
        raise KeyError("Test KeyError")
    except Exception as e:
        logger.error(LogCategory.API, "test_key_error", error=e)
    
    try:
        raise RuntimeError("Test RuntimeError")
    except Exception as e:
        logger.error(LogCategory.API, "test_runtime_error", error=e)
    
    # Verify error logs
    with open(log_file, 'r') as f:
        logs = [json.loads(line) for line in f.readlines()]
        
        # Check ValueError log
        value_error_log = next(log for log in logs if log['operation'] == 'test_value_error')
        assert value_error_log['error_type'] == 'ValueError'
        assert value_error_log['error'] == 'Test ValueError'
        
        # Check KeyError log
        key_error_log = next(log for log in logs if log['operation'] == 'test_key_error')
        assert key_error_log['error_type'] == 'KeyError'
        assert 'Test KeyError' in key_error_log['error']
        
        # Check RuntimeError log
        runtime_error_log = next(log for log in logs if log['operation'] == 'test_runtime_error')
        assert runtime_error_log['error_type'] == 'RuntimeError'
        assert runtime_error_log['error'] == 'Test RuntimeError' 