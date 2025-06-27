module.exports = {
  // Test environment
  testEnvironment: 'jsdom',
  
  // File patterns
  testMatch: [
    '**/test_client/**/*.test.js',
    '**/test_client/**/*.spec.js'
  ],
  
  // Coverage configuration
  collectCoverageFrom: [
    'client.js',
    '!**/node_modules/**',
    '!**/vendor/**'
  ],
  
  // Setup files
  setupFilesAfterEnv: [
    '<rootDir>/test_client/setup.js',
    'jest-extended'
  ],
  
  // Transform configuration
  transform: {
    '^.+\\.js$': ['babel-jest', { configFile: './.babelrc' }]
  },
  
  // Module name mapper for static assets
  moduleNameMapper: {
    '\\.(css|less|scss|sass)$': '<rootDir>/test_client/__mocks__/styleMock.js',
    '\\.(jpg|jpeg|png|gif|webp|svg)$': '<rootDir>/test_client/__mocks__/fileMock.js'
  },
  
  // Test environment options
  testEnvironmentOptions: {
    url: 'http://localhost'
  },
  
  // Handle ES modules
  transformIgnorePatterns: [
    'node_modules/(?!(@babel/runtime)/)'
  ],
  
  // Test timeout
  testTimeout: 10000,
  
  // Verbose output
  verbose: true,
  
  // Test runners
  runner: 'jest-runner',
  testRunner: 'jest-circus/runner',
  
  // Parallel test execution
  maxWorkers: '50%',
  
  // Coverage thresholds
  coverageThreshold: {
    global: {
      branches: 80,
      functions: 80,
      lines: 80,
      statements: 80
    }
  },
  
  // Report test results in real time
  reporters: [
    'default',
    ['jest-junit', {
      outputDirectory: './test-results',
      outputName: 'junit.xml',
    }]
  ]
}; 