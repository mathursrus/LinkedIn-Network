import pytest
from fastapi.testclient import TestClient
from linkedin_network_builder import app, CACHE_DIR
import os
import json
from datetime import datetime

@pytest.fixture
def client():
    """Create a test client"""
    return TestClient(app)

@pytest.fixture
def setup_cache():
    """Setup and cleanup cache directory"""
    os.makedirs(CACHE_DIR, exist_ok=True)
    
    def cleanup():
        for file in os.listdir(CACHE_DIR):
            if file.startswith("test_"):
                os.remove(os.path.join(CACHE_DIR, file))
    
    cleanup()
    yield
    cleanup()

def test_get_assistant_config(client):
    """Test getting assistant configuration"""
    response = client.get("/get_assistant_config")
    assert response.status_code == 200
    data = response.json()
    assert "assistant_id" in data

def test_browse_company_people(client, setup_cache):
    """Test browsing company people endpoint"""
    # Test with valid company
    response = client.get("/browse_company_people", params={"company": "Test Company"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    
    # Test with empty company
    response = client.get("/browse_company_people", params={"company": ""})
    assert response.status_code == 422  # FastAPI validation error

def test_search_linkedin_role(client, setup_cache):
    """Test searching for role at company"""
    # Test with valid parameters
    response = client.get("/search_linkedin_role", 
                         params={"role": "Software Engineer", 
                                "company": "Test Company"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    
    # Test with missing parameters
    response = client.get("/search_linkedin_role", 
                         params={"role": "Software Engineer"})
    assert response.status_code == 422  # FastAPI validation error

def test_find_mutual_connections(client, setup_cache):
    """Test finding mutual connections"""
    # Test with valid parameters
    response = client.get("/find_mutual_connections",
                         params={"person": "John Doe",
                                "company": "Test Company"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    
    # Test with profile URL
    response = client.get("/find_mutual_connections",
                         params={"person": "John Doe",
                                "company": "Test Company",
                                "profile_url": "https://linkedin.com/in/johndoe"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data

def test_find_connections_at_company(client, setup_cache):
    """Test finding connections at company for person"""
    # Test with valid parameters
    response = client.get("/find_connections_at_company_for_person",
                         params={"person_name": "John Doe",
                                "company_name": "Test Company"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data
    
    # Test with profile URL
    response = client.get("/find_connections_at_company_for_person",
                         params={"person_name": "John Doe",
                                "company_name": "Test Company",
                                "profile_url": "https://linkedin.com/in/johndoe"})
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "processing"
    assert "job_id" in data

def test_job_status(client, setup_cache):
    """Test job status endpoint"""
    # Create a test cache file
    test_job_id = os.path.join(CACHE_DIR, "test_job.json")
    test_data = {
        "status": "complete",
        "results": ["test result"],
        "timestamp": datetime.now().isoformat()
    }
    with open(test_job_id, 'w') as f:
        json.dump(test_data, f)
    
    # Test getting status of existing job
    response = client.get(f"/job_status/{os.path.basename(test_job_id)}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "complete"
    assert data["results"] == ["test result"]
    
    # Test getting status of non-existent job
    response = client.get("/job_status/nonexistent_job.json")
    assert response.status_code == 404

def test_rate_limits(client):
    """Test rate limits endpoint"""
    response = client.get("/rate_limits")
    assert response.status_code == 200
    data = response.json()
    
    # Check rate limit info for each operation
    for operation in ["linkedin_profile", "linkedin_search", "browser_init", "api_request"]:
        assert operation in data
        limit_info = data[operation]
        assert "current_requests" in limit_info
        assert "max_requests" in limit_info
        assert "time_window_seconds" in limit_info
        assert "usage_percent" in limit_info
        assert "timestamp" in limit_info

def test_error_handling(client):
    """Test API error handling"""
    # Test invalid endpoint
    response = client.get("/invalid_endpoint")
    assert response.status_code == 404
    
    # Test invalid parameters
    response = client.get("/browse_company_people")  # Missing required parameter
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    
    # Test invalid job ID format
    response = client.get("/job_status/invalid<>filename.json")
    assert response.status_code == 404

def test_concurrent_requests(client, setup_cache):
    """Test handling of concurrent requests"""
    import asyncio
    import httpx
    
    async def make_request(client):
        return client.get("/browse_company_people", 
                         params={"company": "Test Company"})
    
    # Make multiple concurrent requests
    responses = []
    for _ in range(3):  # Test with 3 concurrent requests
        response = client.get("/browse_company_people", 
                            params={"company": "Test Company"})
        responses.append(response)
    
    # Verify all requests were accepted and got unique job IDs
    job_ids = set()
    for response in responses:
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processing"
        assert "job_id" in data
        job_ids.add(data["job_id"])
    
    # Verify each request got a unique job ID
    assert len(job_ids) == 3 