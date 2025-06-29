"""Tests for German segmenter (TODO #5 - Large Segmenter Classes)."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from mitlesen.nlp.german.segmenter import GermanSentenceSegmenter, SentenceMatchError


class TestGermanSentenceSegmenter:
    """Test German sentence segmenter."""
    
    @pytest.fixture
    def segmenter(self):
        """Create a German sentence segmenter for testing."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_spacy.return_value = mock_nlp
            segmenter = GermanSentenceSegmenter()
            segmenter.nlp = mock_nlp
            return segmenter
    
    def test_init(self):
        """Test initialization of German segmenter."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_spacy.return_value = mock_nlp
            segmenter = GermanSentenceSegmenter()
            mock_spacy.assert_called_once_with("de_core_news_sm")
            assert segmenter.nlp is mock_nlp
    
    def test_split_long_sentence_basic(self, segmenter):
        """Test basic sentence splitting functionality."""
        long_sentence = "Das ist ein sehr langer Satz. Er sollte aufgeteilt werden."
        result = segmenter.split_long_sentence(long_sentence, max_length=30)
        
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
                    "text": "Hallo Welt! Wie geht es dir?"
                }
            ]
        }
        
        with patch.object(segmenter, '_process_segments') as mock_process:
            mock_process.return_value = [{"text": "Hallo Welt!", "start": 0.0, "end": 2.5}]
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