const LinkedInAssistant = require('../client.js').LinkedInAssistant;
const { fireEvent } = require('@testing-library/dom');
require('@testing-library/jest-dom');

describe('LinkedIn Network Assistant E2E Tests', () => {
  let assistant;
  
  beforeEach(() => {
    resetDOM();
    localStorage.clear();
    fetch.resetMocks();
    assistant = new LinkedInAssistant();
    jest.useFakeTimers();
  });

  afterEach(() => {
    jest.useRealTimers();
  });

  describe('Complete User Flow', () => {
    test('should handle complete conversation flow', async () => {
      // Mock API responses
      fetch
        // Initial thread creation
        .mockResponseOnce(JSON.stringify({ id: 'thread-123' }))
        // Message creation
        .mockResponseOnce(JSON.stringify({ id: 'msg-123' }))
        // Run creation
        .mockResponseOnce(JSON.stringify({ id: 'run-123' }))
        // Run status check
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        // Get messages
        .mockResponseOnce(JSON.stringify({
          data: [{
            content: [{
              text: { value: 'Here is a suggested connection message: "Hi [Name], I noticed we share interests in AI and software development. Would love to connect!"' }
            }]
          }]
        }));

      // 1. Set up configuration
      const apiKey = 'test-api-key';
      const assistantId = 'test-assistant-id';
      document.getElementById('apiKey').value = apiKey;
      document.getElementById('assistantId').value = assistantId;
      assistant.saveConfig();

      // 2. Start new chat
      await assistant.startNewChat();
      expect(assistant.threadId).toBe('thread-123');

      // 3. Send a message
      const userMessage = 'Help me write a connection message for a software developer interested in AI';
      const messageInput = document.getElementById('messageInput');
      const sendButton = document.getElementById('sendButton');

      messageInput.value = userMessage;
      fireEvent.input(messageInput);
      expect(sendButton.disabled).toBe(false);

      // 4. Click send and verify message appears
      await assistant.sendMessage(userMessage);
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain(userMessage);

      // 5. Verify assistant response
      await flushPromises();
      expect(messages.innerHTML).toContain('Here is a suggested connection message');
      expect(messages.innerHTML).toContain('Would love to connect!');

      // 6. Verify UI state
      expect(document.getElementById('typingIndicator').style.display).toBe('none');
      expect(document.querySelector('.status-text').textContent).toBe('Ready');
    });

    test('should handle error scenarios gracefully', async () => {
      // Mock API failures
      fetch
        .mockResponseOnce(JSON.stringify({ id: 'thread-123' }))
        .mockRejectOnce(new Error('Network error'))
        .mockResponseOnce(JSON.stringify({ 
          error: { message: 'Invalid API key' }
        }));

      // 1. Set up configuration
      document.getElementById('apiKey').value = 'invalid-key';
      document.getElementById('assistantId').value = 'test-assistant';
      assistant.saveConfig();

      // 2. Start chat and attempt to send message
      await assistant.startNewChat();
      
      const messageInput = document.getElementById('messageInput');
      messageInput.value = 'Test message';
      fireEvent.input(messageInput);

      // 3. Send message and verify error handling
      try {
        await assistant.sendMessage('Test message');
      } catch (error) {
        // Expected error
      }
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Network error');
    });

    test('should handle rate limiting and retries', async () => {
      // Mock rate limit response followed by success
      fetch
        .mockResponseOnce(JSON.stringify({ id: 'thread-123' }))
        .mockResponseOnce(JSON.stringify({ 
          error: { type: 'rate_limit_exceeded' }
        }))
        .mockResponseOnce(JSON.stringify({ id: 'msg-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'run-123' }))
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        .mockResponseOnce(JSON.stringify({
          data: [{ content: [{ text: { value: 'Response after retry' } }] }]
        }));

      // 1. Set up and start chat
      await assistant.startNewChat();

      // 2. Send message
      const messageInput = document.getElementById('messageInput');
      messageInput.value = 'Test message';
      fireEvent.input(messageInput);

      // 3. Verify rate limit handling
      await assistant.sendMessage('Test message');
      await flushPromises();
      
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Response after retry');
    }, 30000);  // Increase timeout to 30 seconds

    test('should handle long conversations with context', async () => {
      // Mock multiple message exchanges
      fetch
        .mockResponseOnce(JSON.stringify({ id: 'thread-123' }))
        // First exchange
        .mockResponseOnce(JSON.stringify({ id: 'msg-1' }))
        .mockResponseOnce(JSON.stringify({ id: 'run-1' }))
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        .mockResponseOnce(JSON.stringify({
          data: [{ content: [{ text: { value: 'First response' } }] }]
        }))
        // Second exchange
        .mockResponseOnce(JSON.stringify({ id: 'msg-2' }))
        .mockResponseOnce(JSON.stringify({ id: 'run-2' }))
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        .mockResponseOnce(JSON.stringify({
          data: [{ content: [{ text: { value: 'Second response with context' } }] }]
        }));

      // 1. Start chat
      await assistant.startNewChat();

      // 2. First message
      await assistant.sendMessage('First message');
      await flushPromises();

      // 3. Second message
      await assistant.sendMessage('Second message referencing first');
      await flushPromises();

      // 4. Verify conversation flow
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('First response');
      expect(messages.innerHTML).toContain('Second response with context');
    }, 30000);  // Increase timeout to 30 seconds
  });

  describe('Integration with Backend Services', () => {
    test('should handle OpenAI API integration', async () => {
      fetch
        .mockResponseOnce(JSON.stringify({ id: 'thread-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'msg-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'run-123' }))
        .mockResponseOnce(JSON.stringify({
          status: 'requires_action',
          required_action: {
            submit_tool_outputs: {
              tool_calls: [{
                id: 'call-1',
                function: {
                  name: 'analyze_profile',
                  arguments: JSON.stringify({ url: 'https://linkedin.com/test' })
                }
              }]
            }
          }
        }))
        .mockResponseOnce(JSON.stringify({ success: true }))
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        .mockResponseOnce(JSON.stringify({
          data: [{ content: [{ text: { value: 'Profile analysis complete' } }] }]
        }));

      // 1. Configure and start
      await assistant.startNewChat();

      // 2. Send message requiring tool use
      await assistant.sendMessage('Analyze this profile: https://linkedin.com/test');
      await flushPromises();

      // 3. Verify tool execution
      const messages = document.getElementById('messages');
      expect(messages.innerHTML).toContain('Profile analysis complete');
      expect(document.getElementById('asyncRequests').innerHTML).toContain('analyze_profile');
    }, 30000);  // Increase timeout to 30 seconds

    test('should handle file operations', async () => {
      const mockFile = new File(['test content'], 'test.txt', { type: 'text/plain' });
      
      fetch
        .mockResponseOnce(JSON.stringify({ id: 'thread-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'file-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'msg-123' }))
        .mockResponseOnce(JSON.stringify({ id: 'run-123' }))
        .mockResponseOnce(JSON.stringify({ status: 'completed' }))
        .mockResponseOnce(JSON.stringify({
          data: [{ content: [{ text: { value: 'File processed' } }] }]
        }));

      // 1. Start chat
      await assistant.startNewChat();

      // 2. Upload file
      await assistant.uploadFile(mockFile);
      
      // 3. Verify file handling
      expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/files'), expect.any(Object));
      expect(document.getElementById('asyncRequests').innerHTML).toContain('File upload');
    }, 30000);  // Increase timeout to 30 seconds
  });
}); 