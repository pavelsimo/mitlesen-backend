"""Tests for template method pattern refactoring in segmenters (TODO #5 - COMPLETED)."""
import pytest
from unittest.mock import Mock, patch
from mitlesen.nlp.base import BaseSegmenter, SentenceMatchError
from mitlesen.nlp.german.segmenter import GermanSentenceSegmenter
from mitlesen.nlp.japanese.segmenter import JapaneseSentenceSegmenter


class TestBaseSegmenterTemplateMethod:
    """Test the BaseSegmenter template method pattern implementation."""
    
    def test_template_method_defined(self):
        """Test that BaseSegmenter defines the template method."""
        assert hasattr(BaseSegmenter, 'segment_transcripts')
        assert callable(BaseSegmenter.segment_transcripts)
        
        # Should not be abstract anymore (it's the template method)
        assert not getattr(BaseSegmenter.segment_transcripts, '__isabstractmethod__', False)
    
    def test_abstract_hook_methods_defined(self):
        """Test that BaseSegmenter defines the required abstract hook methods."""
        required_hooks = [
            '_extract_text_from_words',
            '_align_words_to_sentence', 
            '_get_processing_log_prefix'
        ]
        
        for hook in required_hooks:
            assert hasattr(BaseSegmenter, hook)
            # Should be abstract
            assert getattr(getattr(BaseSegmenter, hook), '__isabstractmethod__', False)
    
    def test_common_helper_method_defined(self):
        """Test that BaseSegmenter defines common helper methods."""
        assert hasattr(BaseSegmenter, '_create_segment_from_words')
        assert callable(BaseSegmenter._create_segment_from_words)
        
        # Should not be abstract (it's common implementation)
        assert not getattr(BaseSegmenter._create_segment_from_words, '__isabstractmethod__', False)


class TestGermanSegmenterRefactored:
    """Test the refactored German segmenter."""
    
    def test_inherits_from_base_segmenter(self):
        """Test that German segmenter inherits from BaseSegmenter."""
        assert issubclass(GermanSentenceSegmenter, BaseSegmenter)
    
    def test_implements_hook_methods(self):
        """Test that German segmenter implements all required hook methods."""
        required_hooks = [
            '_extract_text_from_words',
            '_align_words_to_sentence',
            '_get_processing_log_prefix'
        ]
        
        for hook in required_hooks:
            assert hasattr(GermanSentenceSegmenter, hook)
            assert callable(getattr(GermanSentenceSegmenter, hook))
    
    def test_extract_text_from_words_german_behavior(self):
        """Test German-specific text extraction (space-separated)."""
        words = [
            {'text': 'Hello'},
            {'text': 'world'},
            {'text': '!'}
        ]
        
        # Create a minimal segmenter instance for testing
        segmenter = GermanSentenceSegmenter.__new__(GermanSentenceSegmenter)
        result = segmenter._extract_text_from_words(words)
        
        # German should join with spaces
        assert result == "Hello world !"
    
    def test_get_processing_log_prefix_german(self):
        """Test German-specific log prefix."""
        segmenter = GermanSentenceSegmenter.__new__(GermanSentenceSegmenter)
        prefix = segmenter._get_processing_log_prefix()
        
        assert prefix == "Processing "
        assert "German" not in prefix  # German doesn't specify language in prefix
    
    def test_uses_template_method_from_base(self):
        """Test that German segmenter uses template method from base class."""
        german_method = getattr(GermanSentenceSegmenter, 'segment_transcripts')
        base_method = getattr(BaseSegmenter, 'segment_transcripts')
        
        # Should be the same method (inherited from base)
        assert german_method is base_method


class TestJapaneseSegmenterRefactored:
    """Test the refactored Japanese segmenter."""
    
    def test_inherits_from_base_segmenter(self):
        """Test that Japanese segmenter inherits from BaseSegmenter."""
        assert issubclass(JapaneseSentenceSegmenter, BaseSegmenter)
    
    def test_implements_hook_methods(self):
        """Test that Japanese segmenter implements all required hook methods."""
        required_hooks = [
            '_extract_text_from_words',
            '_align_words_to_sentence',
            '_get_processing_log_prefix'
        ]
        
        for hook in required_hooks:
            assert hasattr(JapaneseSentenceSegmenter, hook)
            assert callable(getattr(JapaneseSentenceSegmenter, hook))
    
    def test_extract_text_from_words_japanese_behavior(self):
        """Test Japanese-specific text extraction (no spaces)."""
        words = [
            {'text': 'こんにちは'},
            {'text': '世界'},
            {'text': '！'}
        ]
        
        # Create a minimal segmenter instance for testing
        segmenter = JapaneseSentenceSegmenter.__new__(JapaneseSentenceSegmenter)
        result = segmenter._extract_text_from_words(words)
        
        # Japanese should join without spaces
        assert result == "こんにちは世界！"
    
    def test_get_processing_log_prefix_japanese(self):
        """Test Japanese-specific log prefix."""
        segmenter = JapaneseSentenceSegmenter.__new__(JapaneseSentenceSegmenter)
        prefix = segmenter._get_processing_log_prefix()
        
        assert prefix == "Processing Japanese "
        assert "Japanese" in prefix
    
    def test_uses_template_method_from_base(self):
        """Test that Japanese segmenter uses template method from base class."""
        japanese_method = getattr(JapaneseSentenceSegmenter, 'segment_transcripts')
        base_method = getattr(BaseSegmenter, 'segment_transcripts')
        
        # Should be the same method (inherited from base)
        assert japanese_method is base_method


class TestTemplateMethodBehaviorDifferences:
    """Test that language-specific behaviors work correctly through template method."""
    
    def test_text_extraction_differences(self):
        """Test that text extraction differs correctly between languages."""
        words = [
            {'text': 'Hello'},
            {'text': 'world'}
        ]
        
        # Create minimal instances
        german_seg = GermanSentenceSegmenter.__new__(GermanSentenceSegmenter)
        japanese_seg = JapaneseSentenceSegmenter.__new__(JapaneseSentenceSegmenter)
        
        german_text = german_seg._extract_text_from_words(words)
        japanese_text = japanese_seg._extract_text_from_words(words)
        
        # Should have different concatenation strategies
        assert german_text == "Hello world"  # With space
        assert japanese_text == "Helloworld"  # Without space
        assert german_text != japanese_text
    
    def test_log_prefix_differences(self):
        """Test that log prefixes differ correctly between languages."""
        german_seg = GermanSentenceSegmenter.__new__(GermanSentenceSegmenter)
        japanese_seg = JapaneseSentenceSegmenter.__new__(JapaneseSentenceSegmenter)
        
        german_prefix = german_seg._get_processing_log_prefix()
        japanese_prefix = japanese_seg._get_processing_log_prefix()
        
        # Should have different prefixes
        assert german_prefix != japanese_prefix
        assert "Japanese" in japanese_prefix
        assert "Japanese" not in german_prefix


class TestTemplateMethodPatternSuccess:
    """Test that the template method pattern refactoring was successful (TODO #5 - COMPLETED)."""
    
    def test_code_duplication_eliminated(self):
        """Test that code duplication has been eliminated."""
        import inspect
        
        # Check that neither segmenter class has a segment_transcripts implementation
        german_source = inspect.getsource(GermanSentenceSegmenter)
        japanese_source = inspect.getsource(JapaneseSentenceSegmenter)
        
        # Should not contain the old segment_transcripts method
        assert 'def segment_transcripts(' not in german_source
        assert 'def segment_transcripts(' not in japanese_source
        
        # But should have the hook methods
        assert 'def _extract_text_from_words(' in german_source
        assert 'def _extract_text_from_words(' in japanese_source
        assert 'def _align_words_to_sentence(' in german_source
        assert 'def _align_words_to_sentence(' in japanese_source
    
    def test_common_algorithm_extracted(self):
        """Test that the common algorithm has been extracted to base class."""
        import inspect
        
        base_source = inspect.getsource(BaseSegmenter.segment_transcripts)
        
        # Should contain the common algorithm steps
        assert 'new_segments = []' in base_source
        assert 'current_segment_id = 0' in base_source
        assert 'for segment in segments:' in base_source
        assert 'self._extract_text_from_words' in base_source
        assert 'self.segment_text' in base_source
        assert 'self._align_words_to_sentence' in base_source
        assert 'self._create_segment_from_words' in base_source
    
    def test_language_specific_operations_preserved(self):
        """Test that language-specific operations are preserved in hook methods."""
        import inspect
        
        # German should use normalization-based matching
        german_seg = GermanSentenceSegmenter.__new__(GermanSentenceSegmenter)
        german_align_source = inspect.getsource(german_seg._align_words_to_sentence)
        assert 'normalize_text' in german_align_source
        
        # Japanese should use character-by-character matching
        japanese_seg = JapaneseSentenceSegmenter.__new__(JapaneseSentenceSegmenter)
        japanese_align_source = inspect.getsource(japanese_seg._align_words_to_sentence)
        assert 'sentence_chars = list(sentence)' in japanese_align_source
        assert 'word_chars = list(word["text"])' in japanese_align_source
    
    def test_hook_methods_properly_implemented(self):
        """Test that hook methods are properly implemented in both classes."""
        models = [GermanSentenceSegmenter, JapaneseSentenceSegmenter]
        required_hooks = [
            '_extract_text_from_words',
            '_align_words_to_sentence',
            '_get_processing_log_prefix'
        ]
        
        for model in models:
            for hook in required_hooks:
                # Should have the method
                assert hasattr(model, hook)
                
                # Should be callable
                method = getattr(model, hook)
                assert callable(method)
                
                # Should not be abstract (concrete implementation)
                assert not getattr(method, '__isabstractmethod__', False)
    
    def test_template_method_pattern_structure(self):
        """Test that the template method pattern structure is correct."""
        # Template method should be in base class and not abstract
        template_method = getattr(BaseSegmenter, 'segment_transcripts')
        assert not getattr(template_method, '__isabstractmethod__', False)
        
        # Hook methods should be abstract in base class
        hook_methods = [
            '_extract_text_from_words',
            '_align_words_to_sentence',
            '_get_processing_log_prefix'
        ]
        
        for hook in hook_methods:
            base_method = getattr(BaseSegmenter, hook)
            assert getattr(base_method, '__isabstractmethod__', False)
    
    def test_error_handling_preserved(self):
        """Test that error handling is preserved in the template method."""
        import inspect
        
        template_source = inspect.getsource(BaseSegmenter.segment_transcripts)
        
        # Should have proper error handling
        assert 'try:' in template_source
        assert 'except SentenceMatchError' in template_source
        assert 'logger.error' in template_source
        assert 'continue' in template_source  # Continue processing other sentences
    
    def test_segment_creation_unified(self):
        """Test that segment creation logic is unified."""
        import inspect
        
        # Should have common segment creation method
        create_method = getattr(BaseSegmenter, '_create_segment_from_words')
        assert callable(create_method)
        
        create_source = inspect.getsource(create_method)
        
        # Should create proper segment structure
        assert 'start_time = words[0].get("start", 0.0)' in create_source
        assert 'end_time = words[-1].get("end", 0.0)' in create_source
        assert '"id": segment_id' in create_source
        assert '"words": words' in create_source