# LinkedIn Network Builder - Clean Setup

## 🎯 What You Have Now

**3 Simple Components:**

1. **`main_clean.py`** - API server that hosts endpoints (port 8001)
2. **`ui.html`** - Web interface with submit buttons for each option
3. **`chatgpt_feeder.py`** - Service that sends JSON to ChatGPT (port 8002)

## 🚀 Quick Start

### Step 1: Start the API Server
```bash
python main_clean.py
```
- Hosts the API endpoints
- Serves the UI at http://localhost:8001
- Handles LinkedIn searches and caching

### Step 2: Use the Web Interface
- Open http://localhost:8001 in your browser
- You'll see 4 options with submit buttons:
  - 🏢 Find Connections at Company
  - 🏭 Find Connections by Industry (placeholder)
  - 👔 Find Connections by Role (placeholder)  
  - 🗑️ Clear Cache

### Step 3: (Optional) Start ChatGPT Feeder
```bash
python chatgpt_feeder.py
```
- Only needed if you want to auto-send results to ChatGPT
- Requires Chrome with debug mode: `chrome.exe --remote-debugging-port=9222`

## 📋 How It Works

1. **Enter company name** (e.g., "Anthropic") in the web UI
2. **Click Submit** - calls `http://localhost:8001/company/Anthropic`
3. **API searches LinkedIn** using Playwright automation
4. **Results displayed** as JSON in the web interface
5. **Click "Feed to ChatGPT"** to send results to ChatGPT (optional)

## 🔗 API Endpoints

- `GET /` - Web UI interface
- `GET /company/{company_name}` - Get connections at company
- `GET /clear_cache/{company_name}` - Clear cached results

## 📁 Files Explained

- **`main_clean.py`** - Clean API server (no ChatGPT integration)
- **`ui.html`** - Simple web interface with forms and submit buttons
- **`chatgpt_feeder.py`** - Separate service for ChatGPT integration
- **`cache/`** - Stores search results automatically

## ✅ What's Working

- ✅ Clean API server without ChatGPT complexity
- ✅ Web UI with submit buttons for each option
- ✅ Company search functionality
- ✅ Caching system
- ✅ Separate ChatGPT feeder service
- ✅ No encoding issues

## 🎯 Usage Examples

**Search for Anthropic connections:**
1. Go to http://localhost:8001
2. Enter "Anthropic" in company field
3. Click Submit
4. View JSON results
5. Optionally click "Feed to ChatGPT"

**Clear cache:**
1. Enter "Anthropic" in clear cache field
2. Click Submit
3. Cache cleared

**API direct calls:**
- http://localhost:8001/company/Anthropic
- http://localhost:8001/clear_cache/Anthropic 