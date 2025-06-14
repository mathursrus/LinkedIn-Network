#!/usr/bin/env python3
"""
LinkedIn Network Assistant Client
Opens the client interface without starting the server
"""

import webbrowser
from pathlib import Path

def open_client():
    """Open the client HTML file in the default browser"""
    client_path = Path("client.html").absolute()
    
    if not client_path.exists():
        print(f"Error: client.html not found at {client_path}")
        return False
    
    print(f"Opening client interface: {client_path}")
    webbrowser.open(f"file://{client_path}")
    return True

def main():
    """Main startup function"""
    print("LinkedIn Network Assistant - Opening Client")
    print("=" * 50)
    
    # Check if required files exist
    required_files = ["client.html", "client.js"]
    missing_files = [f for f in required_files if not Path(f).exists()]
    
    if missing_files:
        print(f"Error: Missing required files: {', '.join(missing_files)}")
        return 1
    
    # Open the client interface
    if not open_client():
        return 1
    
    print("\n" + "=" * 50)
    print("LinkedIn Network Assistant Client is open!")
    print("- Make sure the automation server is running at http://127.0.0.1:8002")
    print("- Configure your OpenAI API key in the client interface")
    print("- Make sure you're logged into LinkedIn in your browser")
    print("=" * 50)
    
    return 0

if __name__ == "__main__":
    exit(main()) 