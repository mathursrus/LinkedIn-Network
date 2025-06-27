// LinkedIn Network Assistant Client
class LinkedInAssistant {
    constructor() {
        console.log("LinkedInAssistant constructor called");
        this.initializeAssistant();
        this.threadId = localStorage.getItem('thread_id') || '';
        this.asyncRequests = new Map();
        this.browser = null;
        this.isProcessing = false;
        
        this.initializeUI();
        this.loadConfig();
        
        // Try to fetch API key from server if not set in localStorage
        if (!this.apiKey) {
            console.log("Attempting to fetch API key from server.");
            this.fetchApiKeyFromServer().then(key => {
                if (key) {
                    console.log("API key fetched from server.");
                    this.apiKey = key;
                    document.getElementById('apiKey').value = key;
                    localStorage.setItem('openai_api_key', key);
                } else {
                    console.warn("Could not fetch API key from server.");
                }
            });
        }
    }

    initializeUI() {
        const messageInput = document.getElementById('messageInput');
        const sendButton = document.getElementById('sendButton');
        
        if (messageInput && sendButton) {
            messageInput.addEventListener('input', () => {
                sendButton.disabled = !messageInput.value.trim() || this.isProcessing;
            });
            
            messageInput.addEventListener('keydown', (event) => this.handleKeyDown(event));
        }
        
        if (sendButton) {
            sendButton.disabled = true;
        }
        
        // Load saved API key
        if (this.apiKey) {
            document.getElementById('apiKey').value = this.apiKey;
        }
        if (this.assistantId) {
            document.getElementById('assistantId').value = this.assistantId;
        }
    }

    async initializeAssistant() {
        try {
            console.info("Initializing assistant...");
            this.updateStatus('Fetching config from server...', 'processing');

            // Fetch config from the server
            const response = await fetch('http://localhost:8001/get_assistant_config');
            if (!response.ok) {
                throw new Error(`Failed to fetch assistant config: ${response.statusText}`);
            }
            const config = await response.json();
            
            this.apiKey = config.openai_api_key;
            this.assistantId = config.assistant_id;

            // Save to local storage and UI
            localStorage.setItem('openai_api_key', this.apiKey);
            localStorage.setItem('assistant_id', this.assistantId);
            document.getElementById('apiKey').value = this.apiKey;
            document.getElementById('assistantId').value = this.assistantId;

            console.log("Using Assistant ID from server:", this.assistantId);
            
            // Create or get existing thread
            if (!this.threadId) {
                console.log("No thread ID found. Creating new thread.");
                const thread = await this.createThread();
                this.threadId = thread.id;
                localStorage.setItem('thread_id', this.threadId);
                console.log("New thread created with ID:", this.threadId);
            } else {
                console.log("Using existing thread ID:", this.threadId);
            }
            
            this.updateStatus('Ready', 'ready');
            console.info('✅ Assistant initialized successfully!');
        } catch (error) {
            console.error('❌ Failed to initialize assistant:', error);
            this.updateStatus('Configuration failed', 'error');
        }
    }

    async createThread() {
        try {
            const response = await fetch('https://api.openai.com/v1/threads', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`,
                    'Content-Type': 'application/json',
                    'OpenAI-Beta': 'assistants=v2'
                }
            });
            
            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Failed to create thread: ${errorData.error?.message || response.statusText}`);
            }
            
            const data = await response.json();
            this.threadId = data.id;
            return data;
        } catch (error) {
            console.error('Failed to create thread:', error);
            throw error;
        }
    }

    async sendMessage(content) {
        if (!content.trim() || this.isProcessing) return;
        
        console.log(`Sending message: "${content}"`);
        this.isProcessing = true; // Lock sending
        this.updateSendButton();
        
        try {
            const userMsgId = this.addMessage('user', content);
            
            console.log("Adding message to thread...");
            await this.addMessageToThread(content);
            console.log("Message added.");
            
            console.log("Creating run...");
            const run = await this.createRun();
            console.log("Run created with ID:", run.id);

            // This now runs and completes before allowing another message.
            await this.pollRun(run.id, userMsgId, content); 
            
        } catch (error) {
            console.error('❌ Error sending message:', error);
            this.addMessage('assistant', `Error: ${error.message}`);
        } finally {
            this.isProcessing = false; // Unlock sending only after everything is done
            this.updateSendButton();
        }
    }

    async addMessageToThread(content) {
        console.log("Adding message to thread with content:", content);
        const response = await fetch(`https://api.openai.com/v1/threads/${this.threadId}/messages`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'assistants=v2'
            },
            body: JSON.stringify({
                role: 'user',
                content: content
            })
        });
        
        if (!response.ok) {
            const errorData = await response.json().catch(() => ({})); // Try to parse error json
            console.error("OpenAI API Error details:", errorData);
            // Throw a more detailed error
            throw new Error(`Failed to add message: ${errorData.error?.message || response.statusText}`);
        }
        
        return await response.json();
    }

    async createRun() {
        const response = await fetch(`https://api.openai.com/v1/threads/${this.threadId}/runs`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'assistants=v2'
            },
            body: JSON.stringify({
                assistant_id: this.assistantId
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to create run: ${response.statusText}`);
        }

        return await response.json();
    }

    async pollRun(runId, messageId, userMessage) {
        try {
            const response = await fetch(`/threads/${this.threadId}/runs/${runId}`);
            const data = await response.json();

            if (data.status === 'completed') {
                const messages = await this.getThreadMessages();
                const lastMessage = messages.data[0];
                if (lastMessage && lastMessage.content && lastMessage.content[0] && lastMessage.content[0].text) {
                    this.addMessageToUI(lastMessage.content[0].text.value, 'assistant');
                }
                this.hideTypingIndicator();
                return true;
            } else if (data.status === 'requires_action' && data.required_action && data.required_action.submit_tool_outputs) {
                const toolCalls = data.required_action.submit_tool_outputs.tool_calls;
                for (const toolCall of toolCalls) {
                    await this.handleToolCall(toolCall, runId);
                }
                return false;
            } else if (data.status === 'failed') {
                this.addMessageToUI(`Error: ${data.error || 'Run failed'}`, 'assistant');
                this.hideTypingIndicator();
                return true;
            }
            return false;
        } catch (error) {
            this.addMessageToUI(`Error polling run: ${error.message}`, 'assistant');
            this.hideTypingIndicator();
            return true;
        }
    }

    async handleToolCall(toolCall, runId) {
        try {
            const { id, function: { name, arguments: args } } = toolCall;
            const result = await this.executeFunctionWithAsync(name, JSON.parse(args));
            await fetch(`/threads/${this.threadId}/runs/${runId}/tool-outputs`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    tool_outputs: [{
                        tool_call_id: id,
                        output: JSON.stringify(result)
                    }]
                })
            });
        } catch (error) {
            console.error('Tool execution failed:', error);
            throw new Error('Tool execution failed');
        }
    }

    async executeFunctionWithAsync(functionName, args) {
        const requestId = this.generateRequestId();
        this.addAsyncRequest(requestId, `Executing ${functionName}`);

        try {
            let result;
            if (functionName === 'test_function') {
                // Mock implementation for testing
                result = { success: true, data: 'Test result' };
            } else {
                console.error(`Unknown function: ${functionName}`);
                throw new Error(`Unknown function: ${functionName}`);
            }

            this.updateAsyncRequest(requestId, 'completed', 100);
            return result;
        } catch (error) {
            this.updateAsyncRequest(requestId, 'error', null, error.message);
            throw error;
        }
    }

    async handleCompletedRun() {
        console.log("Run completed. Fetching and displaying final messages.");
        this.showTypingIndicator(); // Show while we fetch and render final message
        const messages = await this.getThreadMessages();
        // The user's message is already displayed. Find the latest assistant message.
        const lastMessage = messages
            .filter(m => m.role === 'assistant')
            .sort((a, b) => b.created_at - a.created_at)[0];

        if (lastMessage && lastMessage.content && lastMessage.content[0] && lastMessage.content[0].type === 'text') {
            this.addMessage('assistant', lastMessage.content[0].text.value);
        } else {
            console.warn("Could not find a valid text message from the assistant to display.", lastMessage);
        }
        this.hideTypingIndicator();
    }

    async getThreadMessages() {
        console.log("Fetching latest thread messages...");
        try {
            const response = await fetch(`https://api.openai.com/v1/threads/${this.threadId}/messages`, {
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`,
                    'OpenAI-Beta': 'assistants=v2'
                }
            });
            if (!response.ok) throw new Error(`Failed to get messages: ${response.statusText}`);
            const messages = await response.json();
            console.log("Fetched messages:", messages);
            return messages.data;
        } catch (error) {
            console.error("❌ Error fetching thread messages:", error);
            return [];
        }
    }

    // UI Helper Methods
    addMessage(role, content) {
        const messagesContainer = document.getElementById('messages');
        const messageDiv = document.createElement('div');
        const msgId = 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 6);
        messageDiv.className = `message ${role}`;
        messageDiv.id = msgId;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'You' : role === 'assistant' ? 'AI' : 'SYS';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        if (typeof content === 'object') {
            // Display JSON data nicely
            const jsonDiv = document.createElement('div');
            jsonDiv.className = 'json-display';
            jsonDiv.textContent = JSON.stringify(content, null, 2);
            messageContent.appendChild(jsonDiv);
        } else {
            messageContent.innerHTML = this.formatMessage(content);
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        // Scroll to bottom
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
        return msgId;
    }

    formatMessage(content) {
        // Format code blocks
        content = content.replace(/```(\w+)?\n([\s\S]*?)\n```/g, (match, lang, code) => {
            return `<pre class="code-block ${lang || ''}">${code}</pre>`;
        });
        
        // Format inline code
        content = content.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
        
        // Format bold text
        content = content.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
        
        // Format italic text
        content = content.replace(/\*([^*]+)\*/g, '<em>$1</em>');
        
        // Format links
        content = content.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank">$1</a>');
        
        // Replace newlines with <br>
        content = content.replace(/\n/g, '<br>');
        
        return content;
    }

    showTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.style.display = 'block';
        }
    }

    hideTypingIndicator() {
        const indicator = document.getElementById('typingIndicator');
        if (indicator) {
            indicator.style.display = 'none';
        }
    }

    updateStatus(text, type = 'ready') {
        const statusContainer = document.getElementById('status');
        const statusText = statusContainer.querySelector('.status-text');
        const statusIndicator = statusContainer.querySelector('.status-indicator');
        
        if (statusText) {
            statusText.textContent = text;
        }
        
        if (statusIndicator) {
            statusIndicator.className = 'status-indicator ' + type;
        }
    }

    updateSendButton() {
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');
        
        if (sendButton && messageInput) {
            sendButton.disabled = !messageInput.value.trim() || this.isProcessing;
        }
    }

    // Async Request Management
    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    addAsyncRequest(requestId, description) {
        const container = document.getElementById('asyncRequests');
        const requestElement = document.createElement('div');
        requestElement.id = `async-${requestId}`;
        requestElement.className = 'async-request';
        requestElement.innerHTML = `
            <div class="async-request-info">
                <div class="status-dot"></div>
                <span>${description}</span>
            </div>
            <div>
                <div class="async-request-status"></div>
                <div class="progress-bar">
                    <div class="progress-fill" style="width: 0%"></div>
                </div>
            </div>
        `;
        container.appendChild(requestElement);
    }

    updateAsyncRequest(requestId, status, progress = 0, error = null) {
        const requestElement = document.getElementById(`async-${requestId}`);
        if (!requestElement) return;

        const statusElement = requestElement.querySelector('.async-request-status');
        const progressFill = requestElement.querySelector('.progress-fill');
        const statusDot = requestElement.querySelector('.status-dot');

        statusElement.textContent = status;
        progressFill.style.width = `${progress}%`;
        statusDot.className = `status-dot ${status}`;

        if (error) {
            const errorElement = document.createElement('div');
            errorElement.className = 'error-message';
            errorElement.textContent = error;
            requestElement.appendChild(errorElement);
        }

        if (status === 'completed' || status === 'error') {
            setTimeout(() => {
                requestElement.remove();
            }, 5000);
        }
    }

    updateAsyncRequestsUI() {
        const container = document.getElementById('asyncRequests');
        const requests = Array.from(this.asyncRequests.values());
        
        if (requests.length === 0) {
            container.classList.remove('visible');
            return;
        }
        
        container.classList.add('visible');
        container.innerHTML = requests.map(req => `
            <div class="async-request">
                <div class="async-request-info">
                    <div class="status-dot ${req.status === 'Processing' ? 'processing' : req.status.startsWith('Error') ? 'error' : ''}"></div>
                    <span>${req.description}</span>
                </div>
                <div>
                    <div class="async-request-status">${req.status}</div>
                    <div class="progress-bar">
                        <div class="progress-fill" style="width: ${req.progress}%"></div>
                    </div>
                </div>
            </div>
        `).join('');
    }

    // Configuration
    loadConfig() {
        const apiKey = document.getElementById('apiKey');
        const assistantId = document.getElementById('assistantId');
        
        if (this.apiKey) apiKey.value = this.apiKey;
        if (this.assistantId) assistantId.value = this.assistantId;
    }

    saveConfig() {
        const apiKey = document.getElementById('apiKey').value.trim();
        const assistantId = document.getElementById('assistantId').value.trim();
        
        if (!apiKey) {
            alert('Please enter your OpenAI API key');
            return;
        }
        
        this.apiKey = apiKey;
        this.assistantId = assistantId;
        
        localStorage.setItem('openai_api_key', apiKey);
        if (assistantId) {
            localStorage.setItem('assistant_id', assistantId);
        }
        
        // Hide config panel
        document.getElementById('configPanel').classList.remove('visible');
        
        // Reinitialize assistant
        this.initializeAssistant();
    }

    async startNewChat() {
        try {
            // Clear existing thread ID
            this.threadId = '';
            localStorage.removeItem('thread_id');
            
            // Clear messages
            const messagesDiv = document.getElementById('messages');
            messagesDiv.innerHTML = '<div class="message system">New chat started</div>';
            
            // Create new thread
            const thread = await this.createThread();
            this.threadId = thread.id;
            localStorage.setItem('thread_id', this.threadId);
            
            return this.threadId;
        } catch (error) {
            console.error('Failed to start new chat:', error);
            this.addMessage('system', `Error starting new chat: ${error.message}`);
            throw error;
        }
    }

    addMessageToUI(content, role) {
        const messages = document.getElementById('messages');
        if (!messages) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        messageDiv.id = `msg_${Date.now()}_${Math.random().toString(36).substr(2, 6)}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'assistant' ? 'AI' : 'You';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = this.formatMessage(content);
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        messages.appendChild(messageDiv);
        messages.scrollTop = messages.scrollHeight;
    }

    handleKeyDown(event) {
        if (event.key === 'Enter' && !event.shiftKey) {
            event.preventDefault();
            this.sendMessage(event.target.value);
        }
    }

    adjustTextareaHeight(textarea) {
        textarea.style.height = 'auto';
        textarea.style.height = (textarea.scrollHeight) + 'px';
    }

    toggleConfig() {
        const configPanel = document.getElementById('configPanel');
        if (configPanel) {
            configPanel.classList.toggle('visible');
        }
    }

    async fetchApiKeyFromServer() {
        try {
            const response = await fetch('/get_api_key');
            if (!response.ok) {
                throw new Error(`Failed to fetch API key: ${response.statusText}`);
            }
            const data = await response.json();
            return data.api_key;
        } catch (error) {
            console.error('Failed to fetch API key:', error);
            return null;
        }
    }

    async uploadFile(file) {
        const requestId = this.generateRequestId();
        this.addAsyncRequest(requestId, 'File upload');

        try {
            const formData = new FormData();
            formData.append('file', file);
            formData.append('purpose', 'assistants');

            const response = await fetch('https://api.openai.com/v1/files', {
                method: 'POST',
                headers: {
                    'Authorization': `Bearer ${this.apiKey}`,
                    'OpenAI-Beta': 'assistants=v2'
                },
                body: formData
            });

            if (!response.ok) {
                const errorData = await response.json().catch(() => ({}));
                throw new Error(`Failed to upload file: ${errorData.error?.message || response.statusText}`);
            }

            const data = await response.json();
            this.updateAsyncRequest(requestId, 'completed', 100);
            return data;
        } catch (error) {
            this.updateAsyncRequest(requestId, 'error', 0, error.message);
            throw error;
        }
    }
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const assistant = new LinkedInAssistant();
});

// Export the LinkedInAssistant class
module.exports = {
    LinkedInAssistant
}; 