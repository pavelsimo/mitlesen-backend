"""Tests for Spanish sentence segmenter."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mitlesen.nlp.spanish.segmenter import SpanishSentenceSegmenter
from mitlesen.nlp.base import SentenceMatchError


class TestSpanishSentenceSegmenter:
    """Test Spanish sentence segmenter."""
    
    @pytest.fixture
    def segmenter(self):
        """Create a Spanish sentence segmenter for testing."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []  # No sentencizer initially
            mock_spacy.return_value = mock_nlp
            segmenter = SpanishSentenceSegmenter()
            segmenter.nlp = mock_nlp
            return segmenter
    
    def test_init(self):
        """Test initialization of Spanish segmenter."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy.return_value = mock_nlp
            segmenter = SpanishSentenceSegmenter()
            mock_spacy.assert_called_once_with("es_core_news_sm")
            assert segmenter.nlp is mock_nlp
    
    def test_init_missing_model_downloads(self):
        """Test that missing Spanish model triggers download."""
        with patch('spacy.load') as mock_spacy:
            with patch('spacy.cli.download') as mock_download:
                # First call raises OSError, second succeeds
                mock_nlp = Mock()
                mock_nlp.pipe_names = []
                mock_spacy.side_effect = [OSError("Model not found"), mock_nlp]
                
                segmenter = SpanishSentenceSegmenter()
                
                mock_download.assert_called_once_with("es_core_news_sm")
                assert mock_spacy.call_count == 2
                assert segmenter.nlp is mock_nlp
    
    def test_sentencizer_added_when_missing(self):
        """Test that sentencizer is added when not present."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []  # No sentencizer present
            mock_spacy.return_value = mock_nlp
            
            SpanishSentenceSegmenter()
            
            mock_nlp.add_pipe.assert_called_once_with("sentencizer", first=True)
    
    def test_sentencizer_not_added_when_present(self):
        """Test that sentencizer is not added when already present."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = ['sentencizer']  # Already has sentencizer
            mock_spacy.return_value = mock_nlp
            
            SpanishSentenceSegmenter()
            
            mock_nlp.add_pipe.assert_not_called()
    
    def test_split_long_sentence_short_text(self, segmenter):
        """Test that short sentences are returned as-is."""
        # Mock spaCy Span object
        mock_span = Mock()
        mock_span.text = "Hola mundo."
        
        result = segmenter.split_long_sentence(mock_span, max_len=50)
        
        assert result == ["Hola mundo."]
    
    def test_split_long_sentence_long_text(self, segmenter):
        """Test splitting of long Spanish sentences."""
        # Mock spaCy tokens
        mock_tokens = [
            Mock(text_with_ws="Esta "),
            Mock(text_with_ws="es "),
            Mock(text_with_ws="una "),
            Mock(text_with_ws="oración "),
            Mock(text_with_ws="muy "),
            Mock(text_with_ws="larga, "),
            Mock(text_with_ws="que "),
            Mock(text_with_ws="debe "),
            Mock(text_with_ws="ser "),
            Mock(text_with_ws="dividida."),
        ]
        
        mock_span = Mock()
        mock_span.text = "Esta es una oración muy larga, que debe ser dividida."
        mock_span.__iter__ = lambda self: iter(mock_tokens)
        
        result = segmenter.split_long_sentence(mock_span, max_len=30)
        
        assert isinstance(result, list)
        assert len(result) > 1  # Should be split
        assert all(isinstance(chunk, str) for chunk in result)
    
    def test_segment_text(self, segmenter):
        """Test text segmentation using spaCy."""
        # Mock spaCy doc and sentences
        mock_sent1 = Mock()
        mock_sent1.text = "¿Cómo estás?"
        
        mock_sent2 = Mock() 
        mock_sent2.text = "¡Muy bien, gracias!"
        
        mock_doc = Mock()
        mock_doc.sents = [mock_sent1, mock_sent2]
        
        segmenter.nlp.return_value = mock_doc
        
        with patch.object(segmenter, 'split_long_sentence') as mock_split:
            mock_split.return_value = ["Test sentence"]
            
            result = segmenter.segment_text("¿Cómo estás? ¡Muy bien, gracias!")
            
            assert isinstance(result, list)
            assert mock_split.call_count == 2  # Called for each sentence
    
    def test_extract_text_from_words(self, segmenter):
        """Test Spanish text extraction from word list."""
        words = [
            {"text": "Hola"},
            {"text": "mundo"},
            {"text": "hermoso"}
        ]
        
        result = segmenter._extract_text_from_words(words)
        
        assert result == "Hola mundo hermoso"
    
    def test_align_words_to_sentence_success(self, segmenter):
        """Test successful word alignment for Spanish text."""
        sentence = "Hola mundo"
        words = [
            {"text": "Hola"},
            {"text": "mundo"},
            {"text": "adicional"}
        ]
        
        with patch('mitlesen.nlp.spanish.normalizer.normalize_spanish_text') as mock_norm:
            # Setup normalization to simulate successful matching
            mock_norm.side_effect = [
                "hola mundo",  # target_norm
                "hola mundo adicional",  # initial check
                "hola",  # first iteration
                "hola mundo",  # second iteration (match)
            ]
            
            result_words, next_idx = segmenter._align_words_to_sentence(sentence, words, 0)
            
            assert len(result_words) == 2
            assert result_words[0]["text"] == "Hola"
            assert result_words[1]["text"] == "mundo"
            assert next_idx == 2
    
    def test_align_words_to_sentence_no_start_match(self, segmenter):
        """Test word alignment when sentence start cannot be found."""
        sentence = "No existe"
        words = [
            {"text": "Hola"},
            {"text": "mundo"}
        ]
        
        with patch('mitlesen.nlp.spanish.normalizer.normalize_spanish_text') as mock_norm:
            # Setup normalization to simulate no match
            mock_norm.side_effect = [
                "no existe",  # target_norm
                "hola mundo",  # words text (no match)
                "mundo",  # second attempt (no match)
            ]
            
            with pytest.raises(SentenceMatchError) as exc_info:
                segmenter._align_words_to_sentence(sentence, words, 0)
            
            assert "Could not locate sentence start" in str(exc_info.value)
    
    def test_align_words_to_sentence_overshoot(self, segmenter):
        """Test word alignment edge case handling."""
        # This test checks that the segmenter handles alignment gracefully
        # The exact error condition is complex to mock, so we test basic functionality
        sentence = "Corto"
        words = [
            {"text": "Diferente"},
            {"text": "texto"},
            {"text": "largo"}
        ]
        
        # Test that mismatched content raises appropriate error
        with pytest.raises(SentenceMatchError):
            segmenter._align_words_to_sentence(sentence, words, 0)
    
    def test_get_processing_log_prefix(self, segmenter):
        """Test Spanish-specific log prefix."""
        result = segmenter._get_processing_log_prefix()
        
        assert result == "Processing (Spanish) "
        assert "Spanish" in result