import sys
import asyncio
import json
import os
from datetime import datetime
import uuid
import re
import urllib.parse
from dotenv import load_dotenv
from openai import OpenAI
from assistant_manager import get_assistant, create_assistant
from logger_config import logger, LogCategory, log_operation
from rate_limiter import rate_limiter

# Load environment variables from .env file
load_dotenv()

# Define and create the cache directory
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Check for command line arguments FIRST, before any other imports
if len(sys.argv) > 1 and sys.argv[1] == "--install-browsers":
    # Install browsers and exit
    async def install_browsers():
        """Install Playwright browsers"""
        try:
            print("Installing Playwright browsers...")
            print("This may take several minutes and requires internet connection.")
            
            # Import playwright and install browsers
            from playwright._impl._driver import compute_driver_executable, get_driver_env
            import subprocess
            
            driver_executable = compute_driver_executable()
            env = get_driver_env()
            
            # Set a persistent browser location
            persistent_browser_path = os.path.join(os.path.expanduser("~"), ".playwright-browsers")
            env["PLAYWRIGHT_BROWSERS_PATH"] = persistent_browser_path
            
            # Run playwright install chromium
            result = subprocess.run([
                str(driver_executable), "install", "chromium"
            ], env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                print("✅ Browsers installed successfully!")
                print(f"Browsers installed to: {persistent_browser_path}")
                return True
            else:
                print(f"❌ Browser installation failed: {result.stderr}")
                return False
                
        except Exception as e:
            print(f"❌ Error installing browsers: {e}")
            return False
    
    # Run the installation and exit
    result = asyncio.run(install_browsers())
    sys.exit(0 if result else 1)

# Fix for PyInstaller + Playwright subprocess issues
if sys.platform == 'win32':
    # Use ProactorEventLoop for better subprocess support in PyInstaller
    if hasattr(asyncio, 'WindowsProactorEventLoopPolicy'):
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    else:
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Query, BackgroundTasks, HTTPException
from playwright.async_api import async_playwright
import uvicorn
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Initialize OpenAI client
openai_api_key = os.getenv("OPENAI_API_KEY")
if not openai_api_key:
    raise ValueError("OPENAI_API_KEY environment variable not set.")
client = OpenAI(api_key=openai_api_key)

# Get or create the assistant
ASSISTANT_ID = get_assistant(client)
if not ASSISTANT_ID:
    ASSISTANT_ID = create_assistant(client)

# Global store for job statuses is now REMOVED. We use the filesystem cache.
# jobs = {}

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Global semaphore to limit concurrent browser sessions
browser_semaphore = asyncio.Semaphore(3)

async def install_browsers():
    """Install Playwright browsers"""
    try:
        print("Installing Playwright browsers...")
        print("This may take several minutes and requires internet connection.")
        
        # Import playwright and install browsers
        from playwright._impl._driver import compute_driver_executable, get_driver_env
        import subprocess
        
        driver_executable = compute_driver_executable()
        env = get_driver_env()
        
        # Set a persistent browser location
        persistent_browser_path = os.path.join(os.path.expanduser("~"), ".playwright-browsers")
        env["PLAYWRIGHT_BROWSERS_PATH"] = persistent_browser_path
        
        # Run playwright install chromium
        result = subprocess.run([
            str(driver_executable), "install", "chromium"
        ], env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Browsers installed successfully!")
            print(f"Browsers installed to: {persistent_browser_path}")
            return True
        else:
            print(f"❌ Browser installation failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error installing browsers: {e}")
        return False

def get_cache_filename(query_name: str, **kwargs) -> str:
    """Generate a cache filename from a query name and parameters."""
    filename_parts = [query_name]
    for key, value in sorted(kwargs.items()):
        if value: # Only add parts that have a value
            sanitized_value = re.sub(r'[\W_]+', '', str(value).lower())
            filename_parts.append(sanitized_value)
    
    filename = "_".join(filename_parts) + ".json"
    # Always return a web-friendly path with forward slashes
    return os.path.join(CACHE_DIR, filename).replace('\\', '/')

@log_operation(LogCategory.CACHE, "load_from_cache")
def load_from_cache(filename: str) -> dict:
    """Load data from cache file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            data = json.load(f)
            logger.info(LogCategory.CACHE, "cache_read", cache_hit=True, filename=filename)
            return data
    logger.info(LogCategory.CACHE, "cache_read", cache_hit=False, filename=filename)
    return None

@log_operation(LogCategory.CACHE, "save_to_cache")
def save_to_cache(filename, data):
    """Save data to cache file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
        logger.info(LogCategory.CACHE, "cache_write", filename=filename)

def get_processing_message(**kwargs) -> dict:
    """Get the processing message for a search"""
    job_id = get_cache_filename(**kwargs)
    # Reconstruct a human-readable message from kwargs
    query_name = kwargs.get("query_name", "request").replace("_", " ")
    message = f"Your {query_name} is processing. I'll let you know when it's done."
    
    return {
        "status": "processing",
        "message": message,
        "job_id": job_id
    }

def handle_cached_results(cached_data: dict, **kwargs) -> dict:
    """Handle cached results and determine if we should retry"""
    if not cached_data:
        return None
        
    if cached_data.get('status') == 'complete':
        return cached_data
        
    if cached_data.get('status') == 'processing':
        return get_processing_message(**kwargs)
        
    # If we get here, the previous attempt failed
    print(f"Previous attempt for {kwargs.get('person', '')} at {kwargs.get('company', '')} failed. Retrying...")
    return None

def mark_as_processing(**kwargs):
    """Mark a query as being processed by creating a cache file."""
    cache_filename = get_cache_filename(**kwargs)
    processing_data = { "status": "processing", "timestamp": datetime.now().isoformat() }
    # Add all original parameters to the processing file for context
    processing_data.update(kwargs)
    save_to_cache(cache_filename, processing_data)

async def extract_people_from_page(page):
    """Helper function to extract people information from a LinkedIn page using .mb1 blocks"""
    try:
        await page.wait_for_selector('.search-results-container', timeout=30000)
        print("Search results container found")
        await page.wait_for_timeout(5000)

        # Use .mb1 as the person block selector
        blocks = await page.query_selector_all('.mb1')
        print(f"Found {len(blocks)} person blocks with .mb1 selector")

        mypeople = []
        for block in blocks:
            # Name: first <span aria-hidden="true"> inside <a href*="/in/">
            name_elem = await block.query_selector('a[href*="/in/"] span[aria-hidden="true"]')
            name = await name_elem.inner_text() if name_elem else ""
            # Profile URL from <a href>
            profile_link_elem = await block.query_selector('a[href*="/in/"]')
            profile_url = await profile_link_elem.get_attribute('href') if profile_link_elem else ""

            # Role and location: 2nd and 3rd top-level divs under .mb1
            divs = await block.query_selector_all(':scope > div')
            role = await divs[1].inner_text() if len(divs) > 1 else ""
            location = await divs[2].inner_text() if len(divs) > 2 else ""

            if name:
                mypeople.append({
                    "name": name.strip(),
                    "profile_url": profile_url,
                    "role": role.strip(),
                    "location": location.strip()
                })
        return mypeople
    except Exception as e:
        print(f"Error extracting people from page: {e}")
        return []

@log_operation(LogCategory.BROWSER, "initialize_browser")
async def initialize_browser():
    """Initialize and return a browser instance"""
    if not rate_limiter.check_rate_limit("browser_init"):
        raise Exception("Browser initialization rate limit exceeded")
    
    try:
        async with async_playwright() as p:
            rate_limiter.record_request("browser_init")
            browser = await p.chromium.launch()
            context = await browser.new_context()
            page = await context.new_page()
            logger.info(LogCategory.BROWSER, "browser_initialized")
            return p, browser, context, page
    except Exception as e:
        logger.error(LogCategory.BROWSER, "browser_initialization_failed", error=e)
        raise

@log_operation(LogCategory.NETWORK, "search_and_process_connections")
async def search_and_process_connections(page, network_type: str, company: str = None, role: str = None):
    """Search and process LinkedIn connections"""
    if not rate_limiter.check_rate_limit("linkedin_search"):
        raise Exception("LinkedIn search rate limit exceeded")
    
    try:
        rate_limiter.record_request("linkedin_search")
        # Construct search URL based on parameters
        search_params = []
        if company:
            search_params.append(f"company={urllib.parse.quote(company)}")
        if role:
            search_params.append(f"title={urllib.parse.quote(role)}")
        
        search_url = f"https://www.linkedin.com/search/results/people/?{'&'.join(search_params)}"
        logger.info(LogCategory.NETWORK, "linkedin_search_start", 
                   url=search_url, network_type=network_type)
        
        await page.goto(search_url)
        await page.wait_for_selector('.search-results-container', timeout=30000)
        
        # Process results
        results = await process_search_results(page)
        logger.info(LogCategory.NETWORK, "linkedin_search_complete",
                   result_count=len(results))
        return results
        
    except Exception as e:
        logger.error(LogCategory.NETWORK, "linkedin_search_failed",
                    error=e, network_type=network_type,
                    company=company, role=role)
        raise

@log_operation(LogCategory.NETWORK, "get_mutual_connections")
async def get_mutual_connections_for_profile(page, profile_url: str):
    """Get mutual connections for a profile"""
    if not rate_limiter.check_rate_limit("linkedin_profile"):
        raise Exception("LinkedIn profile access rate limit exceeded")
    
    try:
        rate_limiter.record_request("linkedin_profile")
        logger.info(LogCategory.NETWORK, "mutual_connections_fetch_start",
                   profile_url=profile_url)
        
        await page.goto(profile_url)
        await page.wait_for_selector('.pv-top-card', timeout=30000)
        
        # Get mutual connections
        mutual_connections = []
        mutual_button = await page.query_selector('a[href*="mutual-connections"]')
        if mutual_button:
            await mutual_button.click()
            await page.wait_for_selector('.search-results-container')
            mutual_connections = await process_search_results(page)
        
        logger.info(LogCategory.NETWORK, "mutual_connections_fetch_complete",
                   profile_url=profile_url,
                   mutual_count=len(mutual_connections))
        return mutual_connections
        
    except Exception as e:
        logger.error(LogCategory.NETWORK, "mutual_connections_fetch_failed",
                    error=e, profile_url=profile_url)
        raise

async def process_company_connections(company: str, cache_filename: str):
    """Background task to process company connections"""
    async with browser_semaphore:
        print(f"Browser slot acquired for company: {company}. Starting processing.")
        try:
            # No need to check cache here, the endpoint does it.
            print(f"Starting background processing for company: {company} (Cache File: {cache_filename})")
            browser = None
            p = None
            try:
                browser, page, p = await initialize_browser()
                if not browser or not page:
                    error_result = {
                        "company": company,
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "error": "Failed to initialize browser or login to LinkedIn"
                    }
                    save_to_cache(cache_filename, error_result)
                    return error_result
                
                try:
                    # Search for 1st level connections
                    first_degree = await search_and_process_connections(page, 'F', company=company)
                    
                    # Search for 2nd level connections
                    second_degree = await search_and_process_connections(page, 'S', company=company)
                    
                    # Combine all results
                    people = first_degree + second_degree
                    
                    print("\nClosing browser...")
                    await browser.close()
                    await p.stop()
                    print("Done!")
                    print(f"Total people found: {len(people)}")
                    print(people)
                    
                    # Save results to cache AND update job status
                    result = {
                        "company": company,
                        "status": "complete",
                        "timestamp": datetime.now().isoformat(),
                        "people": people
                    }
                    save_to_cache(cache_filename, result)
                    return result
                    
                finally:
                    if browser:
                        await browser.close()
                    if p:
                        await p.stop()
            
            except Exception as e:
                # If there's an error, save error state to cache
                error_result = {
                    "company": company,
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
                save_to_cache(cache_filename, error_result)
                raise e
        finally:
            print(f"Browser slot released for company: {company}.")

@app.get("/get_assistant_config")
async def get_assistant_config():
    return {"assistant_id": ASSISTANT_ID, "openai_api_key": openai_api_key}

@app.get("/browse_company_people")
@log_operation(LogCategory.API, "browse_company_people")
async def browse_public_linkedin(company: str, background_tasks: BackgroundTasks):
    """Browse people at a company"""
    cache_filename = get_cache_filename("browse_company", company_name=company)
    
    # Check cache first
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        return handle_cached_results(cached_data, query_name="browse_company", company=company)
    
    # Mark as processing and start background task
    mark_as_processing(query_name="browse_company", company_name=company)
    background_tasks.add_task(process_company_connections, company, cache_filename)
    
    return get_processing_message(query_name="browse_company", company=company)

@app.get("/search_linkedin_role")
async def search_linkedin_role(role: str, company: str, background_tasks: BackgroundTasks):
    """Search for people with a specific role at a company"""
    query_params = {"query_name": "role_search", "role": role, "company": company}
    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)
        
    mark_as_processing(**query_params)
    background_tasks.add_task(process_role_search, role, company, cache_filename)
    return get_processing_message(**query_params)

@app.get("/job_status/{job_id:path}")
async def get_job_status(job_id: str):
    """Get the status of a background job from its cache file"""
    if not os.path.exists(job_id):
        raise HTTPException(status_code=404, detail="Job not found")
    return load_from_cache(job_id)

@app.get("/find_mutual_connections")
async def find_mutual_connections(person: str, company: str, background_tasks: BackgroundTasks, profile_url: str = None):
    """Search for mutual connections with a person at a company"""
    query_params = {
        "query_name": "mutual_connections", 
        "person": person, 
        "company": company,
        "profile_url": profile_url
    }
    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)

    mark_as_processing(**query_params)
    background_tasks.add_task(process_mutual_connections, person, company, cache_filename, profile_url)
    return get_processing_message(**query_params)

@app.get("/find_connections_at_company_for_person")
async def find_connections_at_company_for_person(person_name: str, company_name: str, background_tasks: BackgroundTasks, profile_url: str = None):
    """Finds connections of a specific person who work at a specific company."""
    query_params = {
        "query_name": "connections_through_person",
        "person_name": person_name,
        "company_name": company_name,
        "profile_url": profile_url
    }
    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)

    mark_as_processing(**query_params)
    background_tasks.add_task(process_find_connections_at_company_for_person, person_name, company_name, cache_filename, profile_url)
    return get_processing_message(**query_params)

@log_operation(LogCategory.NETWORK, "process_mutual_connections")
async def process_mutual_connections(person: str, company: str, cache_filename: str, profile_url: str = None):
    """Process mutual connections for a person"""
    try:
        async with browser_semaphore:
            logger.info(LogCategory.NETWORK, "mutual_connections_start", 
                       person=person, company=company, profile_url=profile_url)
            
            # Initialize browser
            playwright, browser, context, page = await initialize_browser()
            
            try:
                # Search for the profile
                search_results = await search_and_process_connections(
                    page, "mutual", company, person
                )
                
                if not search_results:
                    error_data = {
                        "person_name": person,
                        "company_name": company,
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "error": f"No results found for {person} at {company}"
                    }
                    save_to_cache(cache_filename, error_data)
                    logger.error(LogCategory.NETWORK, "mutual_connections_not_found",
                               person=person, company=company)
                    return error_data
                
                # Process the results
                result_data = {
                    "person_name": person,
                    "company_name": company,
                    "status": "complete",
                    "timestamp": datetime.now().isoformat(),
                    "results": search_results
                }
                
                save_to_cache(cache_filename, result_data)
                logger.info(LogCategory.NETWORK, "mutual_connections_complete",
                          person=person, company=company,
                          result_count=len(search_results))
                return result_data
                
            finally:
                await browser.close()
                await playwright.stop()
                
    except Exception as e:
        error_data = {
            "person_name": person,
            "company_name": company,
            "status": "error",
            "timestamp": datetime.now().isoformat(),
            "error": str(e)
        }
        save_to_cache(cache_filename, error_data)
        logger.error(LogCategory.NETWORK, "mutual_connections_failed",
                    error=e, person=person, company=company)
        return error_data

async def process_role_search(role: str, company: str, cache_filename: str):
    """Background task to process role search"""
    async with browser_semaphore:
        print(f"Browser slot acquired for role '{role}'. Starting processing.")
        try:
            # No need to check cache here
            print(f"Starting background processing for role '{role}' at company: {company} (Cache File: {cache_filename})")
            browser = None
            p = None
            try:
                browser, page, p = await initialize_browser()
                if not browser or not page:
                    raise Exception("Failed to initialize browser or login to LinkedIn")
                
                # Search for 1st and 2nd level connections matching the role
                first_degree = await search_and_process_connections(page, 'F', company=company, role=role)
                second_degree = await search_and_process_connections(page, 'S', company=company, role=role)
                third_degree = await search_and_process_connections(page, 'O', company=company, role=role)
                
                people = first_degree + second_degree + third_degree
                
                print(f"\nClosing browser... Found {len(people)} people for role '{role}' at {company}")
                
                # Save results to cache AND update job status
                result = {
                    "role": role,
                    "company": company,
                    "status": "complete",
                    "timestamp": datetime.now().isoformat(),
                    "people": people
                }
                save_to_cache(cache_filename, result)
                return result
                    
            except Exception as e:
                error_result = { "role": role, "company": company, "status": "error", "timestamp": datetime.now().isoformat(), "error": str(e) }
                save_to_cache(cache_filename, error_result)
            finally:
                if browser: await browser.close()
                if p: await p.stop()
        finally:
            print(f"Browser slot released for role '{role}'.")

async def process_find_connections_at_company_for_person(person_name: str, company_name: str, cache_filename: str, profile_url: str = None):
    """Background task to find connections of a person at a company."""
    async with browser_semaphore:
        print(f"Browser slot acquired for finding '{person_name}' connections at '{company_name}'.")
        try:
            browser = None
            p = None
            try:
                browser, page, p = await initialize_browser()
                if not browser or not page:
                    raise Exception("Failed to initialize browser or login to LinkedIn")

                # If profile URL is not provided, search for the person
                if not profile_url:
                    search_url = f"https://www.linkedin.com/search/results/people/?keywords={person_name}"
                    print(f"\nNavigating to search results: {search_url}")
                    await page.goto(search_url)
                    
                    # Wait for search results
                    await page.wait_for_selector('.search-results-container', timeout=30000)
                    await page.wait_for_timeout(2000)
                    
                    # Get all profile links
                    profile_links = await page.query_selector_all('a[href*="/in/"]')
                    if not profile_links:
                        raise Exception(f"Could not find any profiles for {person_name}")
                    
                    # Ensure we have exactly one result
                    if len(profile_links) > 1:
                        raise Exception(f"Found multiple profiles for {person_name}. Please provide a more specific name or the profile URL.")
                    
                    # Get the profile URL
                    profile_url = await profile_links[0].get_attribute('href')
                    if not profile_url:
                        raise Exception(f"Could not get profile URL for {person_name}")

                # Navigate to the profile
                print(f"\nNavigating to profile: {profile_url}")
                await page.goto(profile_url)
                await page.wait_for_timeout(2000)

                # Check if this is a 1st connection
                dist_value_element = await page.query_selector('.dist-value')
                if not dist_value_element:
                    raise Exception("Could not determine connection level")
                
                dist_value = await dist_value_element.text_content()
                dist_value = dist_value.strip()
                
                if dist_value != "1st":
                    raise Exception(f"Person must be a 1st degree connection in order to browse their connections at a company. Current connection level: {dist_value}")

                # Find the connectionOf parameter from the connections link
                connections_link = await page.query_selector('a[href*="search/results/people/?connectionOf"]')
                if not connections_link:
                    raise Exception("Could not find connections link")
                
                href = await connections_link.get_attribute('href')
                if not href:
                    raise Exception("Could not get connections URL")
                
                # Extract the connectionOf parameter
                import re
                match = re.search(r'connectionOf=(%5B%22[^%]+%22%5D)', href)
                if not match:
                    raise Exception("Could not extract connectionOf parameter")
                
                connection_of = match.group(1)
                
                # Construct URL for 2nd degree connections at the company
                search_url = f"https://www.linkedin.com/search/results/people/?company={company_name}&connectionOf={connection_of}&network=%5B%22S%22%5D&origin=FACETED_SEARCH"
                
                print(f"\nNavigating to filtered search: {search_url}")
                await page.goto(search_url)
                await page.wait_for_timeout(2000)

                # Extract the people using our common function
                people = await extract_people_from_page(page)
                
                result = {
                    "person_name": person_name,
                    "company_name": company_name,
                    "profile_url": profile_url,
                    "status": "complete",
                    "timestamp": datetime.now().isoformat(),
                    "people": people
                }
                save_to_cache(cache_filename, result)
                return result

            finally:
                if browser:
                    await browser.close()
                if p:
                    await p.stop()

        except Exception as e:
            error_result = {
                "person_name": person_name,
                "company_name": company_name,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            save_to_cache(cache_filename, error_result)

# Add a new endpoint to get rate limit information
@app.get("/rate_limits")
@log_operation(LogCategory.API, "get_rate_limits")
async def get_rate_limits():
    """Get current rate limit information for all operations"""
    operations = ["linkedin_profile", "linkedin_search", "browser_init", "api_request"]
    return {
        "rate_limits": [rate_limiter.get_rate_limit_info(op) for op in operations],
        "timestamp": datetime.now().isoformat()
    }

if __name__ == "__main__":
    # Normal server startup (browser installation check is handled at the top)
    uvicorn.run(app, host="127.0.0.1", port=8001)

def main():
    """Entry point for the console script"""
    import uvicorn
    
    # Browser installation check is handled at the top of the file
    print("Starting LinkedIn Network Builder...")
    print("Server will be available at: http://127.0.0.1:8001")
    print("API documentation at: http://127.0.0.1:8001/docs")
    print("Press Ctrl+C to stop the server")
    uvicorn.run(app, host="127.0.0.1", port=8001)

