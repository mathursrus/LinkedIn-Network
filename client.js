// LinkedIn Network Assistant Client
class LinkedInAssistant {
    constructor() {
        console.log("LinkedInAssistant constructor called");
        this.apiKey = localStorage.getItem('openai_api_key') || '';
        this.assistantId = localStorage.getItem('assistant_id') || '';
        this.threadId = localStorage.getItem('thread_id') || '';
        this.asyncRequests = new Map();
        this.browser = null;
        this.isProcessing = false;
        
        this.initializeUI();
        this.loadConfig();
        
        // Initialize assistant if we have API key
        if (this.apiKey) {
            console.log("API key found in localStorage. Initializing assistant.");
            this.initializeAssistant();
        } else {
            console.warn("API key not found in localStorage.");
        }

        // Try to fetch API key from server if not set in localStorage
        if (!this.apiKey) {
            console.log("Attempting to fetch API key from server.");
            fetchApiKeyFromServer().then(key => {
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
        
        // Enable send button when there's text
        messageInput.addEventListener('input', () => {
            sendButton.disabled = !messageInput.value.trim() || this.isProcessing;
        });
        
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
        const response = await fetch('https://api.openai.com/v1/threads', {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'assistants=v2'
            }
        });
        
        if (!response.ok) {
            throw new Error(`Failed to create thread: ${response.statusText}`);
        }
        
        return await response.json();
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

    async pollRun(runId, userMsgId, originalContent) {
        console.log(`Polling run ${runId}...`);
        this.showTypingIndicator();
        try {
            while (true) {
                const runStatus = await this.getRun(runId);
                console.log("Current run status:", runStatus.status);

                if (runStatus.status === 'completed') {
                    console.log("Run completed. Fetching messages.");
                    await this.handleCompletedRun();
                    break;
                } else if (runStatus.status === 'requires_action') {
                    console.log("Run requires action. Handling...");
                    await this.handleRequiredAction(runId, runStatus.required_action, userMsgId, originalContent);
                    // After handling action, continue polling
                    // await new Promise(resolve => setTimeout(resolve, 2000)); // Poll every 2 seconds
                    // break;  
                } else if (['failed', 'cancelled', 'expired'].includes(runStatus.status)) {
                    this.hideTypingIndicator();
                    console.error("Run ended with status:", runStatus.status);
                    this.addMessage('assistant', `Run ended with status: ${runStatus.status}.`);
                    break;
                }

                
            }
        } catch (error) {
            this.hideTypingIndicator();
            console.error('❌ Error polling run:', error);
            this.addMessage('assistant', `Error polling run: ${error.message}`);
        }
    }

    async getRun(runId) {
        const response = await fetch(`https://api.openai.com/v1/threads/${this.threadId}/runs/${runId}`, {
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'OpenAI-Beta': 'assistants=v2'
            }
        });

        if (!response.ok) {
            throw new Error(`Failed to get run: ${response.statusText}`);
        }

        return await response.json();
    }

    async handleRequiredAction(runId, requiredAction, userMsgId, originalContent) {
        console.log("Handling required action:", requiredAction);
        const toolOutputs = [];

        for (const toolCall of requiredAction.submit_tool_outputs.tool_calls) {
            const functionName = toolCall.function.name;
            const args = JSON.parse(toolCall.function.arguments);
            console.log(`Executing function: ${functionName} with args:`, args);

            try {
                const result = await this.executeFunctionWithAsync(functionName, args, userMsgId, originalContent);
                console.log(`Function ${functionName} executed. Result:`, result);
                toolOutputs.push({
                    tool_call_id: toolCall.id,
                    output: JSON.stringify(result)
                });
            } catch (error) {
                console.error(`❌ Error executing tool ${functionName}:`, error);
                toolOutputs.push({
                    tool_call_id: toolCall.id,
                    output: JSON.stringify({ error: error.message })
                });
            }
        }

        console.log("Submitting tool outputs:", toolOutputs);
        await this.submitToolOutputs(runId, toolOutputs);
    }

    async executeFunctionWithAsync(functionName, args, userMsgId, originalContent) {
        console.log(`[executeFunctionWithAsync] Function: ${functionName}, Args:`, args);
        let endpoint, requestBody, method = 'GET';
        if (functionName === 'search_linkedin_connections') {
            endpoint = 'http://localhost:8001/browse_company_people?company=' + encodeURIComponent(args.company_name);
            requestBody = null;
            method = 'GET';
        } else if (functionName === 'find_mutual_connections') {
            endpoint = 'http://localhost:8001/find_mutual_connections?person=' + encodeURIComponent(args.person_name) + '&company=' + encodeURIComponent(args.company_name);
            requestBody = null;
            method = 'GET';
        } else if (functionName === 'search_linkedin_role') {
            endpoint = `http://localhost:8001/search_linkedin_role?role=${encodeURIComponent(args.role_name)}&company=${encodeURIComponent(args.company_name)}`;
            requestBody = null;
            method = 'GET';
        } else if (functionName === 'find_connections_at_company_for_person') {
            endpoint = `http://localhost:8001/find_connections_at_company_for_person?person_name=${encodeURIComponent(args.person_name)}&company_name=${encodeURIComponent(args.company_name)}`;
            requestBody = null;
            method = 'GET';
        } else {
            console.error(`Unknown function: ${functionName}`);
            throw new Error(`Unknown function: ${functionName}`);
        }

        console.log(`Fetching from endpoint: ${method} ${endpoint}`);
        const response = await fetch(endpoint, {
            method,
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        console.log("Received data from server:", data);

        // This function will now ALWAYS return immediately for processing jobs
        if (data.status === 'processing' && data.job_id) {
            console.log("Server is processing with Job ID:", data.job_id);
            this.showAsyncIndicator(userMsgId, 'processing', data.job_id, functionName, args, originalContent);
            
            this.pollForResult(data.job_id, functionName, args, userMsgId, originalContent);

            return { 
                status: 'processing', 
                message: "I've started the search for you. You'll see a spinning loader icon next to your message while I'm working on it. When the search is done, the icon will change to a green checkmark. Just click the checkmark to see the results!" 
            };
        }
        
        // Handle immediate results if the server returns them
        if (data.status === 'complete') {
            return data;
        }

        console.warn("Unhandled server response:", data);
        return data; // Fallback
    }

    async pollForResult(jobId, functionName, args, userMsgId, originalContent) {
        console.log(`[pollForResult] Polling job: ${jobId}`);
        const pollInterval = 30000; // 30 seconds
        const maxAttempts = 24; 
        let attempts = 0;

        while (attempts < maxAttempts) {
            attempts++;
            console.log(`Polling attempt ${attempts}/${maxAttempts} for job ${jobId}...`);
            try {
                const response = await fetch(`http://localhost:8001/job_status/${jobId}`);
                if (!response.ok) {
                    throw new Error(`Server returned status ${response.status}`);
                }
                const data = await response.json();

                if (data.status === 'complete') {
                    console.log("Polling successful for job: " + jobId + "! Result:", data);
                    this.updateAsyncIndicator(jobId, 'complete', data);
                    return; 
                }
                else if (data.status === 'error') {
                     console.error("Job failed for job: " + jobId + "! Result:", data);
                     this.updateAsyncIndicator(jobId, 'error', { error: `Job failed: ${data.error}` }); 
                     return; 
                 }
            } catch (error) {
                console.error("❌ Error during polling:", error);
                this.updateAsyncIndicator(jobId, 'error', { error: `Polling failed: ${error.message}` });
                return; // Stop polling on any error
            }
            await new Promise(resolve => setTimeout(resolve, pollInterval));
        }
        console.error("Polling timed out.");
        this.updateAsyncIndicator(jobId, 'error', { error: 'Request timed out.' });
    }

    showAsyncIndicator(userMsgId, status, requestId, functionName, args, originalContent) {
        const msgDiv = document.getElementById(userMsgId);
        if (!msgDiv) return;

        const indicatorId = `indicator-${requestId}`;
        let indicator = msgDiv.querySelector('.async-indicator');
        if (!indicator) {
            indicator = document.createElement('span');
            indicator.id = indicatorId;
            indicator.className = 'async-indicator';
            // Append directly to the message div. CSS will handle the rest.
            msgDiv.appendChild(indicator);
        }

        indicator.dataset.requestId = requestId;
        indicator.dataset.functionName = functionName;
        indicator.dataset.args = JSON.stringify(args);
        indicator.dataset.originalContent = originalContent;

        const icons = {
            processing: `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <line x1="12" y1="2" x2="12" y2="6"></line>
                    <line x1="12" y1="18" x2="12" y2="22"></line>
                    <line x1="4.93" y1="4.93" x2="7.76" y2="7.76"></line>
                    <line x1="16.24" y1="16.24" x2="19.07" y2="19.07"></line>
                    <line x1="2" y1="12" x2="6" y2="12"></line>
                    <line x1="18" y1="12" x2="22" y2="12"></line>
                    <line x1="4.93" y1="19.07" x2="7.76" y2="16.24"></line>
                    <line x1="16.24" y1="7.76" x2="19.07" y2="4.93"></line>
                </svg>`,
            complete: `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>`,
            error: `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>`
        };

        if (status === 'processing') {
            indicator.className = 'async-indicator processing';
            indicator.innerHTML = icons.processing;
            indicator.style.cursor = 'default';
            indicator.title = 'Processing... This may take a minute. The icon will change when the job is complete.';
            indicator.onclick = null;
        }
    }
    
    updateAsyncIndicator(requestId, status, data) {
        const indicators = document.querySelectorAll(`.async-indicator[data-request-id="${requestId}"]`);
        if (indicators.length === 0) return;

        const icons = {
            complete: `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                    <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>`,
            error: `
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="12" cy="12" r="10"></circle>
                    <line x1="15" y1="9" x2="9" y2="15"></line>
                    <line x1="9" y1="9" x2="15" y2="15"></line>
                </svg>`
        };

        indicators.forEach(indicator => {
            if (status === 'complete') {
                indicator.className = 'async-indicator complete';
                indicator.innerHTML = icons.complete;
                indicator.style.cursor = 'pointer';
                indicator.title = 'Success! Results are ready. Click this icon to have the assistant analyze them.';
                indicator.onclick = () => {
                    this.sendMessage(indicator.dataset.originalContent);
                    indicator.remove(); // Or hide it
                };
            } else if (status === 'error') {
                indicator.className = 'async-indicator error';
                indicator.innerHTML = icons.error;
                indicator.title = `Job failed: ${data.error}. Click to try running the search again.`;
                indicator.style.cursor = 'pointer';
                indicator.onclick = () => {
                    this.sendMessage(indicator.dataset.originalContent);
                    indicator.remove();
                };
            }
        });
    }

    async submitToolOutputs(runId, toolOutputs) {
        const response = await fetch(`https://api.openai.com/v1/threads/${this.threadId}/runs/${runId}/submit_tool_outputs`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'assistants=v2'
            },
            body: JSON.stringify({
                tool_outputs: toolOutputs
            })
        });

        if (!response.ok) {
            throw new Error(`Failed to submit tool outputs: ${response.statusText}`);
        }

        return await response.json();
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
        // Basic markdown-like formatting
        return content
            .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
            .replace(/\*(.*?)\*/g, '<em>$1</em>')
            .replace(/\n/g, '<br>');
    }

    showTypingIndicator() {
        if (document.getElementById('typingIndicator')) return; // Don't add if one exists

        const messagesContainer = document.getElementById('messages');
        const typingDiv = document.createElement('div');
        typingDiv.className = 'message assistant';
        typingDiv.id = 'typingIndicator';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'AI';
        
        const typingContent = document.createElement('div');
        typingContent.className = 'message-content';
        typingContent.innerHTML = '<div class="typing-indicator"><div class="typing-dot"></div><div class="typing-dot"></div><div class="typing-dot"></div></div>';
        
        typingDiv.appendChild(avatar);
        typingDiv.appendChild(typingContent);
        messagesContainer.appendChild(typingDiv);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }

    hideTypingIndicator() {
        const typingIndicator = document.getElementById('typingIndicator');
        if (typingIndicator) {
            typingIndicator.remove();
        }
    }

    updateStatus(text, type = 'ready') {
        const statusText = document.getElementById('statusText');
        const statusDot = document.getElementById('statusDot');
        
        statusText.textContent = text;
        statusDot.className = `status-dot ${type}`;
    }

    updateSendButton() {
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');
        sendButton.disabled = !messageInput.value.trim() || this.isProcessing;
    }

    // Async Request Management
    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    addAsyncRequest(id, description) {
        this.asyncRequests.set(id, {
            id,
            description,
            status: 'Processing',
            progress: 0,
            startTime: Date.now()
        });
        this.updateAsyncRequestsUI();
    }

    updateAsyncRequest(id, status, progress = null) {
        const request = this.asyncRequests.get(id);
        if (request) {
            request.status = status;
            if (progress !== null) {
                request.progress = progress;
            }
            this.updateAsyncRequestsUI();
            
            // Remove completed requests after a delay
            if (status === 'Completed' || status.startsWith('Error')) {
                setTimeout(() => {
                    this.asyncRequests.delete(id);
                    this.updateAsyncRequestsUI();
                }, 3000);
            }
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
        console.log("Starting new chat...");
        this.isProcessing = true;
        this.updateSendButton();
        this.updateStatus('Starting new chat...', 'processing');

        // Clear UI
        const messagesContainer = document.getElementById('messages');
        messagesContainer.innerHTML = '';

        // Clear thread from memory and storage
        this.threadId = '';
        localStorage.removeItem('thread_id');
        
        try {
            // Create a new thread
            const thread = await this.createThread();
            this.threadId = thread.id;
            localStorage.setItem('thread_id', this.threadId);
            console.log("New thread created for new chat:", this.threadId);
            
            this.addMessage('assistant', "New chat started. I'm ready to help!");
            this.updateStatus('Ready', 'ready');

        } catch (error) {
            console.error('❌ Failed to start new chat:', error);
            this.addMessage('assistant', `Error starting new chat: ${error.message}`);
            this.updateStatus('Error', 'error');
        } finally {
            this.isProcessing = false;
            this.updateSendButton();
        }
    }
}

// Global functions for HTML event handlers
let assistant;

function initializeApp() {
    assistant = new LinkedInAssistant();
}

function sendMessage() {
    const messageInput = document.getElementById('messageInput');
    const content = messageInput.value.trim();
    
    if (content && assistant) {
        messageInput.value = '';
        adjustTextareaHeight(messageInput);
        assistant.sendMessage(content);
    }
}

function handleKeyDown(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

function adjustTextareaHeight(textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 120) + 'px';
}

function toggleConfig() {
    const panel = document.getElementById('configPanel');
    panel.classList.toggle('visible');
}

function saveConfig() {
    if (assistant) {
        assistant.saveConfig();
    }
}

function startNewChat() {
    if (assistant) {
        assistant.startNewChat();
    }
}

async function fetchApiKeyFromServer() {
    try {
        const response = await fetch('/get_api_key');
        if (response.ok) {
            const data = await response.json();
            return data.api_key;
        }
    } catch (error) {
        // This is expected if the server doesn't have the endpoint.
        // console.warn("Could not fetch API key from server. This is okay if you're setting it manually.");
    }
    return null;
}

// Initialize app when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeApp); 