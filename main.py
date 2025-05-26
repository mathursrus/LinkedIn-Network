import sys
import asyncio
import json
import os
from datetime import datetime

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

from fastapi import FastAPI, Query, BackgroundTasks
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

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

def get_cache_filename(company: str, person: str = None) -> str:
    """Get the cache filename for a company or person-company combination"""
    if person:
        return f"{person.replace(' ', '_')}_{company.replace(' ', '_')}-Mutual-Connections.json"
    return f"{company.replace(' ', '_')}-Connections.json"

def save_to_cache(filename: str, data: dict):
    """Save data to cache file"""
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)

def load_from_cache(filename: str) -> dict:
    """Load data from cache file"""
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return None

def get_processing_message(company: str, person: str = None) -> dict:
    """Get the processing message for a search"""
    if person:
        return {
            "message": f"Processing in progress for mutual connections between {person} and {company}. Please try again in a few minutes.",
            "status": "processing"
        }
    return {
        "message": f"Processing in progress for {company}. Please try again in a few minutes.",
        "status": "processing"
    }

def handle_cached_results(cached_data: dict, company: str, person: str = None) -> dict:
    """Handle cached results and determine if we should retry"""
    if not cached_data:
        return None
        
    if cached_data.get('status') == 'complete':
        return cached_data
        
    if cached_data.get('status') == 'processing':
        return get_processing_message(company, person)
        
    # If we get here, the previous attempt failed
    print(f"Previous attempt for {person + ' at ' if person else ''}{company} failed. Retrying...")
    return None

def mark_as_processing(company: str):
    """Mark a company as being processed"""
    processing_data = {
        "company": company,
        "status": "processing",
        "timestamp": datetime.now().isoformat(),
        "message": f"Processing started for {company}. Please try again in a few minutes."
    }
    save_to_cache(get_cache_filename(company), processing_data)

async def extract_people_from_page(page):
    """Helper function to extract people information from a LinkedIn page"""
    try:
        # Wait for search results container
        await page.wait_for_selector('.search-results-container', timeout=30000)
        print("Search results container found")
        
        # Wait a bit more for dynamic content
        await page.wait_for_timeout(5000)

        # Try multiple possible selectors that LinkedIn might use
        selectors = [
            '.qMGLeKnJyQnibGOueKodvnfLgWpsuA',  # People block class
            'ul[role="list"] > li',  # Fallback to list items
            '.entity-result',  # Fallback to entity result
            '.search-result'   # Fallback to search result
        ]
        
        blocks = []
        for selector in selectors:
            print(f"\nTrying selector: {selector}")
            blocks = await page.query_selector_all(selector)
            print(f"Found {len(blocks)} blocks with selector {selector}")
            if len(blocks) > 0:
                break

        mypeople = []
        # Process all blocks
        for block in blocks:
            # Skip the banner/ad result
            if await block.evaluate("el => el.querySelector('.search-nec__banner-card')"):
                print("Skipping banner/ad result")
                continue
                
            # Extract person information using evaluate
            result = await block.evaluate("""el => {
                // Get name using the specific class within the name block
                const nameBlock = el.querySelector('.kmApjJVnFerynwITxTBSCqzqgoHwVfkiA.HHGiVqODTCkszDUDWwPGPJGUPfAeRpygAKwwLePrQ');
                const nameEl = nameBlock ? nameBlock.querySelector('.sDWEFrcVubKuUVGggeBOYqLlgYgPbojOc') : null;
                const name = nameEl ? nameEl.innerText.trim().split('\\n')[0] : 'Unknown';
                
                // Get role using the specific class
                const roleEl = el.querySelector('.kFTZPhxHBbvnnRxiRPmTxafKGLUNSiaeInag');
                const role = roleEl ? roleEl.innerText.trim() : 'Unknown';
                
                // Get location using the specific class
                const locationEl = el.querySelector('.FlWUwyrEUZpkVCgzGTDwUHTLntfZNseavlY');
                const location = locationEl ? locationEl.innerText.trim() : 'Unknown';
                    
                // Get profile URL
                const profileLink = el.querySelector('a[href*="/in/"]');
                const profileUrl = profileLink ? profileLink.href : null;
            
                // Only return if we found a valid name
                if (name === 'Unknown') {
                    return null;
                }
                
                return {
                    name: name,
                    role: role,
                    location: location,
                    profile_url: profileUrl
                };
            }""")
            
            if result:
                mypeople.append(result)
        
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
            await page.wait_for_selector('.ph5.pb5', timeout=15000)
            
            # Find the profile block
            profile_block = await page.query_selector('.ph5.pb5')
            if not profile_block:
                print("Could not find profile block")
                return []
                
            # Find the mutual connections link within the profile block
            mutual_connections_link = await profile_block.query_selector('a.sDWEFrcVubKuUVGggeBOYqLlgYgPbojOc')
            print(f"Mutual connections link: {mutual_connections_link}")
            
            if mutual_connections_link:
                # Get the href attribute
                href = await mutual_connections_link.get_attribute('href')
                if href:
                    # Navigate to the mutual connections page
                    await page.goto(href)
                    await page.wait_for_timeout(2000)  # Wait for page to load
                    
                    # Extract mutual connections using the common extraction function
                    mutual_connections = await extract_people_from_page(page)
                    print("mutual_connections", mutual_connections)
                    return mutual_connections
            else:
                print("Could not find mutual connections link")
                return []
                
        except Exception as e:
            print(f"Error fetching mutual connections: {e}")
            return []
        
    except Exception as e:
        print(f"Error navigating to profile: {e}")
        return []

async def search_and_process_connections(page, company, network_type):
    """Helper function to search and process connections of a specific type"""
    search_url = f"https://www.linkedin.com/search/results/people/?company={company}&network=%5B%22{network_type}%22%5D"
    print(f"\nNavigating to {network_type} level connections: {search_url}")
    await page.goto(search_url)
    
    mypeople = await extract_people_from_page(page)
    processed_people = []
    
    # Process all people found
    for person in mypeople:
        person['connection_level'] = 1 if network_type == 'F' else 2
        print(f"\nProcessing: {person['name']}")
        print(f"Role: {person['role']}")
        print(f"Location: {person['location']}")
        print(f"Connection Level: {person['connection_level']}")
        
        # For 2nd-degree connections, fetch mutual connections
        if network_type == 'S' and person['profile_url']:
            print(f"Fetching mutual connections for {person['name']}...")
            person['mutual_connections'] = await get_mutual_connections_for_profile(page, person['profile_url'])
            print(f"Found {len(person['mutual_connections'])} mutual connections")
        
        processed_people.append(person)
    
    print(f"\nProcessed {len(processed_people)} {network_type}-degree connections")
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

async def process_company_connections(company: str):
    """Background task to process company connections"""
    print(f"Starting background processing for company: {company}")
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
            save_to_cache(get_cache_filename(company), error_result)
            return error_result
        
        try:
            # Search for 1st level connections
            first_degree = await search_and_process_connections(page, company, 'F')
            
            # Search for 2nd level connections
            second_degree = await search_and_process_connections(page, company, 'S')
            
            # Combine all results
            people = first_degree + second_degree
            
            print("\nClosing browser...")
            await browser.close()
            await p.stop()
            print("Done!")
            print(f"Total people found: {len(people)}")
            print(people)
            
            # Save results to cache
            result = {
                "company": company,
                "status": "complete",
                "timestamp": datetime.now().isoformat(),
                "people": people
            }
            save_to_cache(get_cache_filename(company), result)
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
        save_to_cache(get_cache_filename(company), error_result)
        if browser:
            await browser.close()
        if p:
            await p.stop()
        raise e

@app.get("/browse_company_people")
async def browse_public_linkedin(company: str, background_tasks: BackgroundTasks):
    """Get people at a company from LinkedIn"""
    cache_filename = get_cache_filename(company)
    cached_data = load_from_cache(cache_filename)
    
    # Check cached results
    result = handle_cached_results(cached_data, company)
    if result:
        return result
    
    # If no cache exists or previous attempt failed, mark as processing and start background processing
    mark_as_processing(company)
    background_tasks.add_task(process_company_connections, company)
    return get_processing_message(company)

@app.get("/find_mutual_connections")
async def find_mutual_connections(person: str, company: str, background_tasks: BackgroundTasks):
    """Find mutual connections between a person and a company"""
    cache_filename = get_cache_filename(company, person)
    cached_data = load_from_cache(cache_filename)
    
    # Check cached results
    result = handle_cached_results(cached_data, company, person)
    if result:
        return result
    
    # If no cache exists or previous attempt failed, mark as processing and start background processing
    processing_data = {
        "person": person,
        "company": company,
        "status": "processing",
        "timestamp": datetime.now().isoformat(),
        "message": f"Processing started for mutual connections between {person} and {company}. Please try again in a few minutes."
    }
    save_to_cache(cache_filename, processing_data)
    background_tasks.add_task(process_mutual_connections, person, company, cache_filename)
    return get_processing_message(company, person)

async def process_mutual_connections(person: str, company: str, cache_filename: str):
    """Background task to process mutual connections"""
    print(f"Starting mutual connections processing for {person} at {company}")
    browser = None
    p = None
    try:
        browser, page, p = await initialize_browser()
        if not browser or not page:
            error_result = {
                "person": person,
                "company": company,
                "status": "error",
                "timestamp": datetime.now().isoformat(),
                "error": "Failed to initialize browser or login to LinkedIn"
            }
            with open(cache_filename, 'w') as f:
                json.dump(error_result, f, indent=2)
            return error_result
        
        try:
            # Search for the person at the company
            search_url = f"https://www.linkedin.com/search/results/people/?keywords={person}&origin=GLOBAL_SEARCH_HEADER&company={company}"
            print(f"\nNavigating to search results: {search_url}")
            await page.goto(search_url)
            
            # Wait for search results
            await page.wait_for_selector('.search-results-container', timeout=30000)
            await page.wait_for_timeout(5000)
            
            # Find the person's profile link
            profile_link = await page.query_selector('a[href*="/in/"]')
            if not profile_link:
                raise Exception(f"Could not find profile for {person} at {company}")
            
            # Get the profile URL
            profile_url = await profile_link.get_attribute('href')
            if not profile_url:
                raise Exception(f"Could not get profile URL for {person}")
            
            # Get mutual connections using the shared function
            mutual_connections = await get_mutual_connections_for_profile(page, profile_url)
            
            print("\nClosing browser...")
            await browser.close()
            await p.stop()
            print("Done!")
            print(f"Total mutual connections found: {len(mutual_connections)}")
            
            # Save results to cache
            result = {
                "person": person,
                "company": company,
                "status": "complete",
                "timestamp": datetime.now().isoformat(),
                "mutual_connections": mutual_connections
            }
            with open(cache_filename, 'w') as f:
                json.dump(result, f, indent=2)
            
            return result
            
        finally:
            if browser:
                await browser.close()
            if p:
                await p.stop()
            
    except Exception as e:
        # If there's an error, save error state to cache
        error_result = {
            "person": person,
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

