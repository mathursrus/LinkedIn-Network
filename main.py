import sys
import asyncio
if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

from fastapi import FastAPI, Query
from playwright.async_api import async_playwright
import uvicorn

app = FastAPI()

@app.get("/browse_company_people")
async def browse_public_linkedin(company: str):
    print(f"Starting search for company: {company}")
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=False)
        
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
            except Exception as e:
                print("Login timeout. Please try again.")
                await browser.close()
                return {"error": "Login timeout"}
        
        # Now search for the company
        people = []
        
        async def search_and_process_connections(network_type):
            """Helper function to search and process connections of a specific type"""
            search_url = f"https://www.linkedin.com/search/results/people/?company={company}&network=%5B%22{network_type}%22%5D"
            print(f"\nNavigating to {network_type} level connections: {search_url}")
            await page.goto(search_url)
            print("Waiting for page to load...")
            
            try:
                await page.wait_for_selector('.search-results-container', timeout=30000)
                print("Search results container found")
                
                # Wait a bit more for dynamic content
                await page.wait_for_timeout(5000)

                print("Searching for people blocks...")
                # Try multiple possible selectors that LinkedIn might use
                selectors = [
                    '.mNBaKQkotJGQRotzYwFJYtULaUkikHZaIOkKY',  # People block class
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

                # Process all blocks
                for block in blocks:
                    # Skip the banner/ad result
                    if await block.evaluate("el => el.querySelector('.search-nec__banner-card')"):
                        print("Skipping banner/ad result")
                        continue
                        
                    # Extract name and role using evaluate
                    result = await block.evaluate("""el => {
                        // Get name using the specific class within the name block
                        const nameBlock = el.querySelector('.CyUFviNsZSgCGQsFYbTjPJGonmDMfMbppOo.RALeCNaydRdPJlTZVGwAhCrjZrXgIIiLAoQ');
                        const nameEl = nameBlock ? nameBlock.querySelector('.scbZDdHASaspEUgpeaTPqGoNBLbulnZdkpWE') : null;
                        const name = nameEl ? nameEl.innerText.trim().split('\\n')[0] : 'Unknown';
                        
                        // Get role using the specific class
                        const roleEl = el.querySelector('.pxUtFAnNAlQUqKbhgaSFYXfZujHHeMMyHYkPM');
                        const role = roleEl ? roleEl.innerText.trim() : 'Unknown';
                        
                        // Get location using the specific class
                        const locationEl = el.querySelector('.dckMfiyJszFLylsZdQUdDdjNLVwdiBBmvz');
                        const location = locationEl ? locationEl.innerText.trim() : 'Unknown';
                        
                        // Only return if we found a valid name
                        if (name === 'Unknown') {
                            return null;
                        }
                        
                        return {
                            name: name,
                            role: role,
                            location: location
                        };
                    }""")
                    
                    if result:
                        print(f"Name: {result['name']}")
                        print(f"Role: {result['role']}")
                        print(f"Location: {result['location']}")
                        result['connection_level'] = 1 if network_type == 'F' else 2
                        print(f"Connection Level: {result['connection_level']}")
                        people.append(result)

            except Exception as e:
                print(f"Error processing {network_type} level connections: {e}")

        # Search for 1st level connections
        await search_and_process_connections('F')
        
        # Search for 2nd level connections
        await search_and_process_connections('S')

        print("\nClosing browser...")
        await browser.close()
        print("Done!")
        return {"people": people}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8001)

