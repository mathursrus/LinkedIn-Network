@echo off
echo "Setting up the Python virtual environment..."

:: Check if python is installed
python --version 2>nul
if %errorlevel% neq 0 (
    echo "Python is not installed. Please install Python 3.8+ and add it to your PATH."
    exit /b 1
)

:: Create a virtual environment
echo "Creating virtual environment..."
python -m venv venv

:: Activate the virtual environment and install dependencies
echo "Activating virtual environment and installing dependencies..."
call venv\Scripts\activate.bat

echo "Installing Playwright version 1.41.2..."
pip install playwright==1.41.2

echo "Installing Chromium browser for Playwright..."
playwright install chromium

echo "Setup complete. You can now run the application."
deactivate 