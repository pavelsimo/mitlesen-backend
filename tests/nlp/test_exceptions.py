"""Tests for SentenceMatchError now unified in base.py (TODO #1 - COMPLETED)."""
import pytest


class TestSentenceMatchError:
    """Test SentenceMatchError now unified in base.py."""
    
    def test_base_sentence_match_error(self):
        """Test SentenceMatchError from base.py."""
        from mitlesen.nlp.base import SentenceMatchError
        
        error = SentenceMatchError("test sentence", "original text", "test reason")
        assert error.sentence == "test sentence"
        assert error.original_text == "original text"
        assert error.reason == "test reason"
        assert "test sentence" in str(error)
        assert "original text" in str(error)
        assert "test reason" in str(error)
    
    def test_german_segmenter_imports_from_base(self):
        """Test that German segmenter imports SentenceMatchError from base."""
        from mitlesen.nlp.german.segmenter import SentenceMatchError
        from mitlesen.nlp.base import SentenceMatchError as BaseSentenceMatchError
        
        # Should be the same class
        assert SentenceMatchError is BaseSentenceMatchError
    
    def test_japanese_segmenter_imports_from_base(self):
        """Test that Japanese segmenter imports SentenceMatchError from base."""
        from mitlesen.nlp.japanese.segmenter import SentenceMatchError
        from mitlesen.nlp.base import SentenceMatchError as BaseSentenceMatchError
        
        # Should be the same class
        assert SentenceMatchError is BaseSentenceMatchError
    
    def test_both_segmenters_use_same_exception(self):
        """Test that both segmenters now use the same exception class."""
        from mitlesen.nlp.german.segmenter import SentenceMatchError as GermanError
        from mitlesen.nlp.japanese.segmenter import SentenceMatchError as JapaneseError
        
        # Should be the exact same class (not just functionally identical)
        assert GermanError is JapaneseError
        
        # Create instances to verify functionality
        german_error = GermanError("test", "text", "reason")
        japanese_error = JapaneseError("test", "text", "reason")
        
        # Should have identical attributes and behavior
        assert german_error.sentence == japanese_error.sentence
        assert german_error.original_text == japanese_error.original_text
        assert german_error.reason == japanese_error.reason
        assert str(german_error) == str(japanese_error)
    
    def test_no_duplicate_exception_classes(self):
        """Test that there are no duplicate SentenceMatchError classes."""
        # Import all modules that might have the exception
        import mitlesen.nlp.base
        import mitlesen.nlp.german.segmenter
        import mitlesen.nlp.japanese.segmenter
        
        base_error = mitlesen.nlp.base.SentenceMatchError
        german_error = mitlesen.nlp.german.segmenter.SentenceMatchError
        japanese_error = mitlesen.nlp.japanese.segmenter.SentenceMatchError
        
        # All should be the same class
        assert base_error is german_error
        assert base_error is japanese_error
        assert german_error is japanese_error