# LinkedIn Network Builder

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
