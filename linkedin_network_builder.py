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

# Load environment variables from .env file
load_dotenv()

# Define and create the cache directory
CACHE_DIR = os.getenv("LINKEDIN_CACHE_DIR", "cache")
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

def save_to_cache(filename, data):
    """Save data to cache file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_from_cache(filename: str) -> dict:
    """Load data from cache file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return None

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

def mark_as_processing(**kwargs):
    """Mark a query as being processed by creating a cache file."""
    cache_filename = get_cache_filename(**kwargs)
    processing_data = { "status": "processing", "timestamp": datetime.now().isoformat() }
    # Add all original parameters to the processing file for context
    processing_data.update(kwargs)
    save_to_cache(cache_filename, processing_data)

async def extract_people_from_page(page):
    """Helper function to extract people information from a LinkedIn page using consistent DOM structure"""
    try:
        await page.wait_for_selector('.search-results-container', timeout=30000)
        print("Search results container found")
        await page.wait_for_timeout(5000)

        blocks = await page.query_selector_all('[data-view-name="search-entity-result-universal-template"]')
        print(f"Found {len(blocks)} person blocks")

        mypeople = []
        for block in blocks:
            try:
                # Name: first <span aria-hidden="true"> inside <a href*="/in/">
                name_elem = await block.query_selector('a[href*="/in/"] span[aria-hidden="true"]')
                if not name_elem:
                    print("Could not find name element")
                    continue
                    
                name = await name_elem.inner_text()
                
                # Profile URL from <a href>
                profile_link_elem = await block.query_selector('a[href*="/in/"]')
                profile_url = await profile_link_elem.get_attribute('href') if profile_link_elem else ""

                # Get the parent div of the name element and its siblings
                # Do this in a single evaluate to maintain node references
                info = await name_elem.evaluate('''
                    node => {
                        const nameParentDiv = node.closest('div');
                        const parentContainer = nameParentDiv.parentNode;
                        const roleDiv = parentContainer.nextElementSibling;
                        const locationDiv = roleDiv ? roleDiv.nextElementSibling : null;
                        return {
                            role: roleDiv ? roleDiv.textContent.trim() : '',
                            location: locationDiv ? locationDiv.textContent.trim() : ''
                        };
                    }
                ''')
                
                if name:
                    mypeople.append({
                        "name": name.strip(),
                        "profile_url": profile_url,
                        "role": info['role'],
                        "location": info['location']
                    })
            except Exception as e:
                print(f"Error processing block: {e}")
                continue
                
        return mypeople
    except Exception as e:
        print(f"Error extracting people from page: {e}")
        return []

async def get_mutual_connections_for_profile(page, profile_url):
    """Shared function to get mutual connections for a profile"""
    try:
        print(f"\nFetching mutual connections for: {profile_url}")
        await page.goto(profile_url)
        
        try:
            # Wait for the profile section to load
            await page.wait_for_selector('a[data-test-app-aware-link][href*="/search/results/people/"]', timeout=15000)
            
            # Find the mutual connections link within the profile block - an a class element with a href attribute that contains /search/results/people/
            mutual_connections_link = await page.query_selector('a[data-test-app-aware-link][href*="/search/results/people/"]')
            
            if mutual_connections_link:
                # Get the href attribute
                href = await mutual_connections_link.get_attribute('href')
                print(f"Mutual connections link is: {href}")
            
                if href:
                    # Navigate to the mutual connections page
                    await page.goto(href)
                    await page.wait_for_timeout(2000)  # Wait for page to load
                    
                    # Extract mutual connections using the common extraction function
                    mutual_connections = await navigate_all_pages(page, extract_people_from_page)
                    print("mutual_connections", mutual_connections)
                    return mutual_connections
            else:
                print("Could not find mutual connections link")
                return []
                
        except Exception as e:
            print(f"Error fetching mutual connections: {e}")
            raise e
        
    except Exception as e:
        print(f"Error navigating to profile: {e}")
        raise e



async def navigate_all_pages(page, extraction_function, max_pages=None):
    """Navigate through all pages by incrementing the &page= param in the URL and extract data."""
    import re
    all_results = []
    current_page = 1
    # Extract the base URL (without &page=...)
    url = page.url
    print(f"Starting navigation with URL: {url}")
    # Remove any existing &page=... param
    url = re.sub(r'([&?])page=\d+', '', url)
    # Ensure we have a separator
    sep = '&' if '?' in url else '?'
    while True:
        paged_url = f"{url}{sep}page={current_page}"
        print(f"Navigating to: {paged_url}")
        await page.goto(paged_url)
        await page.wait_for_timeout(2000)
        page_results = await extraction_function(page)
        print(f"Page {current_page} results: {len(page_results)}")
        if not page_results:
            print("No more results, stopping.")
            break
        all_results.extend(page_results)
        if max_pages and current_page >= max_pages:
            break
        current_page += 1
    return all_results

async def search_and_process_connections(page, network_type: str, company: str = None, role: str = None):
    """
    Helper function to search and process connections of a specific type,
    with optional filtering by company and role.
    Now supports multi-page extraction.
    """
    # Build the search URL
    base_url = "https://www.linkedin.com/search/results/people/?"
    params = {
        "network": f'["{network_type}"]'  # F for 1st, S for 2nd, T for 3rd
    }
    if company:
        params["company"] = company
    if role:
        params["title"] = role
    from urllib.parse import urlencode
    query_string = urlencode(params)
    search_url = f"{base_url}{query_string}"
    print(f"\nNavigating to search: {search_url}")
    await page.goto(search_url)
    # Use pagination-aware extraction
    all_people = await navigate_all_pages(page, extract_people_from_page, max_pages=10)
    processed_people = []
    for person in all_people:
        person['connection_level'] = 1 if network_type == 'F' else 2 if network_type == 'S' else 3
        print(f"\nProcessing: {person['name']} ({person.get('role', 'N/A')})")
        if network_type == 'S' and person.get('profile_url'):
            print(f"Fetching mutual connections for {person['name']}...")
            person['mutual_connections'] = await get_mutual_connections_for_profile(page, person['profile_url'])
            print(f"Found {len(person.get('mutual_connections', []))} mutual connections")
        processed_people.append(person)
    print(f"\nProcessed {len(processed_people)} {network_type}-degree connections across all pages.")
    return processed_people

async def initialize_browser():
    """Shared function to initialize browser and handle LinkedIn login"""
    print("Launching browser...")
    try:
        # Set persistent browser location for PyInstaller compatibility
        persistent_browser_path = os.path.join(os.path.expanduser("~"), ".playwright-browsers")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = persistent_browser_path
        
        # For PyInstaller executables, we need to handle the playwright installation differently
        p = await async_playwright().start()
        
        # Try to launch browser, but if it fails due to missing browsers, install them
        try:
            # Launch browser with explicit settings for PyInstaller
            browser = await p.chromium.launch(
                headless=False,
                # Add explicit args to help with subprocess creation in PyInstaller
                args=[
                    '--no-sandbox',
                    '--disable-dev-shm-usage',
                    '--disable-gpu',
                    '--disable-web-security',
                    '--disable-features=VizDisplayCompositor'
                ]
            )
        except Exception as browser_error:
            print(f"Browser launch failed: {browser_error}")
            if "Executable doesn't exist" in str(browser_error):
                print("Installing browsers automatically...")
                # Try to install browsers
                install_success = await install_browsers()
                if install_success:
                    print("Retrying browser launch...")
                    # Try launching again after installation
                    browser = await p.chromium.launch(
                        headless=False,
                        args=[
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-gpu',
                            '--disable-web-security',
                            '--disable-features=VizDisplayCompositor'
                        ]
                    )
                else:
                    print("Browser installation failed. Please run with --install-browsers flag first.")
                    await p.stop()
                    return None, None, None
            else:
                # Re-raise if it's a different error
                await p.stop()
                raise browser_error
        
        # Try to load existing browser state, but don't fail if it doesn't exist
        try:
            context = await browser.new_context(
                storage_state="./browser_state.json"
            )
        except FileNotFoundError:
            print("No existing browser state found, starting fresh...")
            context = await browser.new_context()
            
        page = await context.new_page()

        # First, go to LinkedIn homepage
        print("Navigating to LinkedIn...")
        await page.goto("https://www.linkedin.com")
        
        # Check if we're already logged in
        try:
            await page.wait_for_selector('.feed-shared-update-v2', timeout=5000)
            print("Already logged in!")
            return browser, page, p
        except:
            # Wait for user to log in
            print("\nPlease log in to LinkedIn in the browser window.")
            print("The script will continue automatically after login...")
            
            # Wait for the feed to appear, which indicates successful login
            try:
                await page.wait_for_selector('.feed-shared-update-v2', timeout=120000)  # 2 minute timeout
                print("Login detected! Saving browser state...")
                # Save the browser state immediately after login
                await context.storage_state(path="./browser_state.json")
                print("Browser state saved for future use")
                return browser, page, p
            except Exception as e:
                print("Login timeout. Please try again.")
                # Don't close the browser here, just return None to indicate login failed
                return None, None, None
        
    except Exception as e:
        print(f"Error initializing browser: {str(e)}")
        print("This might be due to missing browser files. Playwright will download them on first run.")
        try:
            if 'browser' in locals():
                await browser.close()
        except:
            pass
        try:
            if 'p' in locals():
                await p.stop()
        except:
            pass
        return None, None, None

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
                        "results": people
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

async def process_entire_network(cache_filename: str):
    """Background task to crawl all 1st and 2nd degree connections and their mutual connections."""
    async with browser_semaphore:
        print(f"Browser slot acquired for entire network crawl. Starting processing.")
        try:
            browser = None
            p = None
            try:
                browser, page, p = await initialize_browser()
                if not browser or not page:
                    error_result = {
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "error": "Failed to initialize browser or login to LinkedIn"
                    }
                    save_to_cache(cache_filename, error_result)
                    return error_result
                try:
                    # Search for 1st degree connections
                    first_degree = await search_and_process_connections(page, 'F')
                    # Search for 2nd degree connections
                    second_degree = await search_and_process_connections(page, 'S')
                    # Combine all results
                    people = first_degree + second_degree
                    print("\nClosing browser...")
                    await browser.close()
                    await p.stop()
                    print("Done!")
                    print(f"Total people found: {len(people)}")
                    # Save results to cache AND update job status
                    result = {
                        "status": "complete",
                        "timestamp": datetime.now().isoformat(),
                        "results": people
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
                    "status": "error",
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)
                }
                save_to_cache(cache_filename, error_result)
                raise e
        finally:
            print(f"Browser slot released for entire network crawl.")

@app.get("/get_assistant_config")
async def get_assistant_config():
    return {"assistant_id": ASSISTANT_ID, "openai_api_key": openai_api_key}

@app.get("/who_do_i_know_at_company")
async def browse_public_linkedin(company: str, background_tasks: BackgroundTasks):
    """Get people at a company from LinkedIn"""
    query_params = {"query_name": "company_people_search", "company": company}
    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)
    
    mark_as_processing(**query_params)
    background_tasks.add_task(process_company_connections, company, cache_filename)
    return get_processing_message(**query_params)

@app.get("/who_works_as_role_at_company")
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

@app.get("/crawl_my_entire_network")
async def crawl_my_entire_network(background_tasks: BackgroundTasks):
    """Crawl all 1st and 2nd degree connections and their mutual connections."""
    query_params = {"query_name": "entire_network_crawl"}
    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)
    mark_as_processing(**query_params)
    background_tasks.add_task(process_entire_network, cache_filename)
    return get_processing_message(**query_params)

@app.get("/who_can_introduce_me_to_person")
async def find_mutual_connections(background_tasks: BackgroundTasks, profile_url: str = None, person: str = None, company: str = None):
    """Search for mutual connections with a person.
    Either provide:
    1. profile_url - direct link to person's LinkedIn profile, OR
    2. person AND company - to search for the person at that company"""
    
    if not profile_url and (not person or not company):
        raise HTTPException(
            status_code=400, 
            detail="Must provide either 'profile_url' OR both 'person' and 'company'"
        )

    # If profile_url is provided, ignore person and company
    query_params = {
        "query_name": "mutual_connections",
        "profile_url": profile_url
    } if profile_url else {
        "query_name": "mutual_connections",
        "person": person,
        "company": company
    }
    
    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)

    mark_as_processing(**query_params)
    background_tasks.add_task(process_mutual_connections, person if not profile_url else None, company if not profile_url else None, cache_filename, profile_url)
    return get_processing_message(**query_params)

@app.get("/who_does_person_know_at_company")
async def find_connections_at_company_for_person(background_tasks: BackgroundTasks, profile_url: str = None, person_name: str = None, company_name: str = None):
    """Find who a specific person knows at a company.
    Either provide:
    1. profile_url - direct link to person's LinkedIn profile, OR
    2. person_name AND company_name - to search for the person at that company"""
    
    if not profile_url and (not person_name or not company_name):
        raise HTTPException(
            status_code=400, 
            detail="Must provide either 'profile_url' OR both 'person_name' and 'company_name'"
        )

    # If profile_url is provided, ignore person_name
    query_params = {
        "query_name": "connections_through_person",
        "profile_url": profile_url,
        "company_name": company_name  # Note: company_name is always needed to filter connections
    } if profile_url else {
        "query_name": "connections_through_person",
        "person_name": person_name,
        "company_name": company_name
    }

    cache_filename = get_cache_filename(**query_params)
    cached_data = load_from_cache(cache_filename)
    if cached_data:
        if cached_data.get('status') == 'complete':
            return cached_data
        elif cached_data.get('status') == 'processing':
            return get_processing_message(**query_params)

    mark_as_processing(**query_params)
    background_tasks.add_task(process_find_connections_at_company_for_person, person_name if not profile_url else None, company_name, cache_filename, profile_url)
    return get_processing_message(**query_params)

async def process_mutual_connections(person: str, company: str, cache_filename: str, profile_url: str = None):
    """Background task to process mutual connections"""
    async with browser_semaphore:
        print(f"Browser slot acquired for mutual connections with '{profile_url if profile_url else person} at {company}'. Starting processing.")
        try:
            # No need to check cache here
            print(f"Starting mutual connections processing for {profile_url if profile_url else person} at {company} (Cache File: {cache_filename})")
            browser = None
            p = None
            try:
                browser, page, p = await initialize_browser()
                if not browser or not page:
                    error_result = {
                        "profile_url": profile_url if profile_url else None,
                        "person": person if not profile_url else None,
                        "company": company if not profile_url else None,
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "error": "Failed to initialize browser or login to LinkedIn"
                    }
                    with open(cache_filename, 'w') as f:
                        json.dump(error_result, f, indent=2)
                    return error_result

                try:
                    navigate_to_url = profile_url
                    # Search for the person at the company or use provided URL
                    if not navigate_to_url:
                        search_url = f"https://www.linkedin.com/search/results/people/?keywords={person}&origin=GLOBAL_SEARCH_HEADER&company={company}"
                        print(f"\nNavigating to search results: {search_url}")
                        await page.goto(search_url)
                        
                        # Wait for search results
                        await page.wait_for_selector('.search-results-container', timeout=30000)
                        await page.wait_for_timeout(5000)
                        
                        # ensure there is only 1 result
                        results = await page.query_selector_all('[data-view-name="search-entity-result-universal-template"]')
                        if len(results) > 1:
                            raise Exception(f"Found multiple profiles for {person} at {company}. Please provide their LinkedIn profile URL to avoid ambiguity.")
                        elif len(results) == 0:
                            raise Exception(f"Could not find profile for {person} at {company}. Please provide their LinkedIn profile URL.")
                        
                        # Find the person's profile link
                        profile_link = await results[0].query_selector('a[href*="/in/"]')
                        if not profile_link:
                            raise Exception(f"Could not find profile for {person} at {company}. Please provide their LinkedIn profile URL.")
                        
                        # Get the profile URL
                        navigate_to_url = await profile_link.get_attribute('href')
                        if not navigate_to_url:
                            raise Exception(f"Could not get profile URL for {person} at {company}. Please provide their LinkedIn profile URL.")

                    # Get mutual connections using the shared function
                    mutual_connections = await get_mutual_connections_for_profile(page, navigate_to_url)

                    print("\nClosing browser...")
                    await browser.close()
                    await p.stop()
                    print("Done!")
                    print(f"Total mutual connections found: {len(mutual_connections)}")
                    
                    # Save results to cache
                    result = {
                        "profile_url": profile_url if profile_url else None,
                        "person": person if not profile_url else None,
                        "company": company if not profile_url else None,
                        "status": "complete",
                        "timestamp": datetime.now().isoformat(),
                        "results": mutual_connections
                    }
                    with open(cache_filename, 'w') as f:
                        json.dump(result, f, indent=2)
                    
                    return result

                except Exception as e:
                    raise e
                finally:
                    if browser:
                        await browser.close()
                    if p:
                        await p.stop()

            except Exception as e:
                raise e

        except Exception as e:
            # If there's an error, save error state to cache
            error_result = {
                "profile_url": profile_url,
                "person": person if not profile_url else None,
                "company": company,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            with open(cache_filename, 'w') as f:
                json.dump(error_result, f, indent=2)
            if browser:
                await browser.close()
            if p:
                await p.stop()
            raise e
        finally:
            print(f"Browser slot released for mutual connections with '{profile_url if profile_url else person}'.")

async def process_find_connections_at_company_for_person(person_name: str, company_name: str, cache_filename: str, profile_url: str = None):
    """Background task to find connections of a person at a company."""
    async with browser_semaphore:
        print(f"Browser slot acquired for finding connections at '{company_name}' for '{profile_url if profile_url else person_name}'.")
        try:
            browser = None
            p = None
            try:
                browser, page, p = await initialize_browser()
                if not browser or not page:
                    error_result = {
                        "profile_url": profile_url if profile_url else None,
                        "person_name": person_name if not profile_url else None,
                        "company_name": company_name,
                        "status": "error",
                        "timestamp": datetime.now().isoformat(),
                        "error": "Failed to initialize browser or login to LinkedIn"
                    }
                    with open(cache_filename, 'w') as f:
                        json.dump(error_result, f, indent=2)
                    return error_result

                try:
                    navigate_to_url = profile_url
                    # Navigate to profile or search for person
                    if not profile_url:
                        search_url = f'https://www.linkedin.com/search/results/people/?keywords={person_name}&origin=GLOBAL_SEARCH_HEADER&network=%5B"F"%5D'
                        await page.goto(search_url)
                        
                        # Wait for search results
                        await page.wait_for_selector('.search-results-container', timeout=30000)
                        await page.wait_for_timeout(5000)
                        
                        # ensure there is only 1 result
                        results = await page.query_selector_all('[data-view-name="search-entity-result-universal-template"]')
                        if len(results) > 1:
                            raise Exception(f"Found multiple profiles for {person_name}. Please provide their LinkedIn profile URL to avoid ambiguity.")
                        elif len(results) == 0:
                            raise Exception(f"Could not find profile for {person_name}. Remember you can only look at connections of people who you are directly connected to.")
                        
                        # Find the person's profile link
                        profile_link = await results[0].query_selector('a[href*="/in/"]')
                        if not profile_link:
                            raise Exception(f"Could not find profile for {person_name}")
                        
                        # Get the profile URL
                        navigate_to_url = await profile_link.get_attribute('href')
                        if not navigate_to_url:
                            raise Exception(f"Could not get profile URL for {person_name}")
                        
                    await page.goto(navigate_to_url)

                    # Get connections at company
                    connections = await connections_at_company_for_person(page, company_name)

                    result = {
                        "profile_url": profile_url if profile_url else None,
                        "person_name": person_name if not profile_url else None,
                        "company_name": company_name,
                        "status": "complete",
                        "timestamp": datetime.now().isoformat(),
                        "results": connections
                    }
                    with open(cache_filename, 'w') as f:
                        json.dump(result, f, indent=2)
                    return result

                except Exception as e:
                    raise e
                finally:
                    if browser:
                        await browser.close()
                    if p:
                        await p.stop()

            except Exception as e:
                raise e

        except Exception as e:
            error_result = {
                "profile_url": profile_url,
                "person_name": person_name if not profile_url else None,
                "company_name": company_name,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": str(e)
            }
            with open(cache_filename, 'w') as f:
                json.dump(error_result, f, indent=2)
            if browser:
                await browser.close()
            if p:
                await p.stop()
            raise e
        finally:
            print(f"Browser slot released for finding connections at '{company_name}' for '{profile_url if profile_url else person_name}'.")

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
                
                # Search for 1st, 2nd, and 3rd degree connections matching the role
                first_degree = await search_and_process_connections(page, 'F', company=company, role=role)
                second_degree = await search_and_process_connections(page, 'S', company=company, role=role)
                third_degree = await search_and_process_connections(page, 'T', company=company, role=role)
                
                people = first_degree + second_degree + third_degree

                # if no people are found, return an error
                if len(people) == 0:
                    raise Exception(f"No people found for role '{role}' at {company}")
                
                print(f"\nClosing browser... Found {len(people)} people for role '{role}' at {company}")
                
                # Save results to cache AND update job status
                result = {
                    "role": role,
                    "company": company,
                    "status": "complete",
                    "timestamp": datetime.now().isoformat(),
                    "results": people
                }
                save_to_cache(cache_filename, result)
                return result
                    
            except Exception as e:
                error_result = { "role": role, "company": company, "status": "error", "timestamp": datetime.now().isoformat(), "error": str(e) }
                save_to_cache(cache_filename, error_result)
                raise e
            finally:
                if browser: await browser.close()
                if p: await p.stop()
        finally:
            print(f"Browser slot released for role '{role}'.")

async def connections_at_company_for_person(page, company_name):
    try:
        print("Looking for connections link...")
        connections_link_selector = 'a[href*="?connectionOf="]'
        await page.wait_for_selector(connections_link_selector, timeout=30000)
        connections_url = await page.get_attribute(connections_link_selector, 'href')
        if not connections_url:
            raise Exception(f"Could not find connections URL from {page.url}.")
        await page.goto(f"https://www.linkedin.com{connections_url}&company={company_name}", wait_until="load", timeout=60000)

        #print("Applying 'Current company' filter...")
        #await page.get_by_role("button", name="Current company").click()
        
        # 4. Type the company name into the input box.
        #print(f"Typing company name '{company_name}' into filter...")
        #company_input_selector = 'input[aria-label^="Add a company"]'
        #await page.wait_for_selector(company_input_selector, timeout=10000)
        #await page.fill(company_input_selector, company_name)

        # 5. Click the first result in the listbox that shows up.
        #print("Selecting first company from listbox...")
        #listbox_option_selector = '[role="listbox"]'
        #await page.wait_for_selector(listbox_option_selector, timeout=10000)
        # hit the down arrow once followed by enter
        #await page.keyboard.press("ArrowDown")
        #await page.keyboard.press("Enter")
        
        # 6. Click the "Show results" button.
        #print("Clicking 'Show results' button...")
        #await page.get_by_role("button", name="Show results").click()

        # 7. Wait for results to refresh and extract.
        print("Waiting for filtered results to load...")
        await page.wait_for_selector('.search-results-container', timeout=30000)
        
        print("Extracting people from final results page...")
        people = await navigate_all_pages(page, extract_people_from_page)
        return people

    except Exception as e:
        print(f"An error occurred in find_connections_at_company_for_person: {e}")
        return None, str(e)

if __name__ == "__main__":
    # Normal server startup (browser installation check is handled at the top)
    uvicorn.run(app, host="127.0.0.1", port=8001)

