@echo off
echo Installing LinkedIn Network Builder...

REM Create installation directory
set INSTALL_DIR=%USERPROFILE%\LinkedIn-Network-Builder
if not exist "%INSTALL_DIR%" mkdir "%INSTALL_DIR%"

REM Copy files
echo Copying files...
copy linkedin-network-builder.exe "%INSTALL_DIR%\"
copy ngrok.exe "%INSTALL_DIR%\"
copy start-linkedin-network.bat "%INSTALL_DIR%\"

echo Files copied to: %INSTALL_DIR%

REM Install Playwright browsers
echo.
echo Installing browser dependencies...
echo This may take several minutes and requires internet connection.
echo.
"%INSTALL_DIR%\linkedin-network-builder.exe" --install-browsers

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
