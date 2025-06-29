"""Tests for NLP base classes and exceptions."""
import pytest
from unittest.mock import Mock
from mitlesen.nlp.base import BaseTokenizer, BaseSegmenter, BaseWordSplitter


class TestBaseTokenizer:
    """Test BaseTokenizer abstract class."""
    
    def test_tokenize_not_implemented(self):
        """Test that BaseTokenizer.tokenize raises NotImplementedError."""
        with pytest.raises(TypeError):
            BaseTokenizer()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        class ConcreteTokenizer(BaseTokenizer):
            def tokenize(self, text: str):
                return text.split()
        
        tokenizer = ConcreteTokenizer()
        result = tokenizer.tokenize("hello world")
        assert result == ["hello", "world"]


class TestBaseSegmenter:
    """Test BaseSegmenter abstract class."""
    
    def test_segment_transcripts_not_implemented(self):
        """Test that BaseSegmenter.segment_transcripts raises NotImplementedError."""
        with pytest.raises(TypeError):
            BaseSegmenter()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        class ConcreteSegmenter(BaseSegmenter):
            def segment_transcripts(self, transcript_data):
                return {"segments": []}
        
        segmenter = ConcreteSegmenter()
        result = segmenter.segment_transcripts({})
        assert result == {"segments": []}


class TestBaseWordSplitter:
    """Test BaseWordSplitter abstract class."""
    
    def test_split_compound_word_not_implemented(self):
        """Test that BaseWordSplitter.split_compound_word raises NotImplementedError."""
        with pytest.raises(TypeError):
            BaseWordSplitter()
    
    def test_concrete_implementation(self):
        """Test that concrete implementation works."""
        class ConcreteWordSplitter(BaseWordSplitter):
            def split_compound_word(self, word: str):
                return [word]
        
        splitter = ConcreteWordSplitter()
        result = splitter.split_compound_word("test")
        assert result == ["test"]