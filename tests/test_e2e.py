import pytest
import requests
import time
import json
import os
import shutil
import subprocess
from urllib.parse import urljoin

# Test configuration
BASE_URL = "http://localhost:8001"  # Assuming default FastAPI port
TIMEOUT = 1800 # 30 minutes
TEST_CACHE_DIR = "test_cache"  # Separate cache directory for tests

# Sample test data
TEST_COMPANIES = [
    {
        "name": "OpenAI",
        "roles": ["Product Manager"],
        "expected_fields": ["name", "profile_url", "role"]
    },
    {
        "name": "Anthropic",
        "roles": ["Data Scientist"],
        "expected_fields": ["name", "profile_url", "role"]
    }
]

TEST_MUTUAL_CONNECTIONS = [
    {
        "person": "Deepali Mathur",
        "company": "Chewy",
        "expected_fields": ["name", "profile_url", "role"]
    }
]

TEST_CONNECTIONS_AT_COMPANY_FOR_PERSON = [
    {
        "person": "Deepali Mathur",
        "company": "Microsoft",
        "expected_fields": ["name", "profile_url", "role"]
    }
]

@pytest.fixture(scope="session", autouse=True)
def setup_server():
    """Start the FastAPI server and set up test environment"""
    # Clean up any existing test cache
    if os.path.exists(TEST_CACHE_DIR):
        shutil.rmtree(TEST_CACHE_DIR)
    os.makedirs(TEST_CACHE_DIR)
    
    # Set environment variable for test cache directory
    os.environ["LINKEDIN_CACHE_DIR"] = TEST_CACHE_DIR
    
    # Start the FastAPI server using cmd and venv
    os.system('start cmd /k "cd /d %CD% && venv\\Scripts\\activate && python linkedin_network_builder.py"')
    
    # Wait for server to start
    max_retries = 20
    for _ in range(max_retries):
        try:
            response = requests.get(urljoin(BASE_URL, "/get_assistant_config"))
            if response.status_code == 200:
                break
            else:
                print(f"Server not yet ready")
        except requests.exceptions.ConnectionError:
            print(f"Server not yet ready")
        finally:
            time.sleep(5)
    
    yield
        
    os.environ.pop("LINKEDIN_CACHE_DIR", None)

def wait_for_job_completion(session, initial_response, timeout=TIMEOUT):
    """Helper function to wait for a job to complete or return immediate results"""
    data = initial_response.json()
    
    # if status is not processing, return the data
    if data["status"] != "processing":
        return data
    
    # Otherwise, we should have a job_id to poll
    assert "job_id" in data, "Response must contain either results or a job_id"
    job_id = data["job_id"]
    
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            response = session.get(urljoin(BASE_URL, f"/job_status/{job_id}"))
            assert response.status_code == 200
            data = response.json()
            
            if data["status"] != "processing":
                return data
            
            time.sleep(10)
        except requests.exceptions.ConnectionError:
            # The server might be temporarily unavailable, retry
            time.sleep(1)
            continue
    
    pytest.fail(f"Job timed out after {timeout} seconds")

@pytest.fixture
def session():
    """Create a session for making requests"""
    with requests.Session() as session:
        yield session

@pytest.mark.e2e
def test_role_search_workflow(session):
    """Test searching for roles at companies"""
    for company in TEST_COMPANIES:
        for role in company["roles"]:
            # Start the search
            response = session.get(
                urljoin(BASE_URL, "/who_works_as_role_at_company"),
                params={"role": role, "company": company["name"]}
            )
            assert response.status_code == 200
            
            # Wait for results
            results = wait_for_job_completion(session, response)
            
            # first ensure that the status is complete
            assert results["status"] == "complete"
            
            # Validate results
            if len(results) > 0:  # Only check structure if we have results
                for person in results["people"]:
                    for field in company["expected_fields"]:
                        # ensure the field is not empty or undefined
                        assert field in person and person[field] is not None and person[field] != ""

@pytest.mark.e2e
def test_mutual_connections_workflow(session):
    """Test finding mutual connections"""
    person = TEST_MUTUAL_CONNECTIONS[0]
    
    # Do the initial search
    response = session.get(
        urljoin(BASE_URL, "/who_can_introduce_me_to_person"),
        params={"person": person["person"], "company": person["company"]}
    )
    assert response.status_code == 200
    search_results = wait_for_job_completion(session, response)
    
    # first ensure that the status is complete
    assert search_results["status"] == "complete"
    
    # then ensure that the mutual connections are present
    if len(search_results) > 0:  # Only check structure if we have results
        for connection in search_results["mutual_connections"]:
            for field in person["expected_fields"]:
                # ensure the field is not empty or undefined
                assert field in connection and connection[field] is not None and connection[field] != ""

@pytest.mark.e2e
def test_error_handling(session):
    """Test system behavior with invalid inputs"""
    # Test invalid company
    response = session.get(
        urljoin(BASE_URL, "/who_works_as_role_at_company"),
        params={"role": "Software Engineer", "company": "ThisCompanyDoesNotExist12345"}
    )
    assert response.status_code == 200  # Should accept the request
    
    # Wait for job completion
    results = wait_for_job_completion(session, response)
    # status should be error
    assert results["status"] == "error"
    
    # Test invalid role
    response = session.get(
        urljoin(BASE_URL, "/who_works_as_role_at_company"),
        params={"role": "ThisRoleCannotPossiblyExist12345", "company": "Google"}
    )
    assert response.status_code == 200
    
    # Wait for job completion
    results = wait_for_job_completion(session, response)
    # status should be error
    assert results["status"] == "error"
    
    # Test invalid person for mutual connections
    response = session.get(
        urljoin(BASE_URL, "/who_can_introduce_me_to_person"),
        params={"person": "ThisPersonDoesNotExist12345", "company": "Google"}
    )
    assert response.status_code == 200
    
    # Wait for job completion
    results = wait_for_job_completion(session, response)
    assert results["status"] == "error"

    # Test more than 1 profile for mutual connection search
    response = session.get(
        urljoin(BASE_URL, "/who_can_introduce_me_to_person"),
        params={"person": "D", "company": "Google"}
    )
    assert response.status_code == 200
    
    # Wait for job completion
    results = wait_for_job_completion(session, response)
    assert results["status"] == "error"

@pytest.mark.e2e
def test_company_connections_workflow(session):
    """Test finding all my connections at a company"""
    company = TEST_COMPANIES[0]
    
    # Start the search
    response = session.get(
        urljoin(BASE_URL, "/who_do_i_know_at_company"),
        params={"company": company["name"]}
    )
    assert response.status_code == 200
    
    # Wait for results
    results = wait_for_job_completion(session, response)
    
    # first ensure that the status is complete
    assert results["status"] == "complete"
    
    # Validate results
    if len(results) > 0:  # Only check structure if we have results
        for person in results["people"]:
            for field in company["expected_fields"]:
                # ensure the field is not empty or undefined
                assert field in person and person[field] is not None and person[field] != ""

@pytest.mark.e2e
def test_person_company_connections_workflow(session):
    """Test finding who a specific person knows at a company"""
    test_data = TEST_CONNECTIONS_AT_COMPANY_FOR_PERSON[0]
    
    # Start the search
    response = session.get(
        urljoin(BASE_URL, "/who_does_person_know_at_company"),
        params={
            "person_name": test_data["person"],
            "company_name": test_data["company"]
        }
    )
    assert response.status_code == 200
    
    # Wait for results
    results = wait_for_job_completion(session, response)
    
    # first ensure that the status is complete
    assert results["status"] == "complete"
    
    # Validate results
    if len(results) > 0:  # Only check structure if we have results
        for person in results["people"]:
            for field in test_data["expected_fields"]:
                # ensure the field is not empty or undefined
                assert field in person and person[field] is not None and person[field] != ""
            