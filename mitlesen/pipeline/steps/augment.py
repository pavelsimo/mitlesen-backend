import json
import time
from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from mitlesen.ai import get_ai_client
from mitlesen.prompts import aug_transcript_prompt
from mitlesen.schema import Transcript
from mitlesen.nlp import get_transcript_processor

# BatchConfig from 3_augment_transcript.py
class BatchConfig:
    def __init__(
        self,
        max_words_per_translation_batch: int = 30,
        max_api_retries: int = 10,
        delay_between_batches: int = 2,
    ):
        self.max_words_per_translation_batch = max_words_per_translation_batch
        self.max_api_retries = max_api_retries
        self.delay_between_batches = delay_between_batches

def get_retry_delay(retry_count: int) -> int:
    if retry_count == 1: return 30
    if retry_count == 2: return 60
    if retry_count == 3: return 120
    if retry_count == 4: return 180
    return 300

class AugmentStep(PipelineStep):
    def __init__(self, name: str, batch_config: BatchConfig = None):
        super().__init__(name)
        self.batch_config = batch_config or BatchConfig()

    def execute(self, context: PipelineContext) -> bool:
        """Execute the augmentation pipeline with simplified batch processing logic."""
        logger.info(f"🤖 Starting augmentation for {context.youtube_id}")
        logger.info(f"Transcript path: {context.transcript_path}")
        logger.info(f"Augmented transcript path: {context.augmented_transcript_path}")

        if context.augmented_transcript_path.exists():
            logger.warning(f"⚠️ Augmented transcript already exists: {context.augmented_transcript_path}")
            return self.run_next(context)

        try:
            # Load and preprocess transcript
            transcript = self._load_and_preprocess_transcript(context)

            # Get AI client
            client = get_ai_client('gemini', language=context.language)

                        # Create and process batches
            batches = self._create_batches(transcript)
            processed_transcript = self._process_batches(batches, transcript, client, context.language)

            # Save augmented transcript
            self._save_augmented_transcript(processed_transcript, context.augmented_transcript_path)

            logger.info(f"✅ Augmentation completed for {context.youtube_id}")
            return self.run_next(context)

        except Exception as e:
            logger.error(f"❌ Augmentation failed: {str(e)}")
            logger.exception(e)
            return False

    def _load_and_preprocess_transcript(self, context: PipelineContext) -> list:
        """Load transcript from file and apply language-specific preprocessing."""
        logger.info(f"Opening transcript file: {context.transcript_path}")
        with open(context.transcript_path, 'r', encoding='utf-8') as file:
            transcript = json.load(file)

        logger.info(f"Loaded transcript with {len(transcript)} segments.")

        # Use factory pattern instead of language-specific branching
        try:
            processor = get_transcript_processor(context.language)
            logger.info(f"Preprocessing {context.language} transcript...")
            transcript = processor.preprocess_transcript(transcript)
        except ValueError as e:
            logger.warning(f"No transcript processor available for {context.language}: {e}")
            # Continue without preprocessing for unsupported languages

        return transcript

    def _create_batches(self, transcript: list) -> list:
        """Create batches of sentences respecting word count limits."""
        batches = []
        total_sentences = len(transcript)
        current_idx = 0

        while current_idx < total_sentences:
            batch = self._create_single_batch(transcript, current_idx, total_sentences)
            batches.append(batch)
            current_idx = batch['end_idx'] + 1

        logger.info(f"Created {len(batches)} batches for processing")
        return batches

    def _create_single_batch(self, transcript: list, start_idx: int, total_sentences: int) -> dict:
        """Create a single batch starting from the given index."""
        batch_sentences = []
        word_count = 0
        current_idx = start_idx

        while (current_idx < total_sentences and
               word_count < self.batch_config.max_words_per_translation_batch):

            current_sentence = transcript[current_idx]
            sentence_word_count = len(current_sentence["words"])

            # Check if adding this sentence would exceed the limit
            if (word_count + sentence_word_count > self.batch_config.max_words_per_translation_batch
                and batch_sentences):
                break

            batch_sentences.append(current_sentence)
            word_count += sentence_word_count
            current_idx += 1

        return {
            'sentences': batch_sentences,
            'start_idx': start_idx,
            'end_idx': current_idx - 1,
            'word_count': word_count
        }

    def _process_batches(self, batches: list, transcript: list, client, language: str) -> list:
        """Process all batches with retry logic."""
        for batch_number, batch in enumerate(batches, 1):
            logger.info(f"About to process batch {batch_number} with {batch['word_count']} words "
                       f"(sentences {batch['start_idx']} to {batch['end_idx']})")

            success = self._process_batch_with_retry(batch, transcript, client, language, batch_number)

            if success:
                logger.debug(f"Sleeping {self.batch_config.delay_between_batches} seconds after batch {batch_number}...")
                time.sleep(self.batch_config.delay_between_batches)
            else:
                logger.warning(f"Batch {batch_number} failed after all retries, continuing with next batch")

        return transcript

    def _process_batch_with_retry(self, batch: dict, transcript: list, client, language: str, batch_number: int) -> bool:
        """Process a single batch with retry mechanism."""
        sentences_json = json.dumps(batch['sentences'], ensure_ascii=False)
        prompt = aug_transcript_prompt(sentences_json, language=language)

        for retry_count in range(self.batch_config.max_api_retries + 1):
            try:
                logger.debug(f"Sending batch {batch_number} to AI client (attempt {retry_count + 1})...")

                completion = client.complete(prompt, response_schema=Transcript)
                processed_batch = Transcript.model_validate_json(completion).root

                # Apply processed results to original transcript
                self._apply_batch_results(batch, processed_batch, transcript)

                logger.info(f"Processed batch {batch_number} (sentences {batch['start_idx']} to {batch['end_idx']}, {batch['word_count']} words)")
                return True

            except Exception as err:
                logger.error(f"Exception in batch {batch_number} (attempt {retry_count + 1}): {err}")

                if retry_count >= self.batch_config.max_api_retries:
                    logger.error(f"Failed to process batch {batch_number} after {retry_count + 1} attempts")
                    return False

                delay = get_retry_delay(retry_count + 1)
                logger.info(f"Waiting {delay} seconds before retry {retry_count + 2}...")
                time.sleep(delay)

        return False

    def _apply_batch_results(self, batch: dict, processed_batch: list, transcript: list) -> None:
        """Apply processed batch results to the original transcript."""
        for i, sentence in enumerate(processed_batch):
            original_idx = batch['start_idx'] + i
            if original_idx <= batch['end_idx'] and original_idx < len(transcript):
                # Clean up segment-level fields - only keep essential ones
                cleaned_segment = {
                    "id": transcript[original_idx]["id"],
                    "text": transcript[original_idx]["text"],
                    "start": transcript[original_idx]["start"],
                    "end": transcript[original_idx]["end"],
                    "words": [],
                    "translation": sentence.translation
                }

                # Merge word-level annotations - preserve original timestamps, add AI annotations
                orig_words = transcript[original_idx]["words"]
                proc_words = [w.model_dump() for w in sentence.words]

                # Safety check: ensure word counts match to prevent timestamp corruption
                if len(orig_words) != len(proc_words):
                    logger.warning(f"Word count mismatch in segment {original_idx}: "
                                 f"original={len(orig_words)}, processed={len(proc_words)}. "
                                 f"Using original words without AI annotations.")
                    # Use original words without AI annotations to preserve timestamps
                    for orig_word in orig_words:
                        cleaned_word = {
                            "text": orig_word["text"],
                            "start": orig_word["start"],
                            "end": orig_word["end"]
                        }
                        cleaned_segment["words"].append(cleaned_word)
                else:
                    # Safe to merge when word counts match
                    for j, (orig_word, proc_word) in enumerate(zip(orig_words, proc_words)):
                        # Start with original word (preserving timestamps)
                        cleaned_word = {
                            "text": orig_word["text"],
                            "start": orig_word["start"],  # Always use original Whisper timestamps
                            "end": orig_word["end"],      # Always use original Whisper timestamps
                        }

                        # Add only linguistic annotations from AI (never timestamps)
                        ai_annotations = {k: v for k, v in proc_word.items()
                                        if k not in ["text", "start", "end"]}
                        cleaned_word.update(ai_annotations)

                        # For Japanese, ensure case field is empty
                        if context.language == 'ja' and 'case' in cleaned_word:
                            cleaned_word['case'] = ""

                        cleaned_segment["words"].append(cleaned_word)

                # Replace the original segment with the cleaned version
                transcript[original_idx] = cleaned_segment

    def _save_augmented_transcript(self, transcript: list, output_path) -> None:
        """Save the augmented transcript to file."""
        logger.info(f"Ensuring parent directory exists for: {output_path.parent}")
        output_path.parent.mkdir(parents=True, exist_ok=True)

        logger.info(f"Writing augmented transcript to: {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(transcript, f, ensure_ascii=False, indent=2)

