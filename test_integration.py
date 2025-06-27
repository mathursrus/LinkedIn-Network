import pytest
import asyncio
import aiohttp
import json
from unittest.mock import patch, MagicMock
from linkedin_network_builder import LinkedInNetworkBuilder
from rate_limiter import RateLimiter
from assistant_manager import AssistantManager

@pytest.fixture
async def app():
    builder = LinkedInNetworkBuilder()
    rate_limiter = RateLimiter()
    assistant_manager = AssistantManager()
    
    # Configure test settings
    builder.configure(
        api_key='test-key',
        assistant_id='test-assistant',
        max_retries=3,
        retry_delay=1
    )
    
    return builder, rate_limiter, assistant_manager

@pytest.mark.asyncio
async def test_end_to_end_message_flow(app):
    builder, rate_limiter, assistant_manager = app
    
    # Mock OpenAI API responses
    with patch('aiohttp.ClientSession.post') as mock_post, \
         patch('aiohttp.ClientSession.get') as mock_get:
        
        # Mock thread creation
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={'id': 'thread-123'})
        
        # Mock message creation
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={'id': 'msg-123'})
        
        # Mock run creation and completion
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={'id': 'run-123', 'status': 'completed'})
        
        # Mock message retrieval
        mock_get.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={
                'data': [{
                    'content': [{
                        'text': {
                            'value': 'Test response'
                        }
                    }]
                }]
            })
        
        # Test complete message flow
        thread_id = await builder.create_thread()
        assert thread_id == 'thread-123'
        
        message_id = await builder.add_message(thread_id, 'Test message')
        assert message_id == 'msg-123'
        
        run_id = await builder.create_run(thread_id)
        assert run_id == 'run-123'
        
        response = await builder.get_completion(thread_id, run_id)
        assert 'Test response' in response

@pytest.mark.asyncio
async def test_rate_limiting_integration(app):
    builder, rate_limiter, _ = app
    
    # Configure stricter rate limits for testing
    rate_limiter.configure(
        requests_per_minute=2,
        burst_limit=3
    )
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={'id': 'thread-123'})
        
        # Test rate limiting
        for _ in range(3):  # Should succeed
            thread_id = await builder.create_thread()
            assert thread_id == 'thread-123'
        
        # Should be rate limited
        with pytest.raises(Exception) as exc_info:
            await builder.create_thread()
        assert 'Rate limit exceeded' in str(exc_info.value)
        
        # Wait for rate limit to reset
        await asyncio.sleep(60)
        
        # Should succeed again
        thread_id = await builder.create_thread()
        assert thread_id == 'thread-123'

@pytest.mark.asyncio
async def test_assistant_integration(app):
    _, _, assistant_manager = app
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        # Mock assistant creation
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={
                'id': 'assistant-123',
                'name': 'Test Assistant',
                'instructions': 'Test instructions'
            })
        
        # Test assistant creation
        assistant_id = await assistant_manager.create_assistant(
            name='Test Assistant',
            instructions='Test instructions',
            tools=['code_interpreter']
        )
        assert assistant_id == 'assistant-123'
        
        # Test assistant configuration
        config = await assistant_manager.get_assistant_config(assistant_id)
        assert config['name'] == 'Test Assistant'
        assert config['instructions'] == 'Test instructions'

@pytest.mark.asyncio
async def test_error_handling_integration(app):
    builder, _, _ = app
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        # Mock API error
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={
                'error': {
                    'message': 'Invalid API key'
                }
            })
        mock_post.return_value.__aenter__.return_value.status = 401
        
        # Test error handling
        with pytest.raises(Exception) as exc_info:
            await builder.create_thread()
        assert 'Invalid API key' in str(exc_info.value)
        
        # Test retry mechanism
        mock_post.return_value.__aenter__.return_value.status = 500
        with pytest.raises(Exception) as exc_info:
            await builder.create_thread()
        assert 'Max retries exceeded' in str(exc_info.value)
        assert mock_post.call_count == 3  # Should retry 3 times

@pytest.mark.asyncio
async def test_concurrent_requests(app):
    builder, rate_limiter, _ = app
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={'id': 'thread-123'})
        
        # Test concurrent requests
        tasks = [
            builder.create_thread() for _ in range(5)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Some requests should succeed, others should be rate limited
        success_count = sum(1 for r in results if isinstance(r, str))
        error_count = sum(1 for r in results if isinstance(r, Exception))
        
        assert success_count > 0
        assert error_count > 0
        assert success_count + error_count == 5

@pytest.mark.asyncio
async def test_message_processing_integration(app):
    builder, _, _ = app
    
    with patch('aiohttp.ClientSession.post') as mock_post, \
         patch('aiohttp.ClientSession.get') as mock_get:
        
        # Mock successful message flow
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(side_effect=[
                {'id': 'thread-123'},  # Thread creation
                {'id': 'msg-123'},     # Message creation
                {'id': 'run-123'},     # Run creation
                {'status': 'completed'} # Run completion
            ])
        
        mock_get.return_value.__aenter__.return_value.json = \
            MagicMock(return_value={
                'data': [{
                    'content': [{
                        'text': {
                            'value': 'Processed message'
                        }
                    }]
                }]
            })
        
        # Test complete message processing flow
        thread_id = await builder.create_thread()
        message_id = await builder.add_message(thread_id, 'Test message')
        run_id = await builder.create_run(thread_id)
        
        # Test message processing
        response = await builder.process_message(thread_id, 'Test message')
        assert 'Processed message' in response
        
        # Verify all API calls were made
        assert mock_post.call_count == 4
        assert mock_get.call_count == 1

@pytest.mark.asyncio
async def test_tool_execution_integration(app):
    builder, _, _ = app
    
    with patch('aiohttp.ClientSession.post') as mock_post:
        # Mock tool execution flow
        mock_post.return_value.__aenter__.return_value.json = \
            MagicMock(side_effect=[
                {'id': 'thread-123'},
                {'id': 'msg-123'},
                {'id': 'run-123'},
                {
                    'status': 'requires_action',
                    'required_action': {
                        'submit_tool_outputs': {
                            'tool_calls': [{
                                'id': 'call-123',
                                'function': {
                                    'name': 'analyze_profile',
                                    'arguments': '{"url": "https://linkedin.com/test"}'
                                }
                            }]
                        }
                    }
                },
                {'status': 'completed'}
            ])
        
        # Test tool execution flow
        thread_id = await builder.create_thread()
        message_id = await builder.add_message(
            thread_id,
            'Analyze this profile: https://linkedin.com/test'
        )
        
        # Execute tool and verify
        result = await builder.execute_tool(
            'analyze_profile',
            {'url': 'https://linkedin.com/test'}
        )
        assert result['status'] == 'completed'
        assert mock_post.call_count == 5 