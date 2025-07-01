# LinkedIn Network Builder Tests

This directory contains the test suite for the LinkedIn Network Builder application. The tests are organized into three categories:

## Test Categories

### 1. Mock Tests
Mock tests use test doubles and don't interact with real LinkedIn endpoints. These are fast and reliable for testing the basic structure and logic of the application.

To run mock tests:
```bash
pytest -v -m mock
```

### 2. Integration Tests
Integration tests verify the interaction between different components of the system. They use some real components while mocking others.

To run integration tests:
```bash
pytest -v -m integration
```

### 3. End-to-End Tests
E2E tests interact with real LinkedIn endpoints and test the complete workflow of the application. These tests require LinkedIn credentials and take longer to run.

To run E2E tests:
```bash
pytest -v -m e2e
```

## Running Tests

### Prerequisites
1. Install test dependencies:
```bash
pip install -r requirements.txt
```

2. For E2E tests, ensure you have:
   - Valid LinkedIn credentials
   - Chrome/Chromium browser installed
   - `.env` file with LinkedIn credentials (see below)

### Environment Setup
Create a `.env` file in the project root with:
```
LINKEDIN_USERNAME=your_username
LINKEDIN_PASSWORD=your_password
```

### Running Specific Test Files
- Run all tests: `pytest`
- Run a specific test file: `pytest tests/test_api.py`
- Run a specific test: `pytest tests/test_api.py::test_search_role_api`
- Run with coverage: `pytest --cov=.`

### Test Markers
- `@pytest.mark.mock`: Mock tests
- `@pytest.mark.integration`: Integration tests
- `@pytest.mark.e2e`: End-to-end tests

### Common Options
- `-v`: Verbose output
- `-s`: Show print statements
- `--pdb`: Drop into debugger on failures
- `--cov`: Generate coverage report
- `-k "test_name"`: Run tests matching the name

## Test Structure

```
tests/
├── __init__.py
├── test_api.py         # API endpoint tests
├── test_integration.py # Component integration tests
└── test_e2e.py        # End-to-end workflow tests
```

## Adding New Tests

1. Choose the appropriate test category (mock/integration/e2e)
2. Create test functions in the relevant file
3. Use appropriate fixtures from `conftest.py`
4. Add proper markers to categorize the test
5. Follow the existing patterns for similar tests

## Best Practices

1. Use descriptive test names that indicate what's being tested
2. Include docstrings explaining the test purpose
3. Use appropriate assertions to verify results
4. Clean up any test data or files created
5. Keep E2E tests focused on critical paths
6. Use fixtures to reduce code duplication

## Troubleshooting

### Common Issues

1. **LinkedIn Rate Limiting**
   - E2E tests may fail if LinkedIn rate limits are hit
   - Use the `--reruns` option to retry failed tests
   - Consider increasing delays between requests

2. **Browser Issues**
   - Ensure Chrome/Chromium is installed
   - Check if browser session cleanup is working
   - Verify no orphaned browser processes

3. **Test Discovery Issues**
   - Ensure test files start with `test_`
   - Verify test functions start with `test_`
   - Check `pytest.ini` configuration

### Getting Help

1. Check the test logs in `logs/` directory
2. Use `-v` flag for verbose output
3. Enable debug logging in `pytest.ini`
4. Check the main application README for setup issues 