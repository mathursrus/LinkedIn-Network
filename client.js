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
        
        // Add styles for async indicators
        if (!document.getElementById('async-indicator-styles')) {
            const styles = document.createElement('style');
            styles.id = 'async-indicator-styles';
            styles.textContent = `
                .async-indicator {
                    display: inline-block;
                    margin-left: 8px;
                    vertical-align: middle;
                    color: #666;
                    transition: all 0.3s ease;
                }
                .async-indicator.processing svg {
                    animation: spin 2s linear infinite;
                }
                .async-indicator.complete {
                    color: #28a745;
                }
                .async-indicator.error {
                    color: #dc3545;
                }
                @keyframes spin {
                    100% { transform: rotate(360deg); }
                }
            `;
            document.head.appendChild(styles);
        }
        
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
            
            console.info('✅ Assistant initialized successfully!');
        } catch (error) {
            console.error('❌ Failed to initialize assistant:', error);
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

    async sendMessage(content, showInUI = true) {
        if (!content.trim() || this.isProcessing) return;
        
        // Store the current message for async context
        this.currentUserMessage = content;
        
        console.log(`Sending message: "${content}"`);
        this.isProcessing = true; // Lock sending
        this.updateSendButton();
        
        try {
            const userMsgId = showInUI ? this.addMessage('user', content) : null;
            
            console.log("Adding message to thread...");
            await this.addMessageToThread(content);
            console.log("Message added.");
            
            console.log("Creating run...");
            const run = await this.createRun();
            console.log("Run created with ID:", run.id);

            await this.pollRun(run.id, userMsgId, content); 
            
        } catch (error) {
            console.error('❌ Error sending message:', error);
            if (showInUI) {
                this.addMessage('assistant', `Error: ${error.message}`);
            }
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
                assistant_id: this.assistantId,
                tool_choice: "auto"
            })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            console.error("OpenAI API Error details:", errorData);
            throw new Error(`Failed to create run: ${errorData.error?.message || response.statusText}`);
        }

        const data = await response.json();
        if (!data.id) {
            console.error("Invalid run response:", data);
            throw new Error("Invalid run response from OpenAI API");
        }

        return data;
    }

    async pollRun(runId, userMsgId, originalContent, showInUI = true) {
        console.log(`Polling run ${runId}...`);
        showInUI ? this.showTypingIndicator() : this.hideTypingIndicator();
        try {
            while (true) {
                const runStatus = await this.getRun(runId);
                console.log("Current run status:", runStatus.status);

                if (runStatus.status === 'completed') {
                    if (showInUI) console.log("Run completed. Fetching messages.");
                    if (showInUI) await this.handleCompletedRun();
                    break;
                } else if (runStatus.status === 'requires_action') {
                    console.log("Run requires action. Handling...");
                    const result = await this.handleRequiredAction(runId, runStatus.required_action, userMsgId, originalContent);
                    if (result === "server_processing") {
                        break;
                    } 
                } else if (['failed', 'cancelled', 'expired'].includes(runStatus.status)) {
                    if (showInUI) this.hideTypingIndicator();
                    console.error("Run ended with status:", runStatus.status);
                    if (showInUI) this.addMessage('assistant', `Hmmm ... I hit the following error: ${runStatus.error?.message}.`);
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
        
        // We expect only one tool call
        const toolCall = requiredAction.submit_tool_outputs.tool_calls[0];
        const functionName = toolCall.function.name;
        const args = JSON.parse(toolCall.function.arguments);
        console.log(`Executing function: ${functionName} with args:`, args);

        try {
            const result = await this.executeFunctionWithAsync(runId, toolCall.id, functionName, args, userMsgId, originalContent);
            console.log(`Function ${functionName} executed. Result:`, result);
            
            // If it's a processing result, store context and start polling
            if (result.status === 'processing' && result.job_id) {
                const asyncContext = {
                    run_id: runId,
                    tool_call_id: toolCall.id,
                    job_id: result.job_id,
                    original_user_message: originalContent
                };
                
                // This function will now ALWAYS return immediately for processing jobs
                this.addMessage('assistant', "I'm searching " + functionName + " with args " + JSON.stringify(args) + ". You'll see a spinning loader icon next to your message while I'm working on it. When the search is done, the icon will change to either a green checkmark or a red X. Just click the icon to see the results!");
                
                this.hideTypingIndicator();
                
                // Start polling but don't wait for it
                this.pollJobStatus(result.job_id, this.generateRequestId(), asyncContext);
                return "server_processing";
            }
            
            // For immediate results, submit them back
            await this.submitToolOutputs(runId, [{
                tool_call_id: toolCall.id,
                output: result.status === 'complete' ? JSON.stringify(result.results) : JSON.stringify(result.error)
            }]);
            return "server_complete";
            
        } catch (error) {
            console.error(`❌ Error executing tool ${functionName}:`, error);
            await this.submitToolOutputs(runId, [{
                tool_call_id: toolCall.id,
                output: JSON.stringify(error.message)
            }]);
        }
    }

    async executeFunctionWithAsync(runId, toolCallId, functionName, args, userMsgId, originalContent) {
        console.log(`Executing function ${functionName} with args:`, args);
        let endpoint, requestBody = null, method = 'POST';
        const requestId = this.generateRequestId();

        try {
            if (functionName === 'who_do_i_know_at_company') {
                endpoint = 'http://localhost:8001/who_do_i_know_at_company?company=' + encodeURIComponent(args.company);
                requestBody = null;
                method = 'GET';
            } else if (functionName === 'who_works_as_role_at_company') {
                endpoint = 'http://localhost:8001/who_works_as_role_at_company?role=' + encodeURIComponent(args.role) + '&company=' + encodeURIComponent(args.company);
                requestBody = null;
                method = 'GET';
            } else if (functionName === 'who_can_introduce_me_to_person') {
                endpoint = 'http://localhost:8001/who_can_introduce_me_to_person?' + (args.profile_url ? 'profile_url=' + encodeURIComponent(args.profile_url) : 'person=' + encodeURIComponent(args.person) + '&company=' + encodeURIComponent(args.company));
                requestBody = null;
                method = 'GET';
            } else if (functionName === 'who_does_person_know_at_company') {
                endpoint = 'http://localhost:8001/who_does_person_know_at_company?company_name=' + encodeURIComponent(args.company_name) + '&' + (args.profile_url ? 'profile_url=' + encodeURIComponent(args.profile_url) : 'person_name=' + encodeURIComponent(args.person_name));
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
            const result = await response.json();
            console.log("Received data from server:", result);

            if (result.status === 'processing') {

                // Show the async indicator for this request
                this.showAsyncIndicator(userMsgId, 'processing', requestId, functionName, args, originalContent);

                const asyncContext = {
                    run_id: runId,
                    tool_call_id: toolCallId,
                    job_id: result.job_id,
                    original_content: originalContent,
                    userMsgId: userMsgId
                };
               
                // Start polling but don't wait for it
                this.pollJobStatus(result.job_id, requestId, asyncContext);
            }

            // For immediate results, return them
            return result;

        } catch (error) {
            console.error('Error executing function:', error);
            this.updateAsyncIndicator(requestId, 'error', { error: error.message });
            throw error;
        }
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
            if (status === 'processing') return; 
            let response = data.assistantResponse;
            if (status === 'complete') {
                indicator.className = 'async-indicator complete';
                indicator.innerHTML = icons.complete;
                indicator.title = 'Success! Results are ready. Click here to see them.';
            } else if (status === 'error') {
                indicator.className = 'async-indicator error';
                indicator.innerHTML = icons.error;
                indicator.title = `Job failed. Click here to see why.`;
                response = response? response + "\n\n The specific error was: " + data.error : "The specific error was: " + data.error;
            }
            indicator.style.cursor = 'pointer';
            indicator.onclick = () => {
                // If we have the assistant's response, display it directly
                response = response || "Funny .. I thought I had a response, but I don't. Try again with a different query?";
                this.addMessage('assistant', response);
                // remove the indicator
                indicator.remove();
            };
        });
    }

    async submitToolOutputs(runId, toolOutputs) {
        // Check run status first
        const statusResponse = await fetch(`https://api.openai.com/v1/threads/${this.threadId}/runs/${runId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.apiKey}`,
                'Content-Type': 'application/json',
                'OpenAI-Beta': 'assistants=v2'
            }
        });
        
        if (!statusResponse.ok) {
            console.log(`Run ${runId} status check failed:`, await statusResponse.text());
            throw new Error('Run status check failed');
        }
        
        const runStatus = await statusResponse.json();
        console.log(`Run ${runId} status:`, runStatus.status);
        
        // Only submit if run is still in progress
        if (runStatus.status !== 'requires_action') {
            console.log(`Run ${runId} is in state ${runStatus.status}, not submitting outputs`);
            throw new Error(`Run is in state ${runStatus.status}`);
        }

        console.log(`Submitting Tool outputs: ${JSON.stringify(toolOutputs)}`);

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
            throw new Error(`Failed to submit tool outputs: ${response.error}`);
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
        // If content contains HTML tags, return as-is
        if (typeof content === 'string' && /<[a-z][\s\S]*>/i.test(content)) {
            return content;
        }

        // Otherwise, format as markdown
        // Format code blocks
        content = content.replace(/```(\w+)?\n([\s\S]*?)\n```/g, (match, lang, code) => {
            return `<pre class="code-block ${lang || ''}">${code}</pre>`;
        });
        
        // Format inline code
        content = content.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');
        
        // Format headings (### style)
        content = content.replace(/^###\s+(.*)$/gm, '<h3>$1</h3>');
        content = content.replace(/^##\s+(.*)$/gm, '<h2>$1</h2>');
        content = content.replace(/^#\s+(.*)$/gm, '<h1>$1</h1>');
        
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

    updateSendButton() {
        const sendButton = document.getElementById('sendButton');
        const messageInput = document.getElementById('messageInput');
        sendButton.disabled = !messageInput.value.trim() || this.isProcessing;
    }

    // Async Request Management
    generateRequestId() {
        return 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
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
        
        try {
            // Create a new thread
            const thread = await this.createThread();
            
            // Store the new thread ID
            localStorage.setItem('thread_id', thread.id);
            console.log("New thread created for new chat:", thread.id);
            
            // Refresh the page to reset UI state
            window.location.reload();
            
        } catch (error) {
            console.error('❌ Failed to start new chat:', error);
            this.addMessage('assistant', `Error starting new chat: ${error.message}`);
            this.isProcessing = false;
            this.updateSendButton();
        }
    }

    async pollJobStatus(jobId, requestId, asyncContext) {
        let retries = 0;
        const maxRetries = 360; // 30 minutes with 5-second intervals
        
        while (retries < maxRetries) {
            try {
                const response = await fetch(`http://localhost:8001/job_status/${jobId}`);
                const data = await response.json();
                
                if (data.status === 'complete') {
                    if (asyncContext) {
                        try {
                            // Submit results back to assistant
                            await this.submitToolOutputs(asyncContext.run_id, [{
                                tool_call_id: asyncContext.tool_call_id,
                                output: JSON.stringify(data.results)
                            }]);
                            
                            // Poll for the run completion
                            const runResult = await this.pollRun(asyncContext.run_id, asyncContext.userMsgId, asyncContext.originalContent, false);
                            
                            // Store the result with the context for when user clicks notification
                            const resultContext = {
                                ...asyncContext,
                                assistantResponse: runResult
                            };

                            // Only update UI after we have the assistant's response
                            this.updateAsyncIndicator(requestId, 'complete', resultContext);
                            
                        } catch (error) {
                            console.error('Error processing complete job:', error);
                            this.updateAsyncIndicator(requestId, 'error', { error: error.message });
                            throw error;
                        }
                    }
                    return data;
                } else if (data.status === 'error') {
                    if (asyncContext) {
                        try {
                            // Submit error to assistant
                            await this.submitToolOutputs(asyncContext.run_id, [{
                                tool_call_id: asyncContext.tool_call_id,
                                output: JSON.stringify(data.error)
                            }]);
                            
                            // Poll for the run completion to get assistant's error handling response
                            const runResult = await this.pollRun(asyncContext.run_id, asyncContext.userMsgId, asyncContext.originalContent, false);
                            
                            // Store the error result with context
                            const resultContext = {
                                ...asyncContext,
                                assistantResponse: runResult,
                                error: data.error
                            };
                            // Only update UI after we have the assistant's response
                            this.updateAsyncIndicator(requestId, 'error', resultContext);
                        } catch (error) {
                            console.error('Error processing job error:', error);
                            this.updateAsyncIndicator(requestId, 'error', { error: error.message });
                            throw error;
                        }
                    }
                } else if (data.status === 'processing') {
                    await new Promise(resolve => setTimeout(resolve, 5000));
                    retries++;
                } else {
                    throw new Error(`Unknown status: ${data.status}`);
                }
            } catch (error) {
                this.updateAsyncIndicator(requestId, 'error', { error: error.message });
                throw error;
            }
        }
        
        const error = new Error('Operation timed out');
        this.updateAsyncIndicator(requestId, 'error', { error: error.message });
        throw error;
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
    return false; // Prevent default behavior
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

    
    