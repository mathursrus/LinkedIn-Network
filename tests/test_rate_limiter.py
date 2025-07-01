import pytest
import time
from rate_limiter import RateLimiter, rate_limiter
from collections import deque

@pytest.fixture
def fresh_rate_limiter():
    """Provide a fresh rate limiter instance for each test"""
    return RateLimiter()

def test_rate_limiter_initialization(fresh_rate_limiter):
    """Test that rate limiter initializes with correct default values"""
    assert "linkedin_profile" in fresh_rate_limiter.rate_limits
    assert "linkedin_search" in fresh_rate_limiter.rate_limits
    assert "browser_init" in fresh_rate_limiter.rate_limits
    assert "api_request" in fresh_rate_limiter.rate_limits
    
    # Test specific limits
    linkedin_profile = fresh_rate_limiter.rate_limits["linkedin_profile"]
    assert linkedin_profile.max_requests == 20
    assert linkedin_profile.time_window == 60
    assert isinstance(linkedin_profile.requests, deque)
    assert len(linkedin_profile.requests) == 0

def test_check_rate_limit_unknown_operation(fresh_rate_limiter):
    """Test behavior with unknown operation"""
    assert fresh_rate_limiter.check_rate_limit("unknown_operation") == True

def test_record_request_unknown_operation(fresh_rate_limiter):
    """Test recording request for unknown operation"""
    # Should not raise exception
    fresh_rate_limiter.record_request("unknown_operation")

def test_rate_limit_basic_flow(fresh_rate_limiter):
    """Test basic rate limiting flow"""
    operation = "linkedin_profile"
    
    # Should allow max_requests
    for _ in range(20):
        assert fresh_rate_limiter.check_rate_limit(operation) == True
        fresh_rate_limiter.record_request(operation)
    
    # Should deny next request
    assert fresh_rate_limiter.check_rate_limit(operation) == False

def test_rate_limit_window_expiry(fresh_rate_limiter):
    """Test that requests expire after time window"""
    operation = "linkedin_search"
    
    # Add some requests with artificially old timestamps
    old_time = time.time() - 61  # Just over the 60 second window
    for _ in range(15):
        fresh_rate_limiter.rate_limits[operation].requests.append(old_time)
    
    # Add some recent requests
    for _ in range(10):
        fresh_rate_limiter.record_request(operation)
    
    # Check rate limit - should clean old requests and allow new ones
    assert fresh_rate_limiter.check_rate_limit(operation) == True
    assert len(fresh_rate_limiter.rate_limits[operation].requests) == 10

def test_get_rate_limit_info(fresh_rate_limiter):
    """Test rate limit info reporting"""
    operation = "browser_init"
    
    # Record some requests
    for _ in range(3):
        fresh_rate_limiter.record_request(operation)
    
    info = fresh_rate_limiter.get_rate_limit_info(operation)
    assert info["operation"] == operation
    assert info["current_requests"] == 3
    assert info["max_requests"] == 5
    assert info["time_window_seconds"] == 60
    assert info["usage_percent"] == 60.0
    assert "timestamp" in info

def test_get_rate_limit_info_unknown_operation(fresh_rate_limiter):
    """Test rate limit info for unknown operation"""
    info = fresh_rate_limiter.get_rate_limit_info("unknown_operation")
    assert "error" in info
    assert "timestamp" in info

def test_concurrent_rate_limits(fresh_rate_limiter):
    """Test that different operations have independent rate limits"""
    # Fill up linkedin_profile
    for _ in range(20):
        fresh_rate_limiter.record_request("linkedin_profile")
    
    # linkedin_profile should be blocked
    assert fresh_rate_limiter.check_rate_limit("linkedin_profile") == False
    
    # But linkedin_search should still work
    assert fresh_rate_limiter.check_rate_limit("linkedin_search") == True

def test_rate_limit_edge_cases(fresh_rate_limiter):
    """Test edge cases in rate limiting"""
    operation = "api_request"
    
    # Test exactly at limit
    for _ in range(100):  # api_request limit is 100
        assert fresh_rate_limiter.check_rate_limit(operation) == True
        fresh_rate_limiter.record_request(operation)
    
    assert fresh_rate_limiter.check_rate_limit(operation) == False
    
    # Test recovery after cleaning old requests
    fresh_rate_limiter.rate_limits[operation].requests.clear()
    assert fresh_rate_limiter.check_rate_limit(operation) == True

def test_global_rate_limiter_instance():
    """Test that global rate limiter instance exists and works"""
    assert rate_limiter is not None
    assert isinstance(rate_limiter, RateLimiter)
    
    # Test basic functionality of global instance
    operation = "browser_init"
    initial_state = rate_limiter.check_rate_limit(operation)
    rate_limiter.record_request(operation)
    info = rate_limiter.get_rate_limit_info(operation)
    
    assert isinstance(initial_state, bool)
    assert isinstance(info, dict)
    assert info["operation"] == operation 