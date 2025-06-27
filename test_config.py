import os
import pytest
import logging
from pathlib import Path

# Test configuration
TEST_CONFIG = {
    'API_KEY': 'test-api-key',
    'ASSISTANT_ID': 'test-assistant-id',
    'MAX_RETRIES': 3,
    'RETRY_DELAY': 1,
    'RATE_LIMIT': {
        'REQUESTS_PER_MINUTE': 60,
        'BURST_LIMIT': 10
    },
    'CACHE': {
        'ENABLED': True,
        'TTL': 3600
    },
    'LOGGING': {
        'LEVEL': logging.DEBUG,
        'FORMAT': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    }
}

# Test data directory setup
TEST_DATA_DIR = Path(__file__).parent / 'test_data'
TEST_DATA_DIR.mkdir(exist_ok=True)

# Cache directory for tests
TEST_CACHE_DIR = TEST_DATA_DIR / 'cache'
TEST_CACHE_DIR.mkdir(exist_ok=True)

# Log directory for tests
TEST_LOG_DIR = TEST_DATA_DIR / 'logs'
TEST_LOG_DIR.mkdir(exist_ok=True)

@pytest.fixture(scope='session')
def test_config():
    return TEST_CONFIG

@pytest.fixture(scope='session')
def test_paths():
    return {
        'data_dir': TEST_DATA_DIR,
        'cache_dir': TEST_CACHE_DIR,
        'log_dir': TEST_LOG_DIR
    }

@pytest.fixture(autouse=True)
def setup_test_env(test_config, test_paths):
    # Set up test environment variables
    os.environ['OPENAI_API_KEY'] = test_config['API_KEY']
    os.environ['ASSISTANT_ID'] = test_config['ASSISTANT_ID']
    
    # Configure logging for tests
    logging.basicConfig(
        level=test_config['LOGGING']['LEVEL'],
        format=test_config['LOGGING']['FORMAT'],
        filename=test_paths['log_dir'] / 'test.log'
    )
    
    # Clean up test directories before each test
    for file in test_paths['cache_dir'].glob('*'):
        file.unlink()
    
    yield
    
    # Clean up after tests
    for file in test_paths['cache_dir'].glob('*'):
        file.unlink()

@pytest.fixture
def mock_openai_responses():
    """Common OpenAI API response mocks"""
    return {
        'thread_creation': {'id': 'thread-123'},
        'message_creation': {'id': 'msg-123'},
        'run_creation': {'id': 'run-123'},
        'run_completion': {'status': 'completed'},
        'message_content': {
            'data': [{
                'content': [{
                    'text': {
                        'value': 'Test response'
                    }
                }]
            }]
        }
    }

@pytest.fixture
def mock_rate_limit_config():
    """Rate limit configuration for tests"""
    return {
        'requests_per_minute': 2,
        'burst_limit': 3,
        'window_size': 60
    }

@pytest.fixture
def mock_cache_config():
    """Cache configuration for tests"""
    return {
        'enabled': True,
        'ttl': 300,
        'max_size': 1000,
        'directory': TEST_CACHE_DIR
    }

@pytest.fixture
def mock_assistant_config():
    """Assistant configuration for tests"""
    return {
        'name': 'Test Assistant',
        'instructions': 'Test instructions',
        'tools': ['code_interpreter'],
        'model': 'gpt-4-1106-preview'
    }

@pytest.fixture
def mock_network_config():
    """Network configuration for tests"""
    return {
        'timeout': 30,
        'max_retries': 3,
        'retry_delay': 1,
        'backoff_factor': 2
    }

# Test data fixtures
@pytest.fixture
def sample_messages():
    """Sample messages for testing"""
    return [
        {
            'role': 'user',
            'content': 'Help me write a connection message'
        },
        {
            'role': 'assistant',
            'content': 'Here is a suggested message: "Hi [Name], I noticed we share interests in AI. Would love to connect!"'
        },
        {
            'role': 'user',
            'content': 'Can you make it more professional?'
        }
    ]

@pytest.fixture
def sample_profiles():
    """Sample LinkedIn profiles for testing"""
    return [
        {
            'url': 'https://linkedin.com/test1',
            'name': 'Test User 1',
            'headline': 'Software Engineer',
            'interests': ['AI', 'Machine Learning']
        },
        {
            'url': 'https://linkedin.com/test2',
            'name': 'Test User 2',
            'headline': 'Data Scientist',
            'interests': ['Deep Learning', 'NLP']
        }
    ]

@pytest.fixture
def sample_tool_calls():
    """Sample tool calls for testing"""
    return [
        {
            'id': 'call-1',
            'function': {
                'name': 'analyze_profile',
                'arguments': '{"url": "https://linkedin.com/test1"}'
            }
        },
        {
            'id': 'call-2',
            'function': {
                'name': 'send_connection',
                'arguments': '{"profile_url": "https://linkedin.com/test2", "message": "Hi, would love to connect!"}'
            }
        }
    ] 