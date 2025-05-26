# LinkedIn Network Builder

A simple desktop application that helps you explore your LinkedIn network and discover people at any company. Find mutual connections to get warm introductions when reaching out to target companies.

---

## 🚀 Quick Start (Recommended)

### For End Users - One-Click Installation

1. **Navigate to** the installer folder
2. **Find the** install.bat file
3. **Right-click** on `install.bat` and select **"Run as Administrator"**
4. **Navigate** to `C:\Users\[YourName]\LinkedIn-Network-Builder`
5. **Double-click** `start-linkedin-network.bat`
6. **Copy** the HTTPS URL that appears (for GPT integration)

That's it! The application will:
- ✅ Install all required browsers automatically
- ✅ Start the API server on your computer
- ✅ Create a secure tunnel for GPT access
- ✅ Save your LinkedIn login for future use

---

## 🔧 How It Works

### First Time Setup
1. When you run the application, a browser window will open
2. **Log in to LinkedIn manually** (handle any security checks)
3. Your session will be saved securely for future use
4. The application runs locally on your computer - your data stays private

### Using the Application
- **Browse Company People**: Find 1st and 2nd degree connections at any company
- **Discover Mutual Connections**: See who can introduce you to 2nd degree connections
- **GPT Integration**: Use the HTTPS URL with ChatGPT for conversational networking

---

## 🤖 GPT Integration

### Setting Up Your Custom GPT
1. **Copy the HTTPS URL** from the application startup
2. **Create a new GPT** in ChatGPT
3. **Add the instruction in GPT/instructions.txt**
4. **Configure the API** using the GPT/openapi.json updated with your HTTPS URL in the servers segment
5. **Save and test** your GPT

### Example GPT Conversations
- "Find people at Anthropic and show me who I can get introductions from"
- "Who do I know at Microsoft that could introduce me to their AI team?"
- "Show me my connections at startups in San Francisco"

---

## 🛠️ Developer Setup (Advanced)

### If You Want to Modify the Code

**Requirements:**
- Python 3.11.x (not 3.12+)
- Git

**Setup:**
```bash
git clone <repository-url>
cd linkedin-network-builder
python -m venv venv
venv\Scripts\activate  # Windows
pip install -r requirements.txt
python -m playwright install
```

**Running:**
```bash
python main.py
```

**Building Installer:**
```bash
python build_installer.py
```

---

## 📋 Features

- **🔍 Company Search**: Find all your connections at any company
- **🤝 Mutual Connections**: Discover who can introduce you to 2nd degree connections  
- **💾 Smart Caching**: Results are cached to avoid repeated LinkedIn requests
- **🔒 Privacy First**: Everything runs locally on your computer
- **🚀 GPT Ready**: Built-in API for ChatGPT integration
- **⚡ One-Click Install**: No technical setup required

---

## 🔧 Troubleshooting

### Common Issues

**"Browser not found" error:**
- Run the installer again as Administrator
- The installer automatically downloads required browsers

**"LinkedIn login required":**
- This is normal on first use or after session expires
- Simply log in manually in the browser window that opens

**GPT can't connect:**
- Make sure `start-linkedin-network.bat` is running
- Copy the HTTPS URL exactly as shown
- Check that your firewall isn't blocking the application

**Application won't start:**
- Right-click `start-linkedin-network.bat` and "Run as Administrator"
- Make sure you're running from the installed location: `C:\Users\[YourName]\LinkedIn-Network-Builder`

---

## 🛡️ Privacy & Security

- **Local Only**: All processing happens on your computer
- **No Data Collection**: Your LinkedIn data never leaves your machine
- **Secure Sessions**: Login credentials are stored locally and encrypted
- **HTTPS Tunnel**: GPT communication is encrypted end-to-end

---

## 📞 Support

Having issues? Here's how to get help:

1. **Check the troubleshooting section** above
2. **Restart the application** (close and run `start-linkedin-network.bat` again)
3. **Run as Administrator** if you're having permission issues
4. **Contact support** with the error message you're seeing

---

## ⚖️ Legal Notice

This tool is for personal networking use only. Please respect LinkedIn's Terms of Service and use responsibly. The application automates browsing your existing network connections - it does not scrape public data or violate privacy settings.

---

**Ready to supercharge your networking? Download the installer and get started in minutes!** 