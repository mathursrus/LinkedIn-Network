import os
import json
import pytest
from datetime import datetime
from linkedin_network_builder import (
    CACHE_DIR,
    get_cache_filename,
    load_from_cache,
    save_to_cache,
    get_processing_message,
    handle_cached_results
)

@pytest.fixture
def setup_cache():
    """Setup and cleanup cache directory"""
    # Ensure cache directory exists
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    # Cleanup any existing test files
    def cleanup():
        for file in os.listdir(CACHE_DIR):
            if file.startswith("test_"):
                os.remove(os.path.join(CACHE_DIR, file))
    
    cleanup()
    yield
    cleanup()

def test_get_cache_filename():
    """Test cache filename generation"""
    # Test basic filename
    filename = get_cache_filename("test_query", person="John Doe", company="Acme")
    assert "test_query" in filename
    assert "johndoe" in filename.lower()
    assert "acme" in filename.lower()
    assert filename.endswith(".json")
    
    # Test with special characters
    filename = get_cache_filename("test", person="John @ Doe!", company="Acme & Co.")
    assert "john" in filename.lower()
    assert "doe" in filename.lower()
    assert "acme" in filename.lower()
    assert "co" in filename.lower()
    assert "@" not in filename
    assert "!" not in filename
    assert "&" not in filename
    
    # Test with empty values
    filename = get_cache_filename("test", person="", company=None)
    assert filename == os.path.join(CACHE_DIR, "test.json").replace('\\', '/')
    
    # Test with unicode characters
    filename = get_cache_filename("test", person="José García", company="Café Inc")
    assert "jose" in filename.lower()
    assert "garcia" in filename.lower()
    assert "cafe" in filename.lower()
    assert "inc" in filename.lower()

def test_cache_operations(setup_cache):
    """Test saving and loading from cache"""
    test_data = {
        "status": "complete",
        "results": ["test1", "test2"],
        "timestamp": datetime.now().isoformat()
    }
    
    filename = os.path.join(CACHE_DIR, "test_cache_ops.json")
    
    # Test saving
    save_to_cache(filename, test_data)
    assert os.path.exists(filename)
    
    # Test loading
    loaded_data = load_from_cache(filename)
    assert loaded_data == test_data
    
    # Test loading non-existent file
    non_existent = os.path.join(CACHE_DIR, "non_existent.json")
    assert load_from_cache(non_existent) is None

def test_get_processing_message():
    """Test processing message generation"""
    # Test basic message
    msg = get_processing_message(query_name="test_search", person="John", company="Acme")
    assert isinstance(msg, dict)
    assert msg["status"] == "processing"
    assert "test search" in msg["message"].lower()
    assert "processing" in msg["message"].lower()
    assert msg["job_id"].endswith(".json")
    
    # Test with different query types
    msg = get_processing_message(query_name="find_mutual_connections")
    assert "find mutual connections" in msg["message"].lower()

def test_handle_cached_results():
    """Test cached results handling"""
    # Test complete status
    complete_data = {
        "status": "complete",
        "results": ["result1", "result2"]
    }
    result = handle_cached_results(complete_data, person="John", company="Acme")
    assert result == complete_data
    
    # Test processing status
    processing_data = {
        "status": "processing",
        "timestamp": datetime.now().isoformat()
    }
    result = handle_cached_results(processing_data, person="John", company="Acme")
    assert result["status"] == "processing"
    assert "processing" in result["message"].lower()
    
    # Test failed status
    failed_data = {
        "status": "failed",
        "error": "Test error"
    }
    result = handle_cached_results(failed_data, person="John", company="Acme")
    assert result is None
    
    # Test None input
    assert handle_cached_results(None, person="John", company="Acme") is None

def test_cache_file_integrity(setup_cache):
    """Test cache file integrity and format"""
    test_data = {
        "status": "complete",
        "results": [{"name": "Test User", "role": "Engineer"}],
        "timestamp": datetime.now().isoformat()
    }
    
    filename = os.path.join(CACHE_DIR, "test_integrity.json")
    save_to_cache(filename, test_data)
    
    # Verify file exists and is valid JSON
    assert os.path.exists(filename)
    with open(filename, 'r') as f:
        file_content = f.read()
        # Verify it's valid JSON
        loaded = json.loads(file_content)
        assert loaded == test_data
        
    # Test loading preserves data types
    loaded_data = load_from_cache(filename)
    assert isinstance(loaded_data["results"], list)
    assert isinstance(loaded_data["results"][0], dict)
    assert isinstance(loaded_data["timestamp"], str)

def test_cache_concurrency(setup_cache):
    """Test cache operations with concurrent-like access patterns"""
    filename = os.path.join(CACHE_DIR, "test_concurrency.json")
    
    # Simulate concurrent writes
    initial_data = {"status": "processing", "timestamp": datetime.now().isoformat()}
    save_to_cache(filename, initial_data)
    
    # Immediate read should get processing status
    assert load_from_cache(filename)["status"] == "processing"
    
    # Update with complete status
    complete_data = {"status": "complete", "results": ["data"]}
    save_to_cache(filename, complete_data)
    
    # Read should now get complete status
    loaded = load_from_cache(filename)
    assert loaded["status"] == "complete"
    assert "results" in loaded 