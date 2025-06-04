import requests
import time
import json
import subprocess
import asyncio
from typing import Optional
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_ngrok_url(max_retries: int = 30, retry_delay: int = 1) -> Optional[str]:
    """
    Get the ngrok public URL by querying the ngrok API
    """
    for attempt in range(max_retries):
        try:
            # Query ngrok's local API
            response = requests.get("http://localhost:4040/api/tunnels", timeout=5)
            
            if response.status_code == 200:
                data = response.json()
                tunnels = data.get("tunnels", [])
                
                for tunnel in tunnels:
                    if tunnel.get("proto") == "https":
                        public_url = tunnel.get("public_url")
                        if public_url:
                            logger.info(f"Found ngrok URL: {public_url}")
                            return public_url
                            
            logger.info(f"Attempt {attempt + 1}/{max_retries}: Waiting for ngrok to start...")
            time.sleep(retry_delay)
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                logger.info(f"Attempt {attempt + 1}/{max_retries}: ngrok not ready yet...")
                time.sleep(retry_delay)
            else:
                logger.error(f"Failed to get ngrok URL after {max_retries} attempts: {e}")
                
    return None

def start_ngrok_and_get_url(port: int = 8001) -> Optional[str]:
    """
    Start ngrok and return the public URL
    """
    try:
        logger.info(f"Starting ngrok on port {port}...")
        
        # Start ngrok process
        ngrok_process = subprocess.Popen(
            ["ngrok.exe", "http", str(port)],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_CONSOLE
        )
        
        # Wait a moment for ngrok to start
        time.sleep(3)
        
        # Get the public URL
        public_url = get_ngrok_url()
        
        if public_url:
            logger.info(f"ngrok started successfully: {public_url}")
            return public_url
        else:
            logger.error("Failed to get ngrok URL")
            return None
            
    except Exception as e:
        logger.error(f"Failed to start ngrok: {e}")
        return None

async def setup_gpt_if_needed(ngrok_url: str) -> bool:
    """
    Setup or update GPT with the ngrok URL
    """
    try:
        from gpt_manager import setup_gpt_with_ngrok
        
        logger.info("Setting up GPT with ngrok URL...")
        result = await setup_gpt_with_ngrok(ngrok_url)
        
        if result:
            logger.info(f"GPT setup completed: {result}")
            return True
        else:
            logger.error("GPT setup failed")
            return False
            
    except Exception as e:
        logger.error(f"Error setting up GPT: {e}")
        return False

def save_ngrok_url(url: str, filename: str = "ngrok_url.txt"):
    """Save the ngrok URL to a file for reference"""
    try:
        with open(filename, "w") as f:
            f.write(url)
        logger.info(f"Saved ngrok URL to {filename}")
    except Exception as e:
        logger.error(f"Failed to save ngrok URL: {e}")

async def main():
    """Main function to start ngrok and setup GPT"""
    # Start ngrok and get URL
    ngrok_url = start_ngrok_and_get_url()
    
    if not ngrok_url:
        logger.error("Failed to start ngrok or get URL")
        return False
        
    # Save URL for reference
    save_ngrok_url(ngrok_url)
    
    # Setup GPT
    gpt_success = await setup_gpt_if_needed(ngrok_url)
    
    if gpt_success:
        logger.info("✅ Complete! ngrok and GPT are ready")
        logger.info(f"📡 ngrok URL: {ngrok_url}")
        logger.info("🤖 Your GPT has been created/updated with the new URL")
    else:
        logger.warning("⚠️  ngrok is running but GPT setup failed")
        logger.info(f"📡 ngrok URL: {ngrok_url}")
        logger.info("You can manually update your GPT with this URL")
        
    return True

if __name__ == "__main__":
    asyncio.run(main()) 