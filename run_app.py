import uvicorn
import webbrowser
import threading
import time
import os
import sys
from linkedin_network_builder import app

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")

    return os.path.join(base_path, relative_path)

def run_server():
    """Runs the Uvicorn server."""
    uvicorn.run(app, host="127.0.0.1", port=8001)

def main():
    """Starts the server in a background thread and opens the client."""
    print("Starting LinkedIn Network Assistant...")

    # Start the Uvicorn server in a daemon thread.
    # Daemon threads exit when the main program exits.
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    print("Server has started in the background.")

    # Give the server a moment to initialize before opening the browser.
    time.sleep(2)

    # Get the absolute path to client.html and open it.
    client_path = resource_path('client.html')
    print(f"Opening client interface at: {client_path}")
    webbrowser.open(f"file://{client_path}")

    print("\nApplication is running. Close this window or press Ctrl+C to exit.")
    
    # Keep the main thread alive to allow the server to run.
    # The server thread will exit when this main thread exits.
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down.")

if __name__ == "__main__":
    main() 