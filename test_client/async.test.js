const { LinkedInAssistant } = require('../client.js');

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
          data: [{ content: [{ text: { value: testResponse } }] }]
        }));

      await assistant.pollRun('run-1', 'msg-1', 'Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain(testResponse);
      expect(document.getElementById('typingIndicator').style.display).toBe('none');
    });

    test('should handle required action', async () => {
      const toolCall = {
        id: 'call-1',
        function: {
          name: 'test_function',
          arguments: JSON.stringify({ param: 'value' })
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
        .mockResponseOnce(JSON.stringify({ success: true }));

      const result = await assistant.pollRun('run-1', 'msg-1', 'Test message');
      
      expect(result).toBe(false);
      expect(fetch).toHaveBeenCalledTimes(2);
    });

    test('should handle failed run', async () => {
      const errorMessage = 'Test error';
      fetch.mockResponseOnce(JSON.stringify({
        status: 'failed',
        error: errorMessage
      }));

      await assistant.pollRun('run-1', 'msg-1', 'Test message');
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain(`Error: ${errorMessage}`);
      expect(document.getElementById('typingIndicator').style.display).toBe('none');
    });
  });

  describe('Async Request Tracking', () => {
    test('should track multiple async requests', () => {
      const requestId1 = assistant.generateRequestId();
      const requestId2 = assistant.generateRequestId();
      
      assistant.addAsyncRequest(requestId1, 'Operation 1');
      assistant.addAsyncRequest(requestId2, 'Operation 2');
      
      const container = document.getElementById('asyncRequests');
      expect(container.children.length).toBe(2);
      expect(container.innerHTML).toContain('Operation 1');
      expect(container.innerHTML).toContain('Operation 2');
    });

    test('should update async request status', () => {
      const requestId = assistant.generateRequestId();
      assistant.addAsyncRequest(requestId, 'Test operation');
      
      assistant.updateAsyncRequest(requestId, 'in_progress', 50);
      
      const requestElement = document.getElementById(`async-${requestId}`);
      expect(requestElement.querySelector('.progress-fill').style.width).toBe('50%');
      expect(requestElement.querySelector('.async-request-status').textContent).toBe('in_progress');
    });

    test('should handle async request errors', () => {
      const requestId = assistant.generateRequestId();
      assistant.addAsyncRequest(requestId, 'Test operation');
      
      assistant.updateAsyncRequest(requestId, 'error', 0, 'Test error');
      
      const requestElement = document.getElementById(`async-${requestId}`);
      expect(requestElement.querySelector('.error-message')).toBeTruthy();
      expect(requestElement.querySelector('.error-message').textContent).toBe('Test error');
    });
  });

  describe('Tool Execution', () => {
    test('should execute function with async tracking', async () => {
      const functionName = 'test_function';
      const args = { param: 'value' };
      
      const result = await assistant.executeFunctionWithAsync(functionName, args);
      
      expect(result).toEqual({ success: true, data: 'Test result' });
      expect(document.getElementById('asyncRequests').innerHTML).toContain(functionName);
    });

    test('should handle tool execution errors', async () => {
      const functionName = 'unknown_function';
      const args = { param: 'value' };
      
      await expect(assistant.executeFunctionWithAsync(functionName, args))
        .rejects.toThrow('Unknown function');
      
      expect(document.getElementById('asyncRequests').innerHTML).toContain('error');
    });
  });

  describe('Request Management', () => {
    test('should generate unique request IDs', () => {
      const id1 = assistant.generateRequestId();
      const id2 = assistant.generateRequestId();
      
      expect(id1).not.toBe(id2);
      expect(id1).toMatch(/^req_\d+_[a-z0-9]+$/);
    });

    test('should add async request to queue', () => {
      const requestId = assistant.generateRequestId();
      assistant.addAsyncRequest(requestId, 'Test operation');
      
      const container = document.getElementById('asyncRequests');
      expect(container.classList.contains('visible')).toBe(true);
      expect(container.innerHTML).toContain('Test operation');
    });

    test('should update async request status', () => {
      const requestId = assistant.generateRequestId();
      assistant.addAsyncRequest(requestId, 'Test operation');
      
      assistant.updateAsyncRequest(requestId, 'completed', 100);
      
      const requestElement = document.getElementById(`async-${requestId}`);
      expect(requestElement.querySelector('.progress-fill').style.width).toBe('100%');
      expect(requestElement.querySelector('.async-request-status').textContent).toBe('completed');
    });

    test('should remove completed requests after delay', async () => {
      const requestId = assistant.generateRequestId();
      assistant.addAsyncRequest(requestId, 'Test operation');
      assistant.updateAsyncRequest(requestId, 'completed', 100);
      
      jest.advanceTimersByTime(5000);
      
      const container = document.getElementById('asyncRequests');
      expect(container.innerHTML).not.toContain('Test operation');
    }, 10000);
  });

  describe('Message Processing', () => {
    test('should show typing indicator during processing', () => {
      assistant.showTypingIndicator();
      expect(document.getElementById('typingIndicator').style.display).toBe('block');
      
      assistant.hideTypingIndicator();
      expect(document.getElementById('typingIndicator').style.display).toBe('none');
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