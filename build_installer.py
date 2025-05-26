#!/usr/bin/env python3
"""
Build script to create a standalone executable for LinkedIn Network Builder
"""

import os
import subprocess
import sys
import shutil
import zipfile

def install_dependencies():
    """Install required dependencies"""
    print("Installing dependencies...")
    
    # First install requests (needed for this script)
    try:
        import requests
    except ImportError:
        print("Installing requests...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    
    # Install PyInstaller
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
    
    # Install project dependencies
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])

def download_ngrok():
    """Download ngrok for Windows"""
    print("Downloading ngrok...")
    
    # Import requests here after ensuring it's installed
    import requests
    
    ngrok_url = "https://bin.equinox.io/c/bNyj1mQVY4c/ngrok-v3-stable-windows-amd64.zip"
    ngrok_zip = "ngrok.zip"
    
    # Download ngrok
    response = requests.get(ngrok_url)
    with open(ngrok_zip, 'wb') as f:
        f.write(response.content)
    
    # Extract ngrok
    with zipfile.ZipFile(ngrok_zip, 'r') as zip_ref:
        zip_ref.extract('ngrok.exe', '.')
    
    # Clean up
    os.remove(ngrok_zip)
    print("ngrok downloaded successfully")

def build_executable():
    """Build the executable using PyInstaller"""
    print("Building executable...")
    
    # PyInstaller command
    cmd = [
        "pyinstaller",
        "--onefile",
        "--name", "linkedin-network-builder",
        "--add-data", "GPT;GPT",
        "--hidden-import", "uvicorn.lifespan.on",
        "--hidden-import", "uvicorn.lifespan.off",
        "--hidden-import", "uvicorn.protocols.websockets.auto",
        "--hidden-import", "uvicorn.protocols.http.auto",
        "--hidden-import", "uvicorn.protocols.websockets.websockets_impl",
        "--hidden-import", "uvicorn.protocols.http.httptools_impl",
        "--hidden-import", "uvicorn.protocols.http.h11_impl",
        "--hidden-import", "uvicorn.logging",
        "main.py"
    ]
    
    subprocess.check_call(cmd)

def create_installer_package():
    """Create a simple installer package"""
    print("Creating installer package...")
    
    # Create installer directory
    installer_dir = "installer"
    if os.path.exists(installer_dir):
        shutil.rmtree(installer_dir)
    os.makedirs(installer_dir)
    
    # Copy executable and ngrok
    shutil.copy("dist/linkedin-network-builder.exe", installer_dir)
    shutil.copy("ngrok.exe", installer_dir)
    
    # Create launcher script that starts both the API and ngrok
    launcher_script = """@echo off
title LinkedIn Network Builder
echo Starting LinkedIn Network Builder...
echo.

REM Start the API server in the background
echo Starting API server...
start /B linkedin-network-builder.exe

REM Wait a moment for the server to start
timeout /t 3 /nobreak >nul

REM Start ngrok tunnel
echo Starting ngrok tunnel...
echo.
echo IMPORTANT: Copy the HTTPS URL that ngrok shows below
echo You'll need this URL for your GPT configuration
echo.
ngrok.exe http 8001

REM When ngrok closes, also close the API server
echo Shutting down...
taskkill /f /im linkedin-network-builder.exe >nul 2>&1
"""
    
    with open(os.path.join(installer_dir, "start-linkedin-network.bat"), "w") as f:
        f.write(launcher_script)
    
    # Create install script
    install_script = """@echo off
echo Installing LinkedIn Network Builder...

REM Create installation directory
set INSTALL_DIR=%USERPROFILE%\\LinkedIn-Network-Builder
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy files
echo Copying files...
copy linkedin-network-builder.exe "%INSTALL_DIR%\\"
copy ngrok.exe "%INSTALL_DIR%\\"
copy start-linkedin-network.bat "%INSTALL_DIR%\\"

echo Files copied to: %INSTALL_DIR%

REM Install Playwright browsers
echo.
echo Installing browser dependencies...
echo This may take several minutes and requires internet connection.
echo.
"%INSTALL_DIR%\\linkedin-network-builder.exe" --install-browsers

if %ERRORLEVEL% EQU 0 (
    echo Browser installation completed successfully
) else (
    echo Warning: Browser installation may have failed
    echo You can run this manually later: linkedin-network-builder.exe --install-browsers
)

echo.
echo ============================================
echo Installation complete!
echo ============================================
echo.
echo HOW TO RUN:
echo 1. Navigate to: %INSTALL_DIR%
echo 2. Double-click: start-linkedin-network.bat
echo 3. Copy the HTTPS URL that ngrok displays
echo 4. Update your GPT configuration with this URL
echo.
echo The start script will launch both the API server and ngrok tunnel
echo.
pause
"""
    
    with open(os.path.join(installer_dir, "install.bat"), "w") as f:
        f.write(install_script)
    
    # Create comprehensive README
    readme = """# LinkedIn Network Builder

## Quick Start
1. Run install.bat as Administrator
2. Double-click the "LinkedIn Network Builder" desktop shortcut
3. Copy the HTTPS URL from ngrok (e.g., https://abc123.ngrok.io)
4. Update your GPT configuration with this URL

## What Gets Installed
- LinkedIn Network Builder API server
- ngrok tunnel for external access
- Desktop shortcut that starts everything

## Usage

### Starting the Application
- Double-click "LinkedIn Network Builder" desktop shortcut
- This starts both the API server and ngrok tunnel
- Copy the HTTPS URL that ngrok displays

### API Endpoints
- GET /browse_company_people?company=CompanyName
- GET /find_mutual_connections?person=PersonName&company=CompanyName

### GPT Configuration
1. In your GPT settings, update the server URL to the ngrok HTTPS URL
2. Example: https://abc123.ngrok.io (replace with your actual URL)
3. The ngrok URL changes each time you restart, so update it accordingly

## Important Notes
- The ngrok URL changes every time you restart the application
- Always use the HTTPS URL (not HTTP) for GPT integration
- Keep the command window open while using the application
- Close the command window to stop both the API and tunnel

## Troubleshooting
- If port 8001 is in use, close other applications using that port
- If ngrok fails, check your internet connection
- For GPT integration issues, verify the ngrok URL is correct and accessible

## Support
For technical support, please contact [your contact information]
"""
    
    with open(os.path.join(installer_dir, "README.txt"), "w") as f:
        f.write(readme)
    
    # Create ngrok configuration template
    ngrok_config = """# ngrok Configuration (Optional)
# You can create an ngrok account for additional features:
# 1. Sign up at https://ngrok.com
# 2. Get your auth token
# 3. Run: ngrok config add-authtoken YOUR_TOKEN
# 4. This enables custom domains and longer session times

# Basic usage (no account needed):
# ngrok http 8001
"""
    
    with open(os.path.join(installer_dir, "ngrok-setup.txt"), "w") as f:
        f.write(ngrok_config)
    
    print(f"Installer package created in '{installer_dir}' directory")

def main():
    """Main build process"""
    print("Building LinkedIn Network Builder installer with ngrok...")
    
    try:
        install_dependencies()
        download_ngrok()
        build_executable()
        create_installer_package()
        
        print("\n" + "="*60)
        print("BUILD COMPLETE!")
        print("="*60)
        print("Installer package is ready in the 'installer' directory")
        print("")
        print("CUSTOMER INSTRUCTIONS:")
        print("1. Extract the installer folder")
        print("2. Run install.bat as Administrator")
        print("3. Navigate to the installation folder and run start-linkedin-network.bat")
        print("4. Copy the ngrok HTTPS URL for GPT configuration")
        print("")
        print("The installer includes:")
        print("- LinkedIn Network Builder executable")
        print("- ngrok tunnel software")
        print("- Automatic startup script")
        print("- Complete documentation")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 