const { 
    LinkedInAssistant, 
    handleKeyDown, 
    adjustTextareaHeight, 
    toggleConfig, 
    saveConfig, 
    startNewChat, 
    fetchApiKeyFromServer 
} = require('../client.js');

describe('Async Operations', () => {
  let assistant;
  
  beforeEach(() => {
    resetDOM();
    assistant = new LinkedInAssistant();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Run Polling', () => {
    test('should handle completed run', async () => {
      const testResponse = 'Test response';
      fetch
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        .mockResponseOnce(JSON.stringify({
          data: [{ role: 'assistant', content: [{ type: 'text', text: { value: testResponse } }], created_at: Date.now() }]
        }));

      await assistant.pollRun('run-1', 'msg-1', 'Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain(testResponse);
      expect(document.getElementById('typingIndicator')).toBeNull();
    });

    test('should handle required action', async () => {
      const toolCall = {
        id: 'call-1',
        function: {
          name: 'who_do_i_know_at_company',
          arguments: JSON.stringify({ company: 'TestCompany' })
        }
      };

      fetch
        .mockResponseOnce(JSON.stringify({
          status: 'requires_action',
          required_action: {
            submit_tool_outputs: {
              tool_calls: [toolCall]
            }
          }
        }))
        .mockResponseOnce(JSON.stringify({ status: 'complete', results: [] }))
        .mockResponseOnce(JSON.stringify({ success: true }));

      await assistant.pollRun('run-1', 'msg-1', 'Test message');
      
      expect(fetch).toHaveBeenCalled();
    });

    test('should handle failed run', async () => {
      const errorMessage = 'Test error';
      fetch.mockResponseOnce(JSON.stringify({
        status: 'failed',
        error: { message: errorMessage }
      }));

      await assistant.pollRun('run-1', 'msg-1', 'Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain(errorMessage);
      expect(document.getElementById('typingIndicator')).toBeNull();
    });
  });

  describe('Async Indicator Management', () => {
    test('should track multiple async indicators', () => {
      const requestId1 = assistant.generateRequestId();
      const requestId2 = assistant.generateRequestId();
      const msgId1 = assistant.addMessage('user', 'Message 1');
      const msgId2 = assistant.addMessage('user', 'Message 2');
      
      assistant.showAsyncIndicator(msgId1, 'processing', requestId1, 'test_function', {}, 'content1');
      assistant.showAsyncIndicator(msgId2, 'processing', requestId2, 'test_function', {}, 'content2');
      
      const indicators = document.querySelectorAll('.async-indicator');
      expect(indicators.length).toBe(2);
    });

    test('should update async indicator status', () => {
      const requestId = assistant.generateRequestId();
      const msgId = assistant.addMessage('user', 'Test message');
      
      assistant.showAsyncIndicator(msgId, 'processing', requestId, 'test_function', {}, 'content');
      assistant.updateAsyncIndicator(requestId, 'complete', { assistantResponse: 'Success' });
      
      const indicator = document.querySelector('.async-indicator');
      expect(indicator.className).toContain('complete');
      expect(indicator.title).toContain('Success');
    });

    test('should handle async indicator errors', () => {
      const requestId = assistant.generateRequestId();
      const msgId = assistant.addMessage('user', 'Test message');
      
      assistant.showAsyncIndicator(msgId, 'processing', requestId, 'test_function', {}, 'content');
      assistant.updateAsyncIndicator(requestId, 'error', { error: 'Test error' });
      
      const indicator = document.querySelector('.async-indicator');
      expect(indicator.className).toContain('error');
      expect(indicator.title).toContain('Job failed. Click here to see why.');
    });
  });

  describe('Tool Execution', () => {
    test('should execute function with async tracking', async () => {
      const functionName = 'who_do_i_know_at_company';
      const args = { company: 'TestCompany' };
      fetch.mockResponseOnce(JSON.stringify({ status: 'complete', results: [] }));
      
      const result = await assistant.executeFunctionWithAsync('run-1', 'call-1', functionName, args, 'msg-1', 'content');
      
      expect(result).toEqual({ status: 'complete', results: [] });
      expect(fetch).toHaveBeenCalled();
    });

    test('should handle tool execution errors', async () => {
      const functionName = 'unknown_function';
      const args = { param: 'value' };
      
      await expect(assistant.executeFunctionWithAsync('run-1', 'call-1', functionName, args, 'msg-1', 'content'))
        .rejects.toThrow('Unknown function');
    });
  });

  describe('Request Management', () => {
    test('should generate unique request IDs', () => {
      const id1 = assistant.generateRequestId();
      const id2 = assistant.generateRequestId();
      
      expect(id1).not.toBe(id2);
      expect(id1).toMatch(/^req_\d+_[a-z0-9]+$/);
    });

    test('should handle async indicators correctly', () => {
      const requestId = assistant.generateRequestId();
      const msgId = assistant.addMessage('user', 'Test message');
      
      assistant.showAsyncIndicator(msgId, 'processing', requestId, 'test_function', {}, 'content');
      const indicator = document.querySelector('.async-indicator');
      expect(indicator).toBeTruthy();
      expect(indicator.dataset.requestId).toBe(requestId);
    });

    test('should update indicator on completion', () => {
      const requestId = assistant.generateRequestId();
      const msgId = assistant.addMessage('user', 'Test message');
      
      assistant.showAsyncIndicator(msgId, 'processing', requestId, 'test_function', {}, 'content');
      assistant.updateAsyncIndicator(requestId, 'complete', { assistantResponse: 'Done' });
      
      const indicator = document.querySelector('.async-indicator');
      expect(indicator.className).toContain('complete');
    });

    test('should handle indicator clicks', () => {
      const requestId = assistant.generateRequestId();
      const msgId = assistant.addMessage('user', 'Test message');
      
      assistant.showAsyncIndicator(msgId, 'processing', requestId, 'test_function', {}, 'content');
      assistant.updateAsyncIndicator(requestId, 'complete', { assistantResponse: 'Click response' });
      
      const indicator = document.querySelector('.async-indicator');
      indicator.click();
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Click response');
    });
  });

  describe('Message Processing', () => {
    test('should show typing indicator during processing', () => {
      assistant.showTypingIndicator();
      expect(document.getElementById('typingIndicator')).toBeTruthy();
      
      assistant.hideTypingIndicator();
      expect(document.getElementById('typingIndicator')).toBeNull();
    });

    test('should format messages correctly', () => {
      const message = '```python\nprint("Hello")\n```';
      const formatted = assistant.formatMessage(message);
      
      expect(formatted).toMatch(/class="code-block.*?python/);
      expect(formatted).toContain('print("Hello")');
    });

    test('should handle markdown formatting', () => {
      const message = '**Bold** and `code` and [link](https://example.com)';
      const formatted = assistant.formatMessage(message);
      
      expect(formatted).toContain('<strong>Bold</strong>');
      expect(formatted).toMatch(/class="inline-code"/);
      expect(formatted).toMatch(/<a href="https:\/\/example\.com"/);
    });
  });
}); 