"""Tests for Spanish transcript processor."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from mitlesen.nlp.spanish.transcript_processor import SpanishTranscriptProcessor


class TestSpanishTranscriptProcessor:
    """Test Spanish transcript processor."""
    
    @pytest.fixture
    def processor(self):
        """Create a Spanish transcript processor for testing."""
        return SpanishTranscriptProcessor()
    
    def test_preprocess_transcript_basic(self, processor):
        """Test basic transcript preprocessing."""
        transcript = [
            {
                "id": 0,
                "text": "Hola mundo",
                "words": [
                    {"text": "Hola", "start": 0.0, "end": 0.5},
                    {"text": "mundo", "start": 0.6, "end": 1.0}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            mock_dict.search_by_lemma.return_value = []
            
            result = processor.preprocess_transcript(transcript)
            
            assert result == transcript
            mock_dict.close.assert_called_once()
    
    def test_preprocess_transcript_with_spanish_characters(self, processor):
        """Test preprocessing with Spanish-specific characters."""
        transcript = [
            {
                "id": 0,
                "text": "¡Hola niño! ¿Cómo estás?",
                "words": [
                    {"text": "¡Hola!", "start": 0.0, "end": 0.5},
                    {"text": "niño", "start": 0.6, "end": 1.0},
                    {"text": "¿Cómo?", "start": 1.1, "end": 1.5},
                    {"text": "estás", "start": 1.6, "end": 2.0}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            mock_dict.search_by_lemma.return_value = []
            
            result = processor.preprocess_transcript(transcript)
            
            # Check that Spanish characters are preserved in processing
            assert result == transcript
            
            # Verify dictionary lookups were attempted with cleaned text
            expected_calls = [
                (("hola",), {'lang': 'es'}),
                (("niño",), {'lang': 'es'}),
                (("cómo",), {'lang': 'es'}),
                (("estás",), {'lang': 'es'}),
            ]
            
            # Check that search_by_lemma was called for each word
            assert mock_dict.search_by_lemma.call_count == 8  # 4 words × 2 calls each (es + fallback)
    
    def test_preprocess_transcript_dictionary_lookup_success(self, processor):
        """Test successful dictionary lookup."""
        transcript = [
            {
                "id": 0,
                "text": "Casa blanca",
                "words": [
                    {"text": "Casa", "start": 0.0, "end": 0.5, "pos": "noun"},
                    {"text": "blanca", "start": 0.6, "end": 1.0, "pos": "adjective"}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            
            # Mock successful Spanish dictionary lookup
            mock_dict.search_by_lemma.side_effect = [
                [{"id": 123, "lemma": "casa", "pos": "noun"}],  # Spanish lookup for "casa"
                [],  # Fallback lookup for "casa"
                [{"id": 456, "lemma": "blanco", "pos": "adjective"}],  # Spanish lookup for "blanca"
                [],  # Fallback lookup for "blanca"
            ]
            
            result = processor.preprocess_transcript(transcript)
            
            # Check that dictionary IDs were added
            assert result[0]["words"][0]["id"] == 123
            assert result[0]["words"][1]["id"] == 456
            
            # Verify Spanish-first lookup pattern
            mock_dict.search_by_lemma.assert_any_call("casa", lang='es')
            mock_dict.search_by_lemma.assert_any_call("blanca", lang='es')
    
    def test_preprocess_transcript_dictionary_pos_matching(self, processor):
        """Test POS tag matching in dictionary lookup."""
        transcript = [
            {
                "id": 0,
                "text": "Verde",
                "words": [
                    {"text": "Verde", "start": 0.0, "end": 0.5, "pos": "adjective"}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            
            # Mock dictionary with multiple entries, one matching POS
            mock_dict.search_by_lemma.side_effect = [
                [
                    {"id": 100, "lemma": "verde", "pos": "noun"},
                    {"id": 200, "lemma": "verde", "pos": "adjective"},
                    {"id": 300, "lemma": "verde", "pos": "verb"}
                ],
                []  # Fallback lookup
            ]
            
            result = processor.preprocess_transcript(transcript)
            
            # Should pick the entry with matching POS tag
            assert result[0]["words"][0]["id"] == 200
    
    def test_preprocess_transcript_dictionary_fallback_no_pos_match(self, processor):
        """Test fallback to first entry when no POS match found."""
        transcript = [
            {
                "id": 0,
                "text": "Palabra",
                "words": [
                    {"text": "Palabra", "start": 0.0, "end": 0.5, "pos": "noun"}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            
            # Mock dictionary with entries, none matching POS
            mock_dict.search_by_lemma.side_effect = [
                [
                    {"id": 400, "lemma": "palabra", "pos": "verb"},
                    {"id": 500, "lemma": "palabra", "pos": "adjective"}
                ],
                []  # Fallback lookup
            ]
            
            result = processor.preprocess_transcript(transcript)
            
            # Should pick the first entry as fallback
            assert result[0]["words"][0]["id"] == 400
    
    def test_preprocess_transcript_dictionary_spanish_fallback(self, processor):
        """Test fallback to general lookup when Spanish lookup fails."""
        transcript = [
            {
                "id": 0,
                "text": "Test",
                "words": [
                    {"text": "Test", "start": 0.0, "end": 0.5}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            
            # Spanish lookup fails, general lookup succeeds
            mock_dict.search_by_lemma.side_effect = [
                [],  # Spanish lookup fails
                [{"id": 600, "lemma": "test"}]  # General lookup succeeds
            ]
            
            result = processor.preprocess_transcript(transcript)
            
            # Should use result from general lookup
            assert result[0]["words"][0]["id"] == 600
            
            # Verify both lookups were attempted
            mock_dict.search_by_lemma.assert_any_call("test", lang='es')
            mock_dict.search_by_lemma.assert_any_call("test")
    
    def test_preprocess_transcript_empty_segments(self, processor):
        """Test handling of empty segments."""
        transcript = [
            {
                "id": 0,
                "text": "",
                # No 'words' key
            },
            {
                "id": 1,
                "text": "Test",
                "words": []  # Empty words list
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            
            result = processor.preprocess_transcript(transcript)
            
            # Should return unchanged
            assert result == transcript
            # Dictionary should not be queried
            mock_dict.search_by_lemma.assert_not_called()
    
    def test_preprocess_transcript_dictionary_error_handling(self, processor):
        """Test error handling when dictionary operations fail."""
        transcript = [
            {
                "id": 0,
                "text": "Prueba",
                "words": [
                    {"text": "Prueba", "start": 0.0, "end": 0.5}
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            with patch('mitlesen.logger.logger') as mock_logger:
                mock_dict = Mock()
                mock_dict_class.side_effect = Exception("Database error")
                
                # Should not raise exception, just log warning
                result = processor.preprocess_transcript(transcript)
                
                assert result == transcript
                mock_logger.warning.assert_called_once()
                assert "Spanish dictionary lookup failed" in mock_logger.warning.call_args[0][0]
    
    def test_preprocess_transcript_base_form_priority(self, processor):
        """Test that base_form is preferred over text for dictionary lookup."""
        transcript = [
            {
                "id": 0,
                "text": "Corriendo",
                "words": [
                    {
                        "text": "corriendo",
                        "base_form": "correr",
                        "start": 0.0,
                        "end": 1.0
                    }
                ]
            }
        ]
        
        with patch('mitlesen.nlp.spanish.transcript_processor.SqliteDictionary') as mock_dict_class:
            mock_dict = Mock()
            mock_dict_class.return_value = mock_dict
            mock_dict.search_by_lemma.return_value = [{"id": 700, "lemma": "correr"}]
            
            result = processor.preprocess_transcript(transcript)
            
            # Should look up using base_form ("correr") not text ("corriendo")
            mock_dict.search_by_lemma.assert_any_call("correr", lang='es')
            assert result[0]["words"][0]["id"] == 700