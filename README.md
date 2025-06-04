# 🚀 LinkedIn Network Builder

**The complete all-in-one solution for LinkedIn networking with automatic ChatGPT integration**

## ✨ What This Does

Transform your LinkedIn networking with a powerful tool that:
- **Finds connections** at any company (1st, 2nd, and 3rd degree)
- **Discovers mutual connections** for warm introductions
- **Searches by role** to find specific people you need to meet
- **Automatically sets up ChatGPT** with a custom GPT for easy access
- **Creates secure tunnels** so ChatGPT can access your data

## 🎯 One-Click Setup

**Everything is automated!** Just run one executable and you're ready to go.

### Quick Start (30 seconds)

1. **Download and extract** the `linkedin-network-builder-v1.0.zip` from the main folder
2. **Run** the executable
3. **Choose 'y'** when asked about ChatGPT integration
4. **Login** to ChatGPT when the browser opens
5. **Done!** Your custom GPT is ready to use

## 🛠️ What's Included

- **Single Executable**: Everything bundled into one file
- **Automatic ngrok Tunnel**: Secure public access for ChatGPT
- **GPT Auto-Setup**: Creates "Sid's LinkedIn Network Builder" GPT
- **Professional Templates**: Complete instructions and API schema
- **Error Recovery**: Handles crashes and restarts automatically
- **Clean Interface**: Simple prompts, no technical complexity

## 📋 API Endpoints

Your LinkedIn Network Builder provides these powerful endpoints:

### 🏢 Browse Company People
```
GET /browse_company_people?company=Adobe
```
Returns all your connections at a company with their connection levels.

### 🤝 Find Mutual Connections
```
GET /find_mutual_connections?person=John Smith&company=Adobe
```
Finds mutual connections between you and a specific person at a company.

### 👔 Find People by Role
```
GET /find_people_by_role?role=Software Engineer&company=Adobe
```
Searches for people with specific roles at target companies.

## 🎮 Usage Examples

### Via ChatGPT (Recommended)
Once set up, just chat with your GPT:
- *"Who are my connections at Microsoft?"*
- *"Find mutual connections with Sarah Johnson at Google"*
- *"Who should I connect with at Apple who's a Product Manager?"*

### Via API (Advanced)
Access your tunnel URL directly:
```bash
curl "https://your-ngrok-url.app/browse_company_people?company=Adobe"
```

## 🔧 Technical Features

- **Background Processing**: Large searches run in background with caching
- **Smart Caching**: Results saved to avoid re-scraping
- **Browser Automation**: Uses Playwright for reliable LinkedIn scraping
- **Crash Recovery**: Automatically restarts browser if it crashes
- **Windows Optimized**: Handles Windows-specific asyncio issues

## 📁 File Structure

```
linkedin-network-builder.exe    # Main application (all-in-one)
gpt_manager.py                  # GPT automation (bundled)
ngrok.exe                       # Tunnel software (bundled)
GPT/
  ├── instructions.txt          # GPT instructions template
  └── openapi.json             # API schema template
README.txt                      # Quick start guide
```

## 🚨 Troubleshooting

### Common Issues

**"Browser installation failed"**
- Run as Administrator
- Ensure internet connection
- Try: `linkedin-network-builder.exe --install-browsers`

**"GPT setup failed"**
- Check internet connection
- Ensure you can access ChatGPT
- Try manual setup with the ngrok URL

**"LinkedIn scraping not working"**
- LinkedIn may have changed their layout
- The app uses semantic selectors that adapt to changes
- Contact support if issues persist

### Manual GPT Setup
If automatic setup fails:
1. Note the ngrok HTTPS URL from console
2. Go to https://chatgpt.com/gpts/editor
3. Create new GPT with the URL as an Action

## 🔒 Privacy & Security

- **Local Processing**: All data stays on your machine
- **Secure Tunnels**: ngrok provides HTTPS encryption
- **No Data Storage**: Results cached locally only
- **LinkedIn Login**: Uses your existing LinkedIn session

## 🎯 Perfect For

- **Sales Professionals**: Find warm introductions to prospects
- **Recruiters**: Identify mutual connections with candidates
- **Business Development**: Map networks at target companies
- **Job Seekers**: Find connections at companies you're targeting
- **Entrepreneurs**: Research potential partners and investors

## 🚀 Advanced Usage

### Building from Source
```bash
git clone <repository>
cd linkedin-network-builder
python build_installer.py
```

### Custom Configuration
- Edit `GPT/instructions.txt` for custom GPT behavior
- Modify `GPT/openapi.json` for additional endpoints
- Rebuild with `python build_installer.py`

## 📞 Support

- **Console Output**: Check detailed status messages
- **Error Recovery**: App automatically handles most issues
- **Restart**: Close and reopen if unresponsive
- **Manual Mode**: Use API directly if GPT setup fails

## 🎉 Success Stories

*"Found 15 mutual connections at my target company in 30 seconds!"*

*"The ChatGPT integration makes networking research effortless."*

*"Finally, a tool that actually works with LinkedIn's current layout."*

---

**Ready to supercharge your LinkedIn networking?** 

Download `linkedin-network-builder.exe` and get started in under a minute! 
