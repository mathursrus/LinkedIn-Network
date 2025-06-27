const { LinkedInAssistant } = require('../client.js');

describe('Utility Functions', () => {
  let assistant;

  beforeEach(() => {
    resetDOM();
    assistant = new LinkedInAssistant();
  });

  describe('Message Input Handling', () => {
    test('handleKeyDown should send message on Enter without Shift', () => {
      const textarea = document.getElementById('messageInput');
      const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: false });
      
      textarea.value = 'Test message';
      textarea.dispatchEvent(event);
      
      expect(event.preventDefault).toHaveBeenCalled();
      expect(textarea.value).toBe('Test message');
    });

    test('handleKeyDown should not send message on Shift+Enter', () => {
      const textarea = document.getElementById('messageInput');
      const event = new KeyboardEvent('keydown', { key: 'Enter', shiftKey: true });
      
      textarea.value = 'Test message';
      textarea.dispatchEvent(event);
      
      expect(event.preventDefault).not.toHaveBeenCalled();
      expect(textarea.value).toBe('Test message');
    });

    test('adjustTextareaHeight should update textarea height', () => {
      const textarea = document.getElementById('messageInput');
      textarea.value = 'Test\nMessage\nWith\nMultiple\nLines';
      
      const originalHeight = textarea.style.height;
      textarea.dispatchEvent(new Event('input'));
      
      expect(textarea.style.height).not.toBe(originalHeight);
    });
  });

  describe('Configuration Panel', () => {
    test('toggleConfig should toggle config panel visibility', () => {
      const configPanel = document.getElementById('configPanel');
      configPanel.style.display = 'none';
      
      assistant.toggleConfig();
      expect(configPanel.classList.contains('visible')).toBe(true);
      
      assistant.toggleConfig();
      expect(configPanel.classList.contains('visible')).toBe(false);
    });

    test('saveConfig should update configuration', () => {
      const apiKey = document.getElementById('apiKey');
      const assistantId = document.getElementById('assistantId');
      
      apiKey.value = 'test-key';
      assistantId.value = 'test-id';
      
      assistant.saveConfig();
      
      expect(localStorage.setItem).toHaveBeenCalledWith('openai_api_key', 'test-key');
      expect(localStorage.setItem).toHaveBeenCalledWith('assistant_id', 'test-id');
    });
  });

  describe('Chat Management', () => {
    test('startNewChat should reset chat state', async () => {
      const messages = document.getElementById('messages');
      messages.innerHTML = '<div>Old message</div>';
      
      await assistant.startNewChat();
      
      expect(messages.innerHTML).toContain('New chat started');
      expect(localStorage.removeItem).toHaveBeenCalledWith('thread_id');
    });

    test('fetchApiKeyFromServer should handle server response', async () => {
      const testApiKey = 'test-key';
      fetch.mockResponseOnce(JSON.stringify({ api_key: testApiKey }));
      
      const result = await assistant.fetchApiKeyFromServer();
      
      expect(result).toBe(testApiKey);
      expect(fetch).toHaveBeenCalledWith('/get_api_key');
    });

    test('fetchApiKeyFromServer should handle errors', async () => {
      fetch.mockRejectOnce(new Error('Network error'));
      
      const result = await assistant.fetchApiKeyFromServer();
      
      expect(result).toBeNull();
      expect(console.error).toHaveBeenCalled();
    });
  });

  describe('Message Formatting', () => {
    test('should format code blocks correctly', () => {
      const message = '```python\nprint("Hello")\n```';
      const formatted = assistant.formatMessage(message);
      expect(formatted).toMatch(/class="code-block.*?python/);
      expect(formatted).toContain('print("Hello")');
    });

    test('should format inline code correctly', () => {
      const message = 'Use `console.log()` for debugging';
      const formatted = assistant.formatMessage(message);
      expect(formatted).toMatch(/class="inline-code"/);
      expect(formatted).toContain('console.log()');
    });

    test('should handle markdown links', () => {
      const message = '[Click here](https://example.com)';
      const formatted = assistant.formatMessage(message);
      expect(formatted).toMatch(/<a href="https:\/\/example\.com"/);
      expect(formatted).toContain('Click here');
    });
  });

  describe('Error Handling', () => {
    test('should handle network errors gracefully', async () => {
      fetch.mockRejectOnce(new Error('Network error'));
      
      await assistant.sendMessage('Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Error');
      expect(messages.innerHTML).toContain('Network error');
    });

    test('should handle API rate limits', async () => {
      fetch.mockResponseOnce(JSON.stringify({ error: 'Rate limit exceeded' }), { status: 429 });
      
      await assistant.sendMessage('Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Error');
      expect(messages.innerHTML).toContain('Too Many Requests');
    });

    test('should handle invalid API responses', async () => {
      fetch.mockResponseOnce('Invalid JSON', { status: 500 });
      
      await assistant.sendMessage('Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Error');
    });
  });
}); 