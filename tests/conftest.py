"""Test configuration and fixtures."""
import pytest
from unittest.mock import Mock, MagicMock
import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

@pytest.fixture
def mock_supabase_client():
    """Mock Supabase client."""
    client = Mock()
    client.table.return_value = Mock()
    return client

@pytest.fixture
def mock_openai_client():
    """Mock OpenAI client."""
    client = Mock()
    client.chat.completions.create.return_value = Mock(
        choices=[Mock(message=Mock(content="mocked response"))]
    )
    return client

@pytest.fixture
def mock_gemini_client():
    """Mock Gemini client."""
    client = Mock()
    client.generate_content.return_value = Mock(text="mocked response")
    return client

@pytest.fixture
def sample_transcript():
    """Sample transcript data for testing."""
    return {
        "segments": [
            {
                "start": 0.0,
                "end": 2.5,
                "text": "Hello world",
                "words": [
                    {"start": 0.0, "end": 1.0, "word": "Hello"},
                    {"start": 1.0, "end": 2.5, "word": "world"}
                ]
            },
            {
                "start": 2.5,
                "end": 5.0,
                "text": "This is a test",
                "words": [
                    {"start": 2.5, "end": 3.0, "word": "This"},
                    {"start": 3.0, "end": 3.5, "word": "is"},
                    {"start": 3.5, "end": 4.0, "word": "a"},
                    {"start": 4.0, "end": 5.0, "word": "test"}
                ]
            }
        ]
    }

@pytest.fixture
def sample_video_context():
    """Sample video context for pipeline testing."""
    from mitlesen.pipeline.base import PipelineContext
    return PipelineContext(
        video_id="test_video_id",
        title="Test Video",
        description="Test Description",
        channel_name="Test Channel",
        duration=120,
        thumbnail_url="https://example.com/thumb.jpg",
        youtube_url="https://youtube.com/watch?v=test",
        language="en"
    )