# Personal Network Agent

A local API server that helps you explore your LinkedIn network and discover people at any company you specify. This project is designed for **personal use** and can be integrated with GPTs using the provided OpenAPI spec.

---

## 🚦 Requirements

- **Python 3.11.x** (not 3.12+; Playwright is not fully compatible with 3.12)
- **pip** (Python package manager)
- **Google Chrome** (or Chromium-based browser)
- **LinkedIn account** (you will log in interactively)
- **Windows, Mac, or Linux** (tested on Windows 10+)

---

## 🛠️ Setup Instructions

### 1. **Install Python 3.11**
- Download Python 3.11 from [python.org](https://www.python.org/downloads/release/python-3110/)
- During installation, check **"Add Python to PATH"**

### 2. **Clone the Repository**
```bash
git clone <your-repo-url>
cd <your-repo-directory>
```

### 3. **Create and Activate a Virtual Environment**
```bash
# Windows
python -m venv venv311
venv311\Scripts\activate

# Mac/Linux
python3.11 -m venv venv311
source venv311/bin/activate
```

### 4. **Install Dependencies**
```bash
pip install -r requirements.txt
```

### 5. **Install Playwright Browsers**
```bash
python -m playwright install
```

### 6. **Test Playwright Installation (Optional)**
```bash
python test_playwright.py
```
This should open and close a browser window without errors.

---

## 🚀 Running the Local API Server

### 1. **Start the Server**
```bash
python run.py
```
_or, if you want to use Uvicorn directly:_
```bash
uvicorn main:app --reload --port 8001
```

### 2. **Log In to LinkedIn**
- On first use, a browser window will open.
- Log in to LinkedIn **manually** (handle MFA/CAPTCHA as needed).
- The session will be saved and reused for future requests.

---

## 🧪 Testing the API
You can test the API with:
```bash
curl "http://127.0.0.1:8001/browse_company_people?company=Microsoft"
```
- Replace `Microsoft` with any company name.
- The response will be a JSON list of people, their roles, locations, and connection levels.

---

## 🤖 GPT Integration

### 1. **OpenAPI Spec**
- Download ngrok (or cloudflare)
- Run ngrok http 8001
- Take note of the https endpoint that ngrok returns

### 2. **Instructions for GPT Users**
- Use the `GPT/instructions.txt` and `GPT/openapi.json` to create a custom GPT that calls your local API.
- Update the servers segment of the spec with the endpoint that ngrok returned
- Save the GPT and use it for your networking needs.

---

## 📝 Notes & Troubleshooting
- **Python Version:**  
  You **must** use Python 3.11.x. Playwright is not fully compatible with 3.12+.
- **Virtual Environment:**  
  Always activate your venv before running the server.
- **Playwright Browsers:**  
  If you see errors about missing browsers, rerun `python -m playwright install`.
- **Session Expiry:**  
  If you are prompted to log in again, simply complete the login in the browser window.
- **Security:**  
  This project is for **personal/local use only**. Do **not** expose your server to the public internet without proper authentication and HTTPS.

---

## 📂 Project Structure
```
.
├── main.py                # FastAPI app with LinkedIn logic
├── run.py                 # Script to launch the server with hot reload
├── requirements.txt       # Python dependencies
├── test_playwright.py     # (Optional) Test script for Playwright install
├── GPT/
│   ├── instructions.txt   # Instructions for your GPT
│   └── openapi.json       # OpenAPI spec for the API
└── ... (other files)
```

---

## 🛡️ Disclaimer
- This project is for educational and personal use only.
- Using automation on LinkedIn may violate their Terms of Service. Use responsibly and at your own risk.

---

**Enjoy your Personal Network Agent!**
If you have questions or need help, open an issue or ask in the repo. 