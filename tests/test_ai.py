"""Tests for AI client refactoring (TODO #7 - COMPLETED)."""
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
from mitlesen.ai import BaseAIClient, CompletionClient, CompletionStreamClient


class TestBaseAIClient:
    """Test the new BaseAIClient class."""
    
    def test_base_client_openai_setup(self):
        """Test BaseAIClient OpenAI setup."""
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client
                
                client = BaseAIClient(backend="openai")
                assert client.backend == "openai"
                assert client.client is mock_client
                assert client.model == client.model_openai
                assert hasattr(client, '_messages')
                mock_openai.assert_called_once_with(api_key='test-key')
    
    def test_base_client_gemini_setup(self):
        """Test BaseAIClient Gemini setup."""
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_genai.return_value = mock_client
                
                client = BaseAIClient(backend="gemini")
                assert client.backend == "gemini"
                assert client.client is mock_client
                assert client.model == client.model_gemini
                mock_genai.assert_called_once_with(api_key='test-key')
    
    def test_base_client_invalid_backend(self):
        """Test BaseAIClient with invalid backend."""
        with pytest.raises(ValueError, match="Unsupported backend: invalid"):
            BaseAIClient(backend="invalid")
    
    def test_shared_initialization_logic(self):
        """Test that BaseAIClient provides shared initialization logic."""
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_genai.return_value = mock_client
                
                client = BaseAIClient(
                    backend="gemini",
                    language="ja",
                    model_openai="gpt-4",
                    model_gemini="gemini-pro",
                    system_prompt="Custom prompt"
                )
                
                assert client.backend == "gemini"
                assert client.model_openai == "gpt-4"
                assert client.model_gemini == "gemini-pro"
                assert client.system_prompt == "Custom prompt"


class TestRefactoredCompletionClient:
    """Test CompletionClient after refactoring."""
    
    def test_completion_client_inherits_from_base(self):
        """Test that CompletionClient properly inherits from BaseAIClient."""
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_genai.return_value = mock_client
                
                client = CompletionClient(backend="gemini")
                
                # Should be instance of BaseAIClient
                assert isinstance(client, BaseAIClient)
                
                # Should have all base functionality
                assert client.backend == "gemini"
                assert client.client is mock_client
                assert hasattr(client, 'model_openai')
                assert hasattr(client, 'model_gemini')
                assert hasattr(client, 'system_prompt')
    
    def test_completion_client_functionality_preserved(self):
        """Test that CompletionClient functionality is preserved after refactoring."""
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_response = Mock(text="test response")
                mock_client.models.generate_content.return_value = mock_response
                mock_genai.return_value = mock_client
                
                client = CompletionClient(backend="gemini")
                
                # Should still have complete method
                assert hasattr(client, 'complete')
                assert hasattr(client, 'reset')
                
                # Should work as before
                result = client.complete("test prompt")
                assert result == "test response"


class TestRefactoredCompletionStreamClient:
    """Test CompletionStreamClient after refactoring."""
    
    def test_stream_client_inherits_from_base(self):
        """Test that CompletionStreamClient properly inherits from BaseAIClient."""
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_chat = Mock()
                mock_client.chats.create.return_value = mock_chat
                mock_genai.return_value = mock_client
                
                client = CompletionStreamClient(backend="gemini", page_size=20)
                
                # Should be instance of BaseAIClient
                assert isinstance(client, BaseAIClient)
                
                # Should have all base functionality
                assert client.backend == "gemini"
                assert client.client is mock_client
                
                # Should have stream-specific functionality
                assert client.page_size == 20
                assert client.gemini_chat is mock_chat
    
    def test_stream_client_functionality_preserved(self):
        """Test that CompletionStreamClient functionality is preserved after refactoring."""
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_chat = Mock()
                mock_client.chats.create.return_value = mock_chat
                mock_genai.return_value = mock_client
                
                client = CompletionStreamClient(backend="gemini")
                
                # Should still have stream method
                assert hasattr(client, 'stream')
                assert hasattr(client, '_make_user_prompt')
                
                # Should maintain stream-specific attributes
                assert client.page_size == 10  # default
                assert client._page == 0


class TestAIClientRefactoringSuccess:
    """Test that the AI client refactoring was successful (TODO #7 - COMPLETED)."""
    
    def test_redundancy_eliminated(self):
        """Test that redundant initialization code has been eliminated."""
        # Both clients should now use BaseAIClient for common functionality
        with patch.dict(os.environ, {'OPENAI_API_KEY': 'test-key'}):
            with patch('openai.OpenAI') as mock_openai:
                mock_client = Mock()
                mock_openai.return_value = mock_client
                
                completion_client = CompletionClient(backend="openai")
                stream_client = CompletionStreamClient(backend="openai")
                
                # Both should be instances of BaseAIClient
                assert isinstance(completion_client, BaseAIClient)
                assert isinstance(stream_client, BaseAIClient)
                
                # Both should have used the same backend setup
                assert mock_openai.call_count == 2  # Once for each client
                
                # Both should have identical backend configuration
                assert completion_client.backend == stream_client.backend
                assert completion_client.model_openai == stream_client.model_openai
    
    def test_common_interface_extracted(self):
        """Test that common interface has been successfully extracted to BaseAIClient."""
        # BaseAIClient should provide all the common functionality
        base_methods = [method for method in dir(BaseAIClient) if not method.startswith('_')]
        
        # Should have backend setup methods
        assert '_setup_backend' in [method for method in dir(BaseAIClient) if method.startswith('_')]
        assert '_setup_openai' in [method for method in dir(BaseAIClient) if method.startswith('_')]
        assert '_setup_gemini' in [method for method in dir(BaseAIClient) if method.startswith('_')]
    
    def test_backend_configuration_unified(self):
        """Test that backend configuration is now unified."""
        # Both client types should use the same backend configuration logic
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_chat = Mock()
                mock_client.chats.create.return_value = mock_chat
                mock_genai.return_value = mock_client
                
                completion_client = CompletionClient(backend="gemini")
                stream_client = CompletionStreamClient(backend="gemini")
                
                # Both should have the same underlying client
                assert type(completion_client.client) == type(stream_client.client)
                
                # Both should have used the same configuration
                assert completion_client.model_gemini == stream_client.model_gemini
                assert completion_client.system_prompt == stream_client.system_prompt
    
    def test_composition_over_inheritance_for_backends(self):
        """Test that backend-specific behavior now uses composition."""
        # BaseAIClient should handle backend setup through composition
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client') as mock_genai:
                mock_client = Mock()
                mock_genai.return_value = mock_client
                
                client = BaseAIClient(backend="gemini")
                
                # Should have a client attribute (composition)
                assert hasattr(client, 'client')
                assert client.client is mock_client
                
                # Should have backend-specific setup methods
                assert hasattr(client, '_setup_backend')
                assert hasattr(client, '_setup_openai')
                assert hasattr(client, '_setup_gemini')
    
    def test_configuration_management_unified(self):
        """Test that configuration management is now unified."""
        # Both clients should use the same configuration parameters
        config_params = {
            'backend': 'gemini',
            'language': 'ja',
            'model_openai': 'gpt-4',
            'model_gemini': 'gemini-pro',
            'system_prompt': 'Custom prompt'
        }
        
        with patch.dict(os.environ, {'GEMINI_KEY': 'test-key'}):
            with patch('google.genai.Client'):
                completion_client = CompletionClient(**config_params)
                stream_client = CompletionStreamClient(**config_params, page_size=15)
                
                # Should have identical configuration (except stream-specific)
                assert completion_client.backend == stream_client.backend
                assert completion_client.model_openai == stream_client.model_openai
                assert completion_client.model_gemini == stream_client.model_gemini
                assert completion_client.system_prompt == stream_client.system_prompt
                
                # Stream client should have additional stream-specific config
                assert stream_client.page_size == 15