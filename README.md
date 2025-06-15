# 🤖 LinkedIn Network Assistant

An intelligent, chat-based application for exploring your LinkedIn network, powered by Python, FastAPI, and the OpenAI Assistants API.

This project provides a web interface where you can have a conversation with an AI assistant to perform complex searches on your LinkedIn network. It uses browser automation (Playwright) on the backend to find connections, analyze relationships, and return the data to the assistant for a natural language response.

## ✨ Features

- **Conversational Interface**: Interact with your LinkedIn network using natural language.
- **Find Company Connections**: Ask for people who work at a specific company (e.g., "Who do I know at Google?").
- **Search by Role**: Find people with a specific job title at a company (e.g., "Find me recruiters at Apple").
- **Discover Mutual Connections**: See who you and a target contact both know.
- **Advanced Connection Search**: Find out if a person in your network knows anyone at a target company (e.g., "Does Jeff Weiner know anyone at Microsoft?").
- **Asynchronous Job Processing**: Long-running searches (like scraping LinkedIn) are handled in the background, so the UI is never blocked.
- **Real-time Status Updates**: Visual icons show you the real-time status of your requests (In Progress, Complete, or Failed).
- **Resilient Caching**: Results are cached on disk, so you never have to run the same search twice.
- **Secure Configuration**: Your OpenAI API key and Assistant ID are managed securely on the server and are never exposed to the client directly.

## ⚙️ How It Works

This application consists of two main parts:

1.  **Backend (Python/FastAPI)**: A server that uses Playwright to perform LinkedIn automation. It manages a queue for browser sessions, handles caching, and serves the frontend. It also securely manages the OpenAI Assistant configuration.
2.  **Frontend (HTML/JS)**: A clean, chat-based web interface that interacts with the OpenAI Assistants API. The assistant uses the backend server as a "tool" to get live data from LinkedIn.

## 📋 Requirements

- Python 3.8+ and `pip`
- A LinkedIn account
- An OpenAI API Key

## 🚀 Getting Started

Follow these steps to get the application running locally.

### 1. Clone the Repository

```bash
git clone <your-repository-url>
cd <repository-directory>
```

### 2. Set Up a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
# Windows
python -m venv venv_new
.\venv_new\Scripts\activate

# macOS/Linux
python3 -m venv venv_new
source venv_new/bin/activate
```

### 3. Install Dependencies

Install all the required Python packages from `requirements.txt`.

```bash
pip install -r requirements.txt
```

This will also install Playwright's browser dependencies. If it fails, you can run `playwright install` manually.

### 4. Configure Your API Key

Create a file named `.env` in the root of the project directory. This file will hold your secret API key.

Add your OpenAI API key to the `.env` file like this:

```
OPENAI_API_KEY="sk-YourSecretKeyHere"
```

The server will automatically load this key when it starts. The `.gitignore` file is already configured to prevent this file from being committed.

### 5. Run the Server

Launch the FastAPI server .

```bash
python linkedin_network_builder.py
```

### 6. Open the Client

Open the `client.html` file in your web browser. The application will initialize, fetch the necessary configuration from the server, and you'll be ready to start chatting.

## 💡 Example Queries

Once the application is running, here are some things you can ask the assistant:

- "Find people who work at OpenAI"
- "Who works as a recruiter at Google?"
- "Does Jeff Weiner know anyone at Anthropic?"
- "Find mutual connections I have with Satya Nadella"
- "Who are the most influential people at Microsoft in the AI division?"
- "Help me write a message to a recruiter at Apple."

## 🚀 LinkedIn Network Builder


## 🚨 Troubleshooting

### Common Issues

**"Browser installation failed"**
- Run as Administrator
- Ensure internet connection
- Try: `linkedin-network-builder.exe --install-browsers`


**"LinkedIn scraping not working"**
- LinkedIn may have changed their layout
- The app uses semantic selectors that adapt to changes
- Contact support if issues persist


## 🔒 Privacy & Security

- **Local Processing**: All data stays on your machine
- **No Data Storage**: Results cached locally only
- **LinkedIn Login**: Uses your existing LinkedIn session

## 🎯 Perfect For

- **Sales Professionals**: Find warm introductions to prospects
- **Recruiters**: Identify mutual connections with candidates
- **Business Development**: Map networks at target companies
- **Job Seekers**: Find connections at companies you're targeting
- **Entrepreneurs**: Research potential partners and investors





## 📞 Support

- **Console Output**: Check detailed status messages
- **Error Recovery**: App automatically handles most issues
- **Restart**: Close and reopen if unresponsive

---


**Made with ❤️ by [Sid Mathur](https://github.com/mathursrus)** 