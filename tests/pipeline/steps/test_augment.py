"""Tests for refactored AugmentStep (TODO #3 - COMPLETED)."""
import pytest
from unittest.mock import Mock, patch, mock_open
import json
from pathlib import Path
from mitlesen.pipeline.steps.augment import AugmentStep, BatchConfig, get_retry_delay
from mitlesen.pipeline.base import PipelineContext


class TestAugmentStepRefactored:
    """Test the refactored AugmentStep with simplified batch processing."""
    
    @pytest.fixture
    def mock_context(self):
        """Create a mock pipeline context."""
        context = Mock(spec=PipelineContext)
        context.youtube_id = "test_video_id"
        context.language = "en"
        context.transcript_path = Path("/fake/path/transcript.json")
        context.augmented_transcript_path = Path("/fake/path/transcript.json.2")
        return context
    
    @pytest.fixture
    def augment_step(self):
        """Create an AugmentStep instance."""
        return AugmentStep("test_augment", BatchConfig(max_words_per_translation_batch=10))
    
    @pytest.fixture
    def sample_transcript(self):
        """Sample transcript for testing."""
        return [
            {"text": "Hello world", "words": [{"word": "Hello"}, {"word": "world"}]},
            {"text": "This is a test", "words": [{"word": "This"}, {"word": "is"}, {"word": "a"}, {"word": "test"}]},
            {"text": "Another sentence", "words": [{"word": "Another"}, {"word": "sentence"}]}
        ]
    
    def test_load_and_preprocess_transcript(self, augment_step, mock_context, sample_transcript):
        """Test the _load_and_preprocess_transcript method with factory pattern."""
        mock_file_content = json.dumps(sample_transcript)
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('mitlesen.pipeline.steps.augment.get_transcript_processor') as mock_get_processor:
                mock_processor = Mock()
                mock_processor.preprocess_transcript.return_value = sample_transcript
                mock_get_processor.return_value = mock_processor
                mock_context.language = 'de'
                
                result = augment_step._load_and_preprocess_transcript(mock_context)
                
                assert result == sample_transcript
                mock_get_processor.assert_called_once_with('de')
                mock_processor.preprocess_transcript.assert_called_once_with(sample_transcript)
    
    def test_load_and_preprocess_transcript_unsupported_language(self, augment_step, mock_context, sample_transcript):
        """Test the _load_and_preprocess_transcript method with unsupported language."""
        mock_file_content = json.dumps(sample_transcript)
        
        with patch('builtins.open', mock_open(read_data=mock_file_content)):
            with patch('mitlesen.pipeline.steps.augment.get_transcript_processor') as mock_get_processor:
                mock_get_processor.side_effect = ValueError("Unsupported language")
                mock_context.language = 'en'  # Unsupported language
                
                result = augment_step._load_and_preprocess_transcript(mock_context)
                
                # Should return original transcript without preprocessing
                assert result == sample_transcript
                mock_get_processor.assert_called_once_with('en')
    
    def test_create_batches(self, augment_step, sample_transcript):
        """Test the _create_batches method."""
        batches = augment_step._create_batches(sample_transcript)
        
        assert len(batches) >= 1
        assert isinstance(batches, list)
        
        # Check batch structure
        for batch in batches:
            assert 'sentences' in batch
            assert 'start_idx' in batch
            assert 'end_idx' in batch
            assert 'word_count' in batch
            assert isinstance(batch['sentences'], list)
            assert isinstance(batch['start_idx'], int)
            assert isinstance(batch['end_idx'], int)
            assert isinstance(batch['word_count'], int)
    
    def test_create_single_batch(self, augment_step, sample_transcript):
        """Test the _create_single_batch method."""
        batch = augment_step._create_single_batch(sample_transcript, 0, len(sample_transcript))
        
        assert batch['start_idx'] == 0
        assert batch['end_idx'] >= 0
        assert batch['word_count'] > 0
        assert len(batch['sentences']) > 0
        assert batch['word_count'] <= augment_step.batch_config.max_words_per_translation_batch
    
    def test_create_single_batch_respects_word_limit(self, augment_step):
        """Test that batch creation respects word count limits."""
        # Create transcript with many words to test batching
        large_transcript = []
        for i in range(20):
            sentence = {
                "text": f"Sentence {i}",
                "words": [{"word": f"word{j}"} for j in range(5)]  # 5 words per sentence
            }
            large_transcript.append(sentence)
        
        batch = augment_step._create_single_batch(large_transcript, 0, len(large_transcript))
        
        # Should not exceed the word limit
        assert batch['word_count'] <= augment_step.batch_config.max_words_per_translation_batch
        assert len(batch['sentences']) <= augment_step.batch_config.max_words_per_translation_batch
    
    def test_process_batch_with_retry_success(self, augment_step):
        """Test successful batch processing."""
        batch = {
            'sentences': [{"text": "test", "words": [{"word": "test"}]}],
            'start_idx': 0,
            'end_idx': 0,
            'word_count': 1
        }
        transcript = [{"text": "test", "words": [{"word": "test"}]}]
        
        mock_client = Mock()
        mock_client.complete.return_value = '{"root": [{"translation": "test translation", "words": [{"word": "test"}]}]}'
        
        with patch('mitlesen.schema.Transcript') as mock_transcript:
            mock_sentence = Mock()
            mock_sentence.translation = "test translation"
            mock_sentence.words = [Mock()]
            mock_sentence.words[0].model_dump.return_value = {"word": "test"}
            
            mock_transcript.model_validate_json.return_value.root = [mock_sentence]
            
            result = augment_step._process_batch_with_retry(batch, transcript, mock_client, "en", 1)
            
            assert result is True
            mock_client.complete.assert_called_once()
    
    def test_process_batch_with_retry_failure(self, augment_step):
        """Test batch processing with retries and eventual failure."""
        batch = {
            'sentences': [{"text": "test", "words": [{"word": "test"}]}],
            'start_idx': 0,
            'end_idx': 0,
            'word_count': 1
        }
        transcript = [{"text": "test", "words": [{"word": "test"}]}]
        
        mock_client = Mock()
        mock_client.complete.side_effect = Exception("API Error")
        
        # Use a config with fewer retries for faster testing
        augment_step.batch_config.max_api_retries = 2
        
        with patch('time.sleep'):  # Speed up test by mocking sleep
            result = augment_step._process_batch_with_retry(batch, transcript, mock_client, "en", 1)
            
            assert result is False
            assert mock_client.complete.call_count == 3  # Original attempt + 2 retries
    
    def test_apply_batch_results(self, augment_step):
        """Test applying batch results to transcript."""
        batch = {
            'start_idx': 0,
            'end_idx': 1,
            'word_count': 3
        }
        
        transcript = [
            {"text": "hello", "words": [{"word": "hello"}]},
            {"text": "world", "words": [{"word": "world"}]}
        ]
        
        mock_sentence1 = Mock()
        mock_sentence1.translation = "hola"
        mock_sentence1.words = [Mock()]
        mock_sentence1.words[0].model_dump.return_value = {"meaning": "greeting"}
        
        mock_sentence2 = Mock()
        mock_sentence2.translation = "mundo"
        mock_sentence2.words = [Mock()]
        mock_sentence2.words[0].model_dump.return_value = {"meaning": "earth"}
        
        processed_batch = [mock_sentence1, mock_sentence2]
        
        augment_step._apply_batch_results(batch, processed_batch, transcript)
        
        # Check that translations were applied
        assert transcript[0]["translation"] == "hola"
        assert transcript[1]["translation"] == "mundo"
        
        # Check that word annotations were merged
        assert transcript[0]["words"][0]["meaning"] == "greeting"
        assert transcript[1]["words"][0]["meaning"] == "earth"
    
    def test_save_augmented_transcript(self, augment_step):
        """Test saving augmented transcript."""
        transcript = [{"text": "test", "words": [{"word": "test"}]}]
        output_path = Path("/fake/path/output.json")
        
        mock_file = mock_open()
        with patch('builtins.open', mock_file):
            with patch('pathlib.Path.mkdir'):
                augment_step._save_augmented_transcript(transcript, output_path)
                
                # Check that file was written
                mock_file.assert_called_once_with(output_path, 'w', encoding='utf-8')
                
                # Check that json.dump was called (indirectly via the file write)
                handle = mock_file()
                assert handle.write.called
    
    def test_simplified_execute_method(self, augment_step, mock_context, sample_transcript):
        """Test that the execute method is now simplified and delegates to helper methods."""
        mock_context.augmented_transcript_path.exists.return_value = False
        
        with patch.object(augment_step, '_load_and_preprocess_transcript') as mock_load, \
             patch.object(augment_step, '_create_batches') as mock_create_batches, \
             patch.object(augment_step, '_process_batches') as mock_process_batches, \
             patch.object(augment_step, '_save_augmented_transcript') as mock_save, \
             patch.object(augment_step, 'run_next') as mock_run_next, \
             patch('mitlesen.ai.get_ai_client') as mock_get_client:
            
            mock_load.return_value = sample_transcript
            mock_create_batches.return_value = [{'sentences': sample_transcript, 'start_idx': 0, 'end_idx': 2, 'word_count': 8}]
            mock_process_batches.return_value = sample_transcript
            mock_run_next.return_value = True
            
            result = augment_step.execute(mock_context)
            
            # Check that all helper methods were called
            mock_load.assert_called_once_with(mock_context)
            mock_create_batches.assert_called_once_with(sample_transcript)
            mock_process_batches.assert_called_once()
            mock_save.assert_called_once()
            mock_run_next.assert_called_once_with(mock_context)
            
            assert result is True


class TestAugmentStepRefactoringSuccess:
    """Test that the AugmentStep refactoring was successful (TODO #3 - COMPLETED)."""
    
    def test_complex_execute_method_simplified(self):
        """Test that the complex execute method has been simplified."""
        augment_step = AugmentStep("test")
        
        # The execute method should now be much shorter and delegate to helper methods
        execute_method = augment_step.execute
        import inspect
        source_lines = inspect.getsource(execute_method)
        
        # Should be significantly shorter than the original (which was ~70 lines)
        line_count = len(source_lines.strip().split('\n'))
        assert line_count < 35, f"Execute method still too long: {line_count} lines"
    
    def test_batch_creation_extracted(self):
        """Test that batch creation logic has been extracted to separate methods."""
        augment_step = AugmentStep("test")
        
        # Should have the extracted methods
        assert hasattr(augment_step, '_create_batches')
        assert hasattr(augment_step, '_create_single_batch')
        assert callable(augment_step._create_batches)
        assert callable(augment_step._create_single_batch)
    
    def test_retry_mechanism_extracted(self):
        """Test that retry mechanism has been extracted to separate method."""
        augment_step = AugmentStep("test")
        
        # Should have the extracted retry method
        assert hasattr(augment_step, '_process_batch_with_retry')
        assert callable(augment_step._process_batch_with_retry)
    
    def test_processing_logic_extracted(self):
        """Test that processing logic has been extracted to separate methods."""
        augment_step = AugmentStep("test")
        
        # Should have extracted processing methods
        assert hasattr(augment_step, '_process_batches')
        assert hasattr(augment_step, '_apply_batch_results')
        assert hasattr(augment_step, '_save_augmented_transcript')
        assert hasattr(augment_step, '_load_and_preprocess_transcript')
        
        # All should be callable
        assert callable(augment_step._process_batches)
        assert callable(augment_step._apply_batch_results)
        assert callable(augment_step._save_augmented_transcript)
        assert callable(augment_step._load_and_preprocess_transcript)
    
    def test_nested_loops_eliminated(self):
        """Test that deeply nested loops have been eliminated."""
        augment_step = AugmentStep("test")
        
        # The execute method should no longer have deeply nested loops
        execute_source = inspect.getsource(augment_step.execute)
        
        # Count while/for loops in execute method
        while_count = execute_source.count('while ')
        for_count = execute_source.count('for ')
        
        # Should have minimal loops in execute (just the main try-catch structure)
        assert while_count <= 1, f"Too many while loops in execute: {while_count}"
        assert for_count <= 1, f"Too many for loops in execute: {for_count}"
    
    def test_single_responsibility_principle(self):
        """Test that methods now follow single responsibility principle."""
        augment_step = AugmentStep("test")
        
        # Each helper method should have a specific, focused purpose
        methods_and_purposes = {
            '_load_and_preprocess_transcript': 'loading and preprocessing',
            '_create_batches': 'batch creation',
            '_create_single_batch': 'single batch creation',
            '_process_batches': 'batch processing coordination',
            '_process_batch_with_retry': 'retry logic',
            '_apply_batch_results': 'result application',
            '_save_augmented_transcript': 'file saving'
        }
        
        for method_name, purpose in methods_and_purposes.items():
            assert hasattr(augment_step, method_name), f"Missing method: {method_name} for {purpose}"
            
            # Check that method has appropriate docstring
            method = getattr(augment_step, method_name)
            assert method.__doc__ is not None, f"Method {method_name} should have docstring"
            assert purpose.split()[0] in method.__doc__.lower(), f"Method {method_name} docstring should mention {purpose}"
    
    def test_error_handling_preserved(self):
        """Test that error handling is preserved after refactoring."""
        augment_step = AugmentStep("test")
        
        # The main execute method should still have proper error handling
        execute_source = inspect.getsource(augment_step.execute)
        
        assert 'try:' in execute_source
        assert 'except Exception' in execute_source
        assert 'logger.error' in execute_source
        
        # Retry logic should be in the retry method
        retry_source = inspect.getsource(augment_step._process_batch_with_retry)
        assert 'try:' in retry_source
        assert 'except Exception' in retry_source