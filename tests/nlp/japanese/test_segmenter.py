"""Tests for Japanese segmenter (TODO #5 - Large Segmenter Classes)."""
import pytest
from unittest.mock import Mock, patch
from mitlesen.nlp.japanese.segmenter import JapaneseSentenceSegmenter, SentenceMatchError


class TestJapaneseSentenceSegmenter:
    """Test Japanese sentence segmenter."""
    
    @pytest.fixture
    def segmenter(self):
        """Create a Japanese sentence segmenter for testing."""
        with patch('janome.tokenizer.Tokenizer') as mock_tokenizer:
            mock_instance = Mock()
            mock_tokenizer.return_value = mock_instance
            segmenter = JapaneseSentenceSegmenter()
            segmenter.tokenizer = mock_instance
            return segmenter
    
    def test_init(self):
        """Test initialization of Japanese segmenter."""
        with patch('janome.tokenizer.Tokenizer') as mock_tokenizer:
            mock_instance = Mock()
            mock_tokenizer.return_value = mock_instance
            segmenter = JapaneseSentenceSegmenter()
            mock_tokenizer.assert_called_once()
            assert segmenter.tokenizer is mock_instance
    
    def test_split_long_sentence_basic(self, segmenter):
        """Test basic sentence splitting functionality."""
        long_sentence = "これは非常に長い文章です。分割されるべきです。"
        result = segmenter.split_long_sentence(long_sentence, max_length=20)
        
        # Should return a list of shorter segments
        assert isinstance(result, list)
        assert len(result) > 0
        assert all(isinstance(segment, str) for segment in result)
    
    def test_segment_transcripts_structure(self, segmenter):
        """Test segment_transcripts returns proper structure."""
        mock_transcript = {
            "segments": [
                {
                    "start": 0.0,
                    "end": 5.0,
                    "text": "こんにちは世界！元気ですか？"
                }
            ]
        }
        
        with patch.object(segmenter, '_process_segments') as mock_process:
            mock_process.return_value = [{"text": "こんにちは世界！", "start": 0.0, "end": 2.5}]
            result = segmenter.segment_transcripts(mock_transcript)
            
            assert "segments" in result
            assert isinstance(result["segments"], list)
    
    def test_sentence_match_error_handling(self, segmenter):
        """Test that SentenceMatchError is properly raised and handled."""
        # This tests the exception we'll be moving to base.py
        error = SentenceMatchError("test", "original", "reason")
        assert isinstance(error, Exception)
        assert error.sentence == "test"
        assert error.original_text == "original"
        assert error.reason == "reason"
    
    def test_segmenter_similarities_with_german(self):
        """Test that Japanese and German segmenters have similar patterns (TODO #5)."""
        # This test documents the similarities that will be refactored
        from mitlesen.nlp.german.segmenter import GermanSentenceSegmenter
        
        # Both should have similar method signatures
        japanese_methods = [method for method in dir(JapaneseSentenceSegmenter) 
                          if not method.startswith('_') and callable(getattr(JapaneseSentenceSegmenter, method))]
        german_methods = [method for method in dir(GermanSentenceSegmenter) 
                        if not method.startswith('_') and callable(getattr(GermanSentenceSegmenter, method))]
        
        # Both should have segment_transcripts and split_long_sentence
        assert 'segment_transcripts' in japanese_methods
        assert 'segment_transcripts' in german_methods
        assert 'split_long_sentence' in japanese_methods
        assert 'split_long_sentence' in german_methods