import '@testing-library/jest-dom';
import 'jest-fetch-mock';

// Mock localStorage
const createLocalStorageMock = () => {
  const store = {};
  const getItem = jest.fn((key) => store[key] || null);
  const setItem = jest.fn((key, value) => {
    store[key] = value;
  });
  const clear = jest.fn(() => {
    Object.keys(store).forEach(key => delete store[key]);
  });
  const removeItem = jest.fn((key) => {
    delete store[key];
  });

  return {
    getItem,
    setItem,
    clear,
    removeItem,
    store,
    _reset() {
      Object.keys(store).forEach(key => delete store[key]);
      getItem.mockClear();
      setItem.mockClear();
      clear.mockClear();
      removeItem.mockClear();
    }
  };
};

const localStorageMock = createLocalStorageMock();
Object.defineProperty(global, 'localStorage', {
  value: localStorageMock,
  writable: true
});

// Mock console methods to avoid noise in tests
global.console = {
  log: jest.fn(),
  error: jest.fn(),
  warn: jest.fn(),
  info: jest.fn(),
  debug: jest.fn()
};

// Setup fetch mock
global.fetch = require('jest-fetch-mock');

// Mock DOM elements that our client.js expects
const setupDOM = () => {
  document.body.innerHTML = `
    <div id="status" class="status">
      <div class="status-text"></div>
      <div class="status-indicator"></div>
    </div>
    <div id="messages" class="messages"></div>
    <div id="typingIndicator" class="typing-indicator" style="display: none;">
      <div class="typing-indicator-bubble">
        <div class="typing-indicator-dot"></div>
        <div class="typing-indicator-dot"></div>
        <div class="typing-indicator-dot"></div>
      </div>
    </div>
    <textarea id="messageInput" placeholder="Type your message..."></textarea>
    <button id="sendButton" onclick="sendMessage()" disabled>Send</button>
    <div id="configPanel" class="config-panel" style="display: none;">
      <input type="text" id="apiKey" placeholder="OpenAI API Key">
      <input type="text" id="assistantId" placeholder="Assistant ID">
      <button onclick="saveConfig()">Save</button>
    </div>
    <div id="asyncRequests" class="async-requests"></div>
    <button onclick="toggleConfig()">⚙️</button>
    <button onclick="startNewChat()">New Chat</button>
  `;
};

// Mock Event constructor
class MockEvent {
  constructor(type, options = {}) {
    this.type = type;
    this.shiftKey = options.shiftKey || false;
    this.preventDefault = jest.fn();
  }
}
global.Event = MockEvent;

// Mock KeyboardEvent constructor
class MockKeyboardEvent extends MockEvent {
  constructor(type, options = {}) {
    super(type, options);
    this.key = options.key || '';
  }
}
global.KeyboardEvent = MockKeyboardEvent;

// Mock window.location
delete window.location;
window.location = {
  href: 'http://localhost:8001',
  protocol: 'http:',
  host: 'localhost:8001',
  hostname: 'localhost',
  port: '8001',
  pathname: '/',
  search: '',
  hash: ''
};

// Setup before each test
beforeEach(() => {
  setupDOM();
  fetch.resetMocks();
  jest.clearAllMocks();
  localStorage._reset();
});

// Export helper functions
global.resetDOM = setupDOM;

// Async test helpers
global.waitFor = (condition, timeout = 5000) => {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const check = () => {
      if (condition()) {
        resolve();
      } else if (Date.now() - start > timeout) {
        reject(new Error('Timeout waiting for condition'));
      } else {
        setTimeout(check, 100);
      }
    };
    check();
  });
};

global.flushPromises = () => new Promise(resolve => setTimeout(resolve, 0));

// Enhanced DOM event simulation
global.simulateEvent = (element, eventName, options = {}) => {
  const event = new MockEvent(eventName, options);
  element.dispatchEvent(event);
  return event;
};

global.simulateKeyEvent = (element, eventName, key, options = {}) => {
  const event = new MockKeyboardEvent(eventName, { ...options, key });
  element.dispatchEvent(event);
  return event;
}; 