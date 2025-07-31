"""Integration tests for Spanish NLP components."""

import pytest
from unittest.mock import Mock, patch
from mitlesen.nlp import get_segmenter, get_transcript_processor
from mitlesen.nlp.spanish.segmenter import SpanishSentenceSegmenter
from mitlesen.nlp.spanish.transcript_processor import SpanishTranscriptProcessor
from mitlesen.prompts import get_system_instruction, aug_transcript_prompt


class TestSpanishIntegration:
    """Test Spanish language integration across the system."""
    
    def test_get_segmenter_spanish(self):
        """Test that Spanish segmenter is correctly instantiated."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy.return_value = mock_nlp
            
            segmenter = get_segmenter('es')
            
            assert isinstance(segmenter, SpanishSentenceSegmenter)
            mock_spacy.assert_called_once_with("es_core_news_sm")
    
    def test_get_segmenter_spanish_case_insensitive(self):
        """Test Spanish segmenter with different case."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy.return_value = mock_nlp
            
            segmenter = get_segmenter('ES')
            
            assert isinstance(segmenter, SpanishSentenceSegmenter)
    
    def test_get_transcript_processor_spanish(self):
        """Test that Spanish transcript processor is correctly instantiated."""
        processor = get_transcript_processor('es')
        
        assert isinstance(processor, SpanishTranscriptProcessor)
    
    def test_get_transcript_processor_spanish_case_insensitive(self):
        """Test Spanish transcript processor with different case."""
        processor = get_transcript_processor('ES')
        
        assert isinstance(processor, SpanishTranscriptProcessor)
    
    def test_unsupported_language_segmenter(self):
        """Test that unsupported language raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_segmenter('fr')  # French not supported
        
        assert "Unsupported language for segmentation: fr" in str(exc_info.value)
    
    def test_unsupported_language_transcript_processor(self):
        """Test that unsupported language raises ValueError."""
        with pytest.raises(ValueError) as exc_info:
            get_transcript_processor('fr')  # French not supported
        
        assert "Unsupported language for transcript processing: fr" in str(exc_info.value)
    
    def test_spanish_system_prompts_integration(self):
        """Test Spanish system prompt integration."""
        system_prompt = get_system_instruction('es')
        
        assert system_prompt is not None
        assert isinstance(system_prompt, str)
        assert "Spanish" in system_prompt
    
    def test_spanish_transcript_prompts_integration(self):
        """Test Spanish transcript prompt integration."""
        sample_json = '[{"text": "Hola mundo", "words": [{"text": "Hola"}, {"text": "mundo"}]}]'
        
        prompt = aug_transcript_prompt(sample_json, language='es')
        
        assert prompt is not None
        assert isinstance(prompt, str)
        assert "Spanish" in prompt
        assert sample_json in prompt
    
    def test_spanish_end_to_end_pipeline_simulation(self):
        """Test end-to-end Spanish processing simulation."""
        # Simulate a Spanish transcript segment
        transcript_segment = [
            {
                "id": 0,
                "start": 0.0,
                "end": 2.0,
                "text": "¿Cómo estás?",
                "words": [
                    {"text": "¿Cómo", "start": 0.0, "end": 0.5},
                    {"text": "estás?", "start": 0.6, "end": 1.0}
                ]
            }
        ]
        
        # Test segmenter
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy.return_value = mock_nlp
            
            segmenter = get_segmenter('es')
            assert isinstance(segmenter, SpanishSentenceSegmenter)
        
        # Test transcript processor
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            mock_dict.search_by_lemma.return_value = []
            
            processor = get_transcript_processor('es')
            result = processor.preprocess_transcript(transcript_segment)
            
            assert result == transcript_segment
            mock_dict.close.assert_called_once()
    
    def test_spanish_prompts_contain_linguistic_features(self):
        """Test that Spanish prompts include Spanish linguistic features."""
        sample_json = '[{"text": "La niña", "words": [{"text": "La"}, {"text": "niña"}]}]'
        
        prompt = aug_transcript_prompt(sample_json, language='es')
        
        # Check for Spanish grammatical features
        assert "gender" in prompt.lower()
        assert "masculino" in prompt
        assert "femenino" in prompt
        assert "tú" in prompt or "usted" in prompt
        assert "spanish" in prompt.lower()
    
    def test_spanish_components_compatibility(self):
        """Test compatibility between Spanish components."""
        # Test that normalizer works with segmenter expectations
        from mitlesen.nlp.spanish.normalizer import normalize_spanish_text
        
        spanish_text = "¡Hola, María! ¿Cómo estás hoy?"
        normalized = normalize_spanish_text(spanish_text)
        
        assert normalized == "hola maría cómo estás hoy"
        assert "¡" not in normalized
        assert "¿" not in normalized
        assert "!" not in normalized
        assert "?" not in normalized
        assert "," not in normalized
        
        # Spanish accents should be preserved
        assert "í" in normalized
        assert "ó" in normalized
        assert "á" in normalized
    
    def test_spanish_factory_functions_consistency(self):
        """Test that factory functions are consistent across calls."""
        with patch('spacy.load') as mock_spacy:
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            mock_spacy.return_value = mock_nlp
            
            segmenter1 = get_segmenter('es')
            segmenter2 = get_segmenter('ES')
            
            assert type(segmenter1) == type(segmenter2)
        
        processor1 = get_transcript_processor('es')
        processor2 = get_transcript_processor('ES')
        
        assert type(processor1) == type(processor2)
    
    def test_spanish_supported_languages_list(self):
        """Test that Spanish is in the supported languages."""
        # Test that we don't get errors for Spanish
        supported_operations = []
        
        try:
            get_segmenter('es')
            supported_operations.append('segmenter')
        except ValueError:
            pass
        
        try:
            get_transcript_processor('es')
            supported_operations.append('transcript_processor')
        except ValueError:
            pass
        
        try:
            get_system_instruction('es')
            supported_operations.append('system_prompt')
        except ValueError:
            pass
        
        try:
            aug_transcript_prompt('[]', 'es')
            supported_operations.append('transcript_prompt')
        except ValueError:
            pass
        
        # All operations should be supported for Spanish
        expected_operations = ['segmenter', 'transcript_processor', 'system_prompt', 'transcript_prompt']
        
        # Account for mocking in segmenter test
        with patch('spacy.load'):
            mock_nlp = Mock()
            mock_nlp.pipe_names = []
            
            for op in expected_operations:
                if op == 'segmenter':
                    with patch('spacy.load', return_value=mock_nlp):
                        get_segmenter('es')
                elif op == 'transcript_processor':
                    get_transcript_processor('es')
                elif op == 'system_prompt':
                    get_system_instruction('es')
                elif op == 'transcript_prompt':
                    aug_transcript_prompt('[]', 'es')
        
        assert len(supported_operations) == len(expected_operations)