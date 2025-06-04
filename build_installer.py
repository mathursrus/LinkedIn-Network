#!/usr/bin/env python3
"""
Build script to create a standalone executable for LinkedIn Network Builder
"""

import os
import subprocess
import sys
import shutil
import zipfile
import json

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
    
    # Copy GPT management file
    shutil.copy2('gpt_manager.py', installer_dir)
    
    # Copy GPT folder with instructions and OpenAPI schema
    gpt_source_dir = "GPT"
    gpt_dest_dir = os.path.join(installer_dir, "GPT")
    if os.path.exists(gpt_source_dir):
        shutil.copytree(gpt_source_dir, gpt_dest_dir)
        print("GPT folder copied with instructions and OpenAPI schema")
    else:
        print("GPT folder not found")
    
    # Create simple documentation
    readme_content = """🚀 LinkedIn Network Builder - Complete Setup

QUICK START:
1. Open Command Prompt or PowerShell in this folder
2. Run: linkedin-network-builder.exe --install-browsers
   (This installs browser components - only needed once)
3. Run: linkedin-network-builder.exe
   (This starts the main application)
4. The system will automatically:
   - Start the LinkedIn Network Builder API
   - Create a secure ngrok tunnel
   - Ask if you want ChatGPT integration
5. Choose 'y' for ChatGPT setup (browser will open)
6. Log in to ChatGPT when prompted
7. Your GPT will be ready to use immediately!

ALTERNATIVE ONE-COMMAND START:
Just run: linkedin-network-builder.exe
(It will auto-install browsers if needed, but may take longer)

WHAT'S INCLUDED:
- linkedin-network-builder.exe: Complete application with integrated setup
- gpt_manager.py: Automatic GPT configuration
- ngrok.exe: Secure tunnel software
- GPT/instructions.txt: GPT instructions template
- GPT/openapi.json: API schema template

FEATURES:
✅ All-in-One Executable: Everything integrated into one file
✅ Automatic Browser Installation: Handles Playwright setup
✅ Automatic GPT Setup: No manual configuration needed
✅ Smart URL Detection: Automatically configures ngrok tunnel
✅ Professional Templates: Uses complete instructions and API schema
✅ One-Click Launch: Just run the executable
✅ Error Recovery: Handles failures gracefully

USAGE:
1. Run linkedin-network-builder.exe --install-browsers (first time only)
2. Run linkedin-network-builder.exe
3. Wait for ngrok tunnel to start
4. Choose whether to set up ChatGPT integration
5. Use your LinkedIn Network Builder!

API ENDPOINTS:
- /browse_company_people - Get connections at a company
- /find_mutual_connections - Find mutual connections with someone
- /find_people_by_role - Find people with specific roles

TROUBLESHOOTING:
- Run as Administrator if you have permission issues
- Ensure you have internet access for ngrok and GPT setup
- Check console output for detailed status messages
- If browsers fail to install, try running --install-browsers separately

Enjoy your LinkedIn Network Builder!
"""
    
    with open(os.path.join(installer_dir, "README.txt"), "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    # Create a system check script
    system_check_script = """@echo off
echo 🔍 LinkedIn Network Builder - System Check
echo ==========================================
echo.

echo Checking Windows version...
ver
echo.

echo Checking if running as Administrator...
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running as Administrator
) else (
    echo ⚠️  Not running as Administrator - some features may require it
)
echo.

echo Checking internet connectivity...
ping -n 1 google.com >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Internet connection available
) else (
    echo ❌ No internet connection detected
)
echo.

echo Checking available disk space...
dir | find "bytes free"
echo.

echo System check complete!
echo.
echo To run LinkedIn Network Builder:
echo 1. Run: linkedin-network-builder.exe --install-browsers (first time)
echo 2. Run: linkedin-network-builder.exe
echo.
pause
"""
    
    with open(os.path.join(installer_dir, "system-check.bat"), "w", encoding="utf-8") as f:
        f.write(system_check_script)
    
    print("✅ Installer package created successfully!")
    print(f"📁 Package location: {os.path.abspath(installer_dir)}")
    print("📋 Contents:")
    for item in os.listdir(installer_dir):
        print(f"   - {item}")
    
    return installer_dir

def create_distribution_zip(installer_dir):
    """Create a clean distribution ZIP file"""
    print("\nCreating distribution ZIP...")
    
    # Clean up any personal data files from installer directory
    personal_files = [
        "browser_state.json",
        "chatgpt_cookies.json", 
        "*-Connections.json",
        "*-Mutual-Connections.json"
    ]
    
    for pattern in personal_files:
        import glob
        files_to_remove = glob.glob(os.path.join(installer_dir, pattern))
        for file_path in files_to_remove:
            try:
                os.remove(file_path)
                print(f"Removed personal file: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"Could not remove {file_path}: {e}")
    
    # Create ZIP file
    zip_filename = "LinkedIn-Network-Builder-v1.0.zip"
    
    # Remove existing ZIP if it exists
    if os.path.exists(zip_filename):
        os.remove(zip_filename)
    
    # Create the ZIP
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        # Add all files from installer directory
        for root, dirs, files in os.walk(installer_dir):
            for file in files:
                file_path = os.path.join(root, file)
                # Calculate the archive name (relative path from installer dir)
                arcname = os.path.relpath(file_path, installer_dir)
                zipf.write(file_path, arcname)
                print(f"Added to ZIP: {arcname}")
    
    # Get ZIP file size
    zip_size = os.path.getsize(zip_filename) / (1024 * 1024)  # Convert to MB
    
    print(f"\n✅ Distribution ZIP created successfully!")
    print(f"📦 File: {zip_filename}")
    print(f"📏 Size: {zip_size:.1f} MB")
    print(f"📍 Location: {os.path.abspath(zip_filename)}")
    
    # Create distribution instructions
    distribution_instructions = f"""
🚀 LINKEDIN NETWORK BUILDER - DISTRIBUTION PACKAGE

📦 File: {zip_filename}
📏 Size: {zip_size:.1f} MB

WHAT TO SEND TO USERS:
✅ Send them this ZIP file: {zip_filename}
✅ Tell them to extract it to any folder
✅ Tell them to run linkedin-network-builder.exe

USER INSTRUCTIONS:
1. Extract {zip_filename} to any folder
2. Open Command Prompt/PowerShell in that folder
3. Run: linkedin-network-builder.exe
4. Follow the prompts for ChatGPT integration
5. Start networking!

WHAT'S INCLUDED:
- Complete standalone application (no Python needed)
- Automatic browser installation
- Automatic ChatGPT GPT setup
- Secure ngrok tunneling
- Professional GPT templates
- Complete documentation

SYSTEM REQUIREMENTS:
- Windows 10/11 (64-bit)
- Internet connection
- 500MB free disk space
- Administrator privileges (for first-time browser installation)

TROUBLESHOOTING FOR FRESH MACHINES:

🔧 If the executable won't run:
1. Install Microsoft Visual C++ Redistributable:
   - Download from: https://aka.ms/vs/17/release/vc_redist.x64.exe
   - This is required for PyInstaller executables

🛡️ If Windows Defender blocks it:
1. Right-click the executable → Properties → Unblock
2. Or add the folder to Windows Defender exclusions
3. Or run as Administrator

🌐 If browser installation fails:
1. Run as Administrator: linkedin-network-builder.exe --install-browsers
2. Ensure internet connection is stable
3. Check Windows Firewall isn't blocking downloads

🔒 If ngrok fails to start:
1. Check if corporate firewall blocks ngrok
2. Try running as Administrator
3. Some corporate networks block tunnel services

💡 Alternative for corporate environments:
- The application can run locally without ngrok
- Access API directly at http://localhost:8001/docs
- Manual GPT setup may be required

SUPPORT:
- Check console output for detailed error messages
- Most issues are resolved by running as Administrator
- Ensure antivirus isn't blocking the application

The application is completely self-contained and requires no additional software installation beyond the optional Visual C++ Redistributable!
"""
    
    with open("DISTRIBUTION_INSTRUCTIONS.txt", "w", encoding="utf-8") as f:
        f.write(distribution_instructions)
    
    print(f"\n📋 Distribution instructions saved to: DISTRIBUTION_INSTRUCTIONS.txt")
    
    return zip_filename

def main():
    """Main build process"""
    print("Building LinkedIn Network Builder installer with automatic GPT setup...")
    
    try:
        install_dependencies()
        download_ngrok()
        build_executable()
        installer_dir = create_installer_package()
        create_distribution_zip(installer_dir)
        
        print("\n" + "="*60)
        print("BUILD COMPLETE!")
        print("="*60)
        print("Installer package is ready in the 'installer' directory")
        print("")
        print("CUSTOMER INSTRUCTIONS:")
        print("1. Extract the installer folder")
        print("2. Run linkedin-network-builder.exe")
        print("3. Follow the prompts to login to ChatGPT")
        print("4. Your GPT will be automatically configured!")
        print("")
        print("The installer includes:")
        print("- LinkedIn Network Builder executable")
        print("- ngrok tunnel software")
        print("- Automatic GPT setup and configuration")
        print("- Complete documentation")
        
    except subprocess.CalledProcessError as e:
        print(f"Build failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 