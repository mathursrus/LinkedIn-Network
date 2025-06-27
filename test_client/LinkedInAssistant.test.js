const { LinkedInAssistant } = require('../client.js');
require('@testing-library/jest-dom');
const { fireEvent } = require('@testing-library/dom');

describe('LinkedInAssistant', () => {
  let assistant;
  
  beforeEach(() => {
    // Reset DOM state
    resetDOM();
    // Reset localStorage mock
    localStorage.clear();
    // Reset fetch mock
    fetch.resetMocks();
    // Create new assistant instance
    assistant = new LinkedInAssistant();
  });

  describe('Initialization', () => {
    test('should initialize with default values', () => {
      expect(assistant.threadId).toBe('');
      expect(assistant.isProcessing).toBe(false);
      expect(assistant.asyncRequests.size).toBe(0);
    });

    test('should load configuration from localStorage', () => {
      const testApiKey = 'test-key';
      const testAssistantId = 'test-assistant';
      
      localStorage.getItem.mockReturnValueOnce(testApiKey);
      localStorage.getItem.mockReturnValueOnce(testAssistantId);
      
      assistant = new LinkedInAssistant();
      
      const apiKeyInput = document.getElementById('apiKey');
      const assistantIdInput = document.getElementById('assistantId');
      
      expect(apiKeyInput.value).toBe(testApiKey);
      expect(assistantIdInput.value).toBe(testAssistantId);
    });

    test('should fetch config from server if not in localStorage', async () => {
      const testApiKey = 'test-key';
      fetch.mockResponseOnce(JSON.stringify({ api_key: testApiKey }));
      
      const result = await assistant.fetchApiKeyFromServer();
      
      expect(result).toBe(testApiKey);
      expect(fetch).toHaveBeenCalledWith('/get_api_key');
    });
  });

  describe('Thread Management', () => {
    test('should create new thread', async () => {
      const testThreadId = 'thread-123';
      fetch.mockResponseOnce(JSON.stringify({ id: testThreadId }));
      
      const thread = await assistant.createThread();
      
      expect(thread.id).toBe(testThreadId);
      expect(fetch).toHaveBeenCalledTimes(1);
    });

    test('should add message to thread', async () => {
      assistant.threadId = 'thread-123';
      const testMessage = 'Test message';
      
      fetch.mockResponseOnce(JSON.stringify({ id: 'msg-123' }));
      
      await assistant.sendMessage(testMessage);
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain(testMessage);
    });
  });

  describe('Message Processing', () => {
    test('should handle message sending', async () => {
      assistant.threadId = 'thread-123';
      
      fetch
        .mockResponseOnce(JSON.stringify({ id: 'msg-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'run-123', status: 'completed' }))
        .mockResponseOnce(JSON.stringify({ messages: [] }));
      
      await assistant.sendMessage('Test message');
      
      expect(fetch).toHaveBeenCalledTimes(3);
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Test message');
    });

    test('should handle message formatting', () => {
      const message = '**Bold** and `code` and ```js\nconsole.log();\n```';
      const formatted = assistant.formatMessage(message);
      
      expect(formatted).toContain('<strong>Bold</strong>');
      expect(formatted).toContain('class="inline-code"');
      expect(formatted).toMatch(/class="code-block.*?js/);
    });
  });

  describe('UI Updates', () => {
    test('should update send button state', () => {
      const messageInput = document.getElementById('messageInput');
      const sendButton = document.getElementById('sendButton');
      
      messageInput.value = 'Test message';
      messageInput.dispatchEvent(new Event('input'));
      
      expect(sendButton.disabled).toBe(false);
      
      messageInput.value = '';
      messageInput.dispatchEvent(new Event('input'));
      
      expect(sendButton.disabled).toBe(true);
    });

    test('should update status', () => {
      const status = document.querySelector('.status-text');
      const indicator = document.querySelector('.status-indicator');
      
      assistant.updateStatus('Processing', 'busy');
      
      expect(status.textContent).toBe('Processing');
      expect(indicator.className).toContain('busy');
    });

    test('should handle typing indicator', () => {
      const indicator = document.getElementById('typingIndicator');
      
      assistant.showTypingIndicator();
      expect(indicator.style.display).toBe('block');
      
      assistant.hideTypingIndicator();
      expect(indicator.style.display).toBe('none');
    });
  });

  describe('Async Request Handling', () => {
    test('should manage async requests', () => {
      const requestId = assistant.generateRequestId();
      assistant.addAsyncRequest(requestId, 'Test operation');
      
      const container = document.getElementById('asyncRequests');
      expect(container.innerHTML).toContain('Test operation');
      
      assistant.updateAsyncRequest(requestId, 'completed', 100);
      expect(container.innerHTML).toContain('completed');
    });

    test('should handle multiple async requests', () => {
      const requestId1 = assistant.generateRequestId();
      const requestId2 = assistant.generateRequestId();
      
      assistant.addAsyncRequest(requestId1, 'Operation 1');
      assistant.addAsyncRequest(requestId2, 'Operation 2');
      
      const container = document.getElementById('asyncRequests');
      expect(container.children.length).toBe(2);
    });
  });

  describe('Configuration Management', () => {
    test('should save and load configuration', () => {
      const apiKey = 'test-key';
      const assistantId = 'test-id';
      
      document.getElementById('apiKey').value = apiKey;
      document.getElementById('assistantId').value = assistantId;
      
      assistant.saveConfig();
      
      expect(localStorage.setItem).toHaveBeenCalledWith('openai_api_key', apiKey);
      expect(localStorage.setItem).toHaveBeenCalledWith('assistant_id', assistantId);
    });

    test('should start new chat', async () => {
      await assistant.startNewChat();
      
      expect(localStorage.removeItem).toHaveBeenCalledWith('thread_id');
      expect(fetch).toHaveBeenCalled();
      expect(document.getElementById('messages').innerHTML).toContain('New chat started');
    });
  });
}); 