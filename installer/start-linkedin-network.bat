@echo off
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
