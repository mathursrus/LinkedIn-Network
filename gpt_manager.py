import asyncio
import json
import re
import time
import os
import platform
import warnings
from playwright.async_api import async_playwright, Page, Browser
from typing import Optional, Dict, Any
import logging

# Suppress harmless Windows asyncio cleanup warnings
if platform.system() == "Windows":
    warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed transport.*")
    warnings.filterwarnings("ignore", category=RuntimeWarning, message=".*Event loop is closed.*")

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class BrowserCrashedException(Exception):
    """Custom exception for when browser crashes or becomes unresponsive"""
    pass

class GPTManager:
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.page: Optional[Page] = None
        self.context = None
        self.gpt_name = "Sid's LinkedIn Network Builder"
        self.gpt_description = "Find LinkedIn connections and mutual connections at target companies"
        self.cookies_file = "chatgpt_cookies.json"
        
    def load_instructions(self) -> str:
        """Load instructions from GPT/instructions.txt"""
        try:
            instructions_path = os.path.join("GPT", "instructions.txt")
            if not os.path.exists(instructions_path):
                # Fallback to current directory
                instructions_path = "instructions.txt"
                
            with open(instructions_path, "r", encoding="utf-8") as f:
                return f.read().strip()
        except Exception as e:
            logger.error(f"Failed to load instructions: {e}")
            raise e
    
    def load_openapi_schema(self, ngrok_url: str) -> Dict[str, Any]:
        """Load and update OpenAPI schema from GPT/openapi.json"""
        try:
            openapi_path = os.path.join("GPT", "openapi.json")
            if not os.path.exists(openapi_path):
                # Fallback to current directory
                openapi_path = "openapi.json"
                
            with open(openapi_path, "r", encoding="utf-8") as f:
                schema = json.load(f)
                
            # Update the server URL with the current ngrok URL
            schema["servers"] = [{"url": ngrok_url, "description": "Current ngrok tunnel"}]
            
            return schema
        except Exception as e:
            logger.error(f"Failed to load OpenAPI schema: {e}")
            raise e
    
    async def save_cookies(self):
        """Save browser cookies to file"""
        try:
            if self.context:
                cookies = await self.context.cookies()
                with open(self.cookies_file, 'w') as f:
                    json.dump(cookies, f)
                logger.info("Cookies saved successfully")
        except Exception as e:
            logger.error(f"Failed to save cookies: {e}")
    
    async def load_cookies(self):
        """Load browser cookies from file"""
        try:
            if os.path.exists(self.cookies_file):
                with open(self.cookies_file, 'r') as f:
                    cookies = json.load(f)
                await self.context.add_cookies(cookies)
                logger.info("Cookies loaded successfully")
                return True
        except Exception as e:
            logger.error(f"Failed to load cookies: {e}")
        return False
        
    async def initialize_browser(self):
        """Initialize Playwright browser with human-like settings"""
        # Set persistent browser location for PyInstaller compatibility
        persistent_browser_path = os.path.join(os.path.expanduser("~"), ".playwright-browsers")
        os.environ["PLAYWRIGHT_BROWSERS_PATH"] = persistent_browser_path
        
        playwright = await async_playwright().start()
        
        # Use more human-like browser settings to avoid CAPTCHAs
        self.browser = await playwright.chromium.launch(
            headless=False,  # Keep visible for user to see login process
            args=[
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-blink-features=AutomationControlled',  # Hide automation
                '--disable-web-security',
                '--disable-features=VizDisplayCompositor'
            ]
        )
        
        # Create context with realistic settings
        self.context = await self.browser.new_context(
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            locale='en-US',
            timezone_id='America/New_York'
        )
        
        self.page = await self.context.new_page()
        
        # Add script to remove webdriver property
        await self.page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined,
            });
        """)
        
        # Load existing cookies if available
        await self.load_cookies()
        
    async def close_browser(self):
        """Close the browser and clean up resources properly"""
        try:
            # Save cookies before closing
            await self.save_cookies()
        except Exception as e:
            logger.debug(f"Error saving cookies during cleanup: {e}")
            
        try:
            # Close page first and wait for it to fully close
            if self.page and not self.page.is_closed():
                await self.page.close()
                await asyncio.sleep(0.5)  # Give time for page cleanup
                self.page = None
                
            # Close context and wait for cleanup
            if self.context:
                await self.context.close()
                await asyncio.sleep(0.5)  # Give time for context cleanup
                self.context = None
                
            # Close browser and wait for all processes to terminate
            if self.browser:
                await self.browser.close()
                await asyncio.sleep(1)  # Give time for browser processes to terminate
                self.browser = None
                
            # Additional wait for Windows to clean up pipes/transports
            await asyncio.sleep(1)
            
        except Exception as e:
            logger.debug(f"Error during browser cleanup: {e}")
            # Force close if normal cleanup fails
            try:
                if self.browser:
                    await self.browser.close()
                    await asyncio.sleep(1)
                    self.browser = None
            except Exception as force_error:
                logger.debug(f"Error during force close: {force_error}")
                
        # Reset all references
        self.page = None
        self.context = None
        self.browser = None
        
    async def is_browser_alive(self) -> bool:
        """Check if browser and page are still alive"""
        try:
            if not self.browser or not self.page or not self.context:
                return False
            if self.page.is_closed():
                return False
            # Try a simple operation to test if browser is responsive
            await self.page.evaluate("() => true")
            return True
        except Exception as e:
            logger.debug(f"Browser health check failed: {e}")
            return False
            
    async def ensure_browser_alive(self):
        """Ensure browser is alive, raise exception if not"""
        if not await self.is_browser_alive():
            logger.error("Browser has crashed or become unresponsive")
            raise BrowserCrashedException("Browser is not responsive")
            
    async def login_to_openai(self) -> bool:
        """Navigate to OpenAI and wait for user to login"""
        try:
            logger.info("Navigating to OpenAI ChatGPT...")
            await self.page.goto("https://chatgpt.com/")
            
            # Add human-like delay
            await asyncio.sleep(2)
            
            # Wait for page to fully load
            await self.page.wait_for_load_state('networkidle')
            
            # Check if browser is still alive after navigation
            await self.ensure_browser_alive()

            # Wait for either login button or already logged in state
            try:
                # Check if login button is present (user not logged in)
                login_button = await self.page.wait_for_selector('button[data-testid="login-button"]', timeout=2000)
                logger.info("Login button found, clicking to start login process...")   
            except:
                # Login button not found, user is already logged in
                logger.info("Already logged in to OpenAI")
                return True
            
            # Wait for login to complete and page to reload with profile
            try:        
                await login_button.click()
                
                logger.info("Please complete the login process in the browser window...")
                logger.info("Waiting for login to complete...")
                
                # Wait for the page to display
                await asyncio.sleep(5)
                await self.page.wait_for_selector('[data-testid="profile-button"]', timeout=120000)
                
                # Check if browser is still alive after login
                await self.ensure_browser_alive()
                
                logger.info("Login successful!")
                return True
            except Exception as e:
                # Login button not found, user is already logged in
                logger.info("Did not login within time limit...exiting")
                raise Exception(f"Login failed: {e}")       
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            logger.error(f"Login failed: {e}")
            return False
            
    async def navigate_to_gpt_builder(self) -> bool:
        """Navigate to the GPT builder page"""
        try:
            logger.info("Navigating to GPT builder...")
            await self.page.goto("https://chatgpt.com/gpts/editor")
            
            # Wait for the page to load
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Check if browser is still alive after navigation
            await self.ensure_browser_alive()
            
            return True
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            logger.error(f"Failed to navigate to GPT builder: {e}")
            return False
            
    async def check_existing_gpt(self) -> Optional[str]:
        """Check if a GPT with our name already exists"""
        try:
            # Check if browser is alive before proceeding
            await self.ensure_browser_alive()
                    
            logger.info(f"Checking for existing GPT: {self.gpt_name}")
            
            # Go to "My GPTs" page first
            await self.page.goto("https://chatgpt.com/gpts/mine")
            await self.page.wait_for_load_state('networkidle')
            await asyncio.sleep(2)
            
            # Check if page crashed after navigation
            await self.ensure_browser_alive()
            
            
            # Look for GPT containers - they typically have the GPT name
            gpt_containers = await self.page.query_selector_all('div[tabindex="0"]')
            
            for container in gpt_containers:
                try:
                    # Get text content of the container
                    container_text = await container.text_content()
                    logger.info(f"Container text: {container_text}")
                    
                    if container_text and self.gpt_name.lower() in container_text.lower():
                        logger.info(f"Found GPT container with matching name")
                        
                        # Look for the edit button within this container instead of href
                        edit_button = await container.query_selector('button[class*="text-token-text-primary"]')
                        
                        if edit_button:
                            logger.info(f"Found edit button: {edit_button}")
                            await edit_button.click()
                            await asyncio.sleep(3)
                            logger.info("Clicked edit button for existing GPT")
                            # Return a special indicator that we clicked the edit button
                            return "EDIT_BUTTON_CLICKED"
                        else:
                            # Fallback: try to find any button in the container
                            fallback_button = await container.query_selector('button')
                            if fallback_button:
                                logger.info("Using fallback button")
                                await fallback_button.click()
                                await asyncio.sleep(3)
                                return "EDIT_BUTTON_CLICKED"
                            else:
                                logger.warning("No edit button found in container")
                except Exception as e:
                    logger.error(f"Error checking container: {e}")
                    continue
                    
            logger.info("No existing GPT found")
            return None
            
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            logger.error(f"Error checking for existing GPT: {e}")
            return None
            
    async def create_new_gpt(self, ngrok_url: str, existing_gpt_url: Optional[str] = None) -> bool:
        """Create a new GPT or update existing GPT with the given ngrok URL"""
        action = "updating" if existing_gpt_url else "creating"
                
        try:
            # Check if browser is alive before proceeding
            await self.ensure_browser_alive()
                    
            if existing_gpt_url and existing_gpt_url != "EDIT_BUTTON_CLICKED":
                logger.info(f"Updating existing GPT: {existing_gpt_url}")
                # Navigate to the existing GPT
                await self.page.goto(existing_gpt_url)
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                # Check browser health after navigation
                await self.ensure_browser_alive()
            elif existing_gpt_url == "EDIT_BUTTON_CLICKED":
                logger.info("Edit button was already clicked, continuing with current page")
                # Wait for the page to load after clicking edit button
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                # Check browser health after page load
                await self.ensure_browser_alive()
            else:
                logger.info(f"Creating new GPT: {self.gpt_name}")
                # Navigate to create new GPT
                await self.page.goto("https://chatgpt.com/gpts/editor")
                await self.page.wait_for_load_state('networkidle')
                await asyncio.sleep(2)
                # Check browser health after navigation
                await self.ensure_browser_alive()
            
            # Check if page crashed after navigation
            await self.ensure_browser_alive()
            
            # Navigate to Configure tab using the specific selector from screenshot
            try:
                configure_tab = await self.page.wait_for_selector('button[data-testid="gizmo-editor-configure-button"]', timeout=5000)
                await configure_tab.click()
                await asyncio.sleep(2)
                logger.info("Navigated to Configure tab")
                # Check browser health after clicking configure tab
                await self.ensure_browser_alive()
            except Exception as e:
                logger.warning(f"Failed to click Configure tab with specific selector: {e}")
                
            # Fill in GPT name
            try:
                name_input = await self.page.wait_for_selector('input[placeholder*="Name"], input[placeholder*="name"], textarea[placeholder*="Name"]', timeout=5000)
                await name_input.fill(self.gpt_name)
                logger.info("GPT name filled successfully")
                # Check browser health after filling name
                await self.ensure_browser_alive()
            except Exception as e:
                logger.error(f"Failed to fill GPT name: {e}")
                return False
            
            # Fill in description using the specific selector from screenshot
            try:
                desc_input = await self.page.wait_for_selector('input[data-testid="gizmo-description-input"]', timeout=5000)
                await desc_input.fill(self.gpt_description)
                logger.info("GPT description filled successfully")
                # Check browser health after filling description
                await self.ensure_browser_alive()
            except Exception as e:
                logger.warning(f"Failed to fill description with specific selector: {e}")
                    
            # Load and configure instructions
            try:
                instructions = self.load_instructions()
                
                inst_input = await self.page.wait_for_selector('textarea[data-testid="gizmo-instructions-input"]', timeout=5000)
                await inst_input.fill(instructions)
                logger.info("GPT instructions filled successfully")
                # Check browser health after filling instructions
                await self.ensure_browser_alive()

            except Exception as e:
                logger.error(f"Failed to configure instructions: {e}")
                return False
            
            # Add conversation starters
            await self.add_conversation_starters()
            # Check browser health after adding conversation starters
            await self.ensure_browser_alive()
                    
            # Configure Actions (API endpoints)
            await self.configure_actions(ngrok_url)
            # Check browser health after configuring actions
            await self.ensure_browser_alive()
            
            # Save the GPT 
            await self.save_gpt()
            # Check browser health after saving
            await self.ensure_browser_alive()
            
            logger.info(f"GPT {action} successfully!")
            
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            action = "update" if existing_gpt_url else "create"
            logger.error(f"Failed to {action} GPT: {e}")
            return False
            
    async def add_conversation_starters(self):
        """Add conversation starters to the GPT"""
        try:
            logger.info("Adding conversation starters...")
            
            conversation_starters = [
                "What companies should I target in the {Industry} industry?",
                "Who are my connections at {Company Name}?",
                "Who are my 2nd degree connections at {Company Name}?",
                "Help me build a connection with person {Person Name} who works at {Company Name}",
                "Who should I connect with at {Company Name} who has a role of {Role}?"
            ]
            
            # Look for the conversation starters section with parent div mb-6
            try:
                # Find the div with class mb-6 that contains "Conversation starters"
                conversation_section = await self.page.wait_for_selector('div.mb-6:has-text("Conversation starters")', timeout=5000)
                if conversation_section:
                    logger.info("Found conversation starters section")
                    
                    # Add conversation starters to empty fields
                    added_count = 0
                    for i, starter in enumerate(conversation_starters):
                        # Find all text input fields within this section
                        text_inputs = await conversation_section.query_selector_all('input[type="text"]')
                        logger.info(f"Found {len(text_inputs)} text input fields in conversation starters section")
                        
                        if i < len(text_inputs):
                            try:
                                input_field = text_inputs[i]
                                current_value = await input_field.input_value()
                                
                                await input_field.fill(starter)
                                logger.info(f"Added conversation starter {i+1}: {starter}")
                                added_count += 1    
                            except Exception as e:
                                logger.debug(f"Failed to add conversation starter {i+1}: {e}")
                                continue
                    
                    logger.info(f"Successfully added {added_count} conversation starters")
                else:
                    logger.warning("Could not find conversation starters section")
                    
            except Exception as e:
                logger.warning(f"Failed to find conversation starters section: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to add conversation starters: {e}")
    
    
    async def configure_actions(self, ngrok_url: str):
        """Configure the Actions (API endpoints) for the GPT"""
        try:
            logger.info("Configuring GPT Actions...")
            
            # Look for the Actions section with parent div mb-6
            try:
                # Find the div with class mb-6 that contains "Actions"
                actions_section = await self.page.wait_for_selector('div.mb-6:has-text("Actions")', timeout=5000)
                if actions_section:
                    logger.info(f"Found Actions section: {actions_section}")
                    
                    # Look for existing populated actions within this section
                    # Look for buttons other than "Create new action" - those are existing actions
                    all_buttons = await actions_section.query_selector_all('button')
                    existing_actions = []
                    
                    logger.info(f"Found {len(all_buttons)} total buttons in actions section")
                    
                    for i, button in enumerate(all_buttons):
                        try:
                            button_text = await button.text_content()
                            button_classes = await button.get_attribute('class')
                            logger.info(f"Button {i+1}: text='{button_text}', classes='{button_classes}'")
                            
                            # Check if this is NOT the "Create new action" button
                            if not button_text or "create new action" not in button_text.lower():
                                existing_actions.append(button)
                                logger.info(f"Added button {i+1} as existing action")
                            else:
                                logger.info(f"Skipped button {i+1} - it's the create button")
                                
                        except Exception as e:
                            logger.debug(f"Error checking button {i+1}: {e}")
                            # If we can't get text, assume it's an action button (like icon buttons)
                            existing_actions.append(button)
                            logger.info(f"Added button {i+1} as existing action (no text)")
                    
                    logger.info(f"Total existing action buttons found: {len(existing_actions)}")
                    
                    if existing_actions and len(existing_actions) > 0:
                        logger.info(f"Found {len(existing_actions)} existing action(s)")
                        
                        await existing_actions[0].click()
                        await asyncio.sleep(2)
                        logger.info("Clicked on existing action div")
                    else:
                        logger.info("No existing actions found, creating new action")
                        
                        # Look for "Create new action" button within the actions section
                        try:
                            create_action_btn = await actions_section.wait_for_selector('button:has-text("Create new action")', timeout=5000)
                            await create_action_btn.click()
                            await asyncio.sleep(2)
                            logger.info("Clicked Create new action button")
                        except Exception as e:
                            logger.warning(f"Could not find 'Create new action' button in actions section: {e}")
                else:
                    logger.warning("Could not find Actions section")
                    return
                    
            except Exception as e:
                logger.warning(f"Failed to find Actions section: {e}")
                return
                
            # Load and configure the OpenAPI schema
            openapi_schema = self.load_openapi_schema(ngrok_url)
            
            # Look for schema textarea specifically
            try:
                # First try to find the schema textarea by looking for the Schema label and associated textarea
                schema_textarea = await self.page.wait_for_selector('textarea[placeholder*="Enter your OpenAPI schema here"]', timeout=5000)
                if schema_textarea:
                    await schema_textarea.fill(json.dumps(openapi_schema, indent=2))
                    logger.info("OpenAPI schema configured successfully using specific selector")
                else:
                    raise Exception("Schema textarea not found with specific selector")
                    
            except Exception as e:
                logger.warning(f"Failed to find schema textarea with specific selector: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to configure actions: {e}")
            
    async def save_gpt(self):
        """Save the GPT configuration and handle the sharing dialog"""
        try:
            # Look for save/create/update button
            save_selectors = [
                'button:has(div:has-text("Create"))',
                'button:has(div:has-text("Update"))',
                'button:has(span:has-text("Create"))',
                'button:has(span:has-text("Update"))',
                'button div:has-text("Create")',
                'button div:has-text("Update")'
            ]
            
            for selector in save_selectors:
                try:
                    save_btn = await self.page.wait_for_selector(selector, timeout=10000)
                    await save_btn.click()
                    await asyncio.sleep(2)
                    logger.info(f"Clicked save button: {selector}")
                    break
                except Exception as e:
                    logger.debug(f"Could not find button with selector '{selector}': {e}")
                    continue
            else:
                logger.warning("Could not find save button with any selector")
                return None
            
            # Wait for either "Share GPT" dialog (new GPT) or "GPT Updated" dialog (existing GPT)
            try:
                # Check which dialog appears
                dialog_appeared = await self.page.wait_for_selector('div:has-text("Share GPT"), div:has-text("GPT Updated")', timeout=10000)
                dialog_text = await dialog_appeared.text_content()
                
                if "Share GPT" in dialog_text:
                    logger.info("Share GPT dialog appeared (new GPT)")
                    return await self.handle_share_gpt_dialog()
                elif "GPT Updated" in dialog_text:
                    logger.info("GPT Updated dialog appeared (existing GPT)")
                    return await self.handle_final_dialog()
                else:
                    logger.warning("Unknown dialog appeared")
                    return None
                    
            except Exception as e:
                logger.warning(f"No dialog appeared: {e}")
                return None
            
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            logger.error(f"Failed to save GPT: {e}")
            return None
    
    async def handle_share_gpt_dialog(self):
        """Handle the Share GPT dialog for new GPTs"""
        try:
            # Click "Only me" option
            try:
                only_me_button = await self.page.wait_for_selector('button:has-text("Only me")', timeout=5000)
                await only_me_button.click()
                await asyncio.sleep(1)
                logger.info("Selected 'Only me' privacy option")
            except Exception as e:
                logger.warning(f"Could not find 'Only me' button: {e}")
            
            # Click Save button in the dialog
            try:
                dialog_save_btn = await self.page.wait_for_selector('button:has-text("Save")', timeout=5000)
                await dialog_save_btn.click()
                await asyncio.sleep(3)
                logger.info("Clicked Save button in dialog")
            except Exception as e:
                logger.warning(f"Could not find Save button in dialog: {e}")
                return None
            
            # Wait for "Settings Saved" dialog and handle copy/view
            return await self.handle_final_dialog()
            
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            logger.error(f"Failed to handle Share GPT dialog: {e}")
            return None
    
    async def handle_final_dialog(self):
        """Handle the final dialog with copy link and view GPT buttons"""
        try:
            # Wait a bit for the dialog to fully load
            await asyncio.sleep(2)
            
            # Click "View GPT" button
            try:
                view_gpt_btn = await self.page.wait_for_selector(':has-text("View GPT")', timeout=5000)
                await view_gpt_btn.click()
                await asyncio.sleep(2)
                logger.info("Clicked View GPT element")
            except Exception as e:
                logger.warning(f"Could not find View GPT element: {e}")
            return None
                
        except BrowserCrashedException:
            # Re-raise browser crashes to trigger restart
            raise
        except Exception as e:
            logger.error(f"Failed to handle final dialog: {e}")
            return None
            

async def setup_gpt_with_ngrok(ngrok_url: str) -> Optional[str]:
    """Main function to setup or update GPT with ngrok URL"""
    max_retries = 2
    
    for attempt in range(max_retries + 1):
        gpt_manager = GPTManager()  # Create fresh instance each attempt
        
        try:
            logger.info(f"GPT setup attempt {attempt + 1}/{max_retries + 1}")
            
            # Initialize browser
            await gpt_manager.initialize_browser()
            
            # Login to OpenAI
            if not await gpt_manager.login_to_openai():
                logger.error("Failed to login to OpenAI")
                if attempt < max_retries:
                    logger.info("Retrying with fresh browser...")
                    continue
                return None
                
            # Check for existing GPT
            existing_gpt = await gpt_manager.check_existing_gpt()
            
            # Use create_new_gpt for both creating and updating
            await gpt_manager.create_new_gpt(ngrok_url, existing_gpt)
            
            logger.info("GPT setup completed successfully!")
            return "SUCCESS"
            
        except BrowserCrashedException as e:
            logger.error(f"Browser crashed during attempt {attempt + 1}: {e}")
            if attempt < max_retries:
                logger.info("Restarting entire process with fresh browser...")
                await asyncio.sleep(3)  # Wait before retry
            else:
                logger.error("Max retries reached due to browser crashes")
                
        except Exception as e:
            logger.error(f"Error in GPT setup attempt {attempt + 1}: {e}")
            if attempt < max_retries:
                logger.info("Retrying with fresh browser...")
                await asyncio.sleep(3)  # Wait before retry
            else:
                logger.error("Max retries reached, giving up")
                
        finally:
            # Always cleanup the current attempt's browser
            try:
                await gpt_manager.close_browser()
                await asyncio.sleep(2)  # Give extra time for Windows cleanup
            except Exception as cleanup_error:
                logger.debug(f"Cleanup error (non-critical): {cleanup_error}")
                
    # Final cleanup - ensure all pending tasks are completed
    await final_cleanup()
    return None

async def final_cleanup():
    """Final cleanup to ensure all asyncio resources are properly closed"""
    try:
        # Wait for any remaining tasks to complete
        pending_tasks = [task for task in asyncio.all_tasks() if not task.done()]
        if pending_tasks:
            logger.debug(f"Waiting for {len(pending_tasks)} pending tasks to complete...")
            await asyncio.sleep(2)
            
        # Give extra time for Windows to clean up pipes and transports
        await asyncio.sleep(1)
        
    except Exception as e:
        logger.debug(f"Final cleanup error (non-critical): {e}")

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        ngrok_url = sys.argv[1]
        result = asyncio.run(setup_gpt_with_ngrok(ngrok_url))
        if result:
            print(f"SUCCESS: {result}")
        else:
            print("FAILED: Could not setup GPT")
    else:
        print("Usage: python gpt_manager.py <ngrok_url>") 