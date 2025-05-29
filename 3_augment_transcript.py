#!/usr/bin/env python3
import json
import os.path
import time
import argparse
from typing import Dict, List, Any, Tuple

from dotenv import load_dotenv
from mitlesen.ai import CompletionClient
from mitlesen.logger import logger
from mitlesen.prompts import aug_transcript_prompt, jp_word_split_prompt, jp_word_split_fix_prompt
from mitlesen.schema import Transcript

load_dotenv()

# Unicode ranges for different Japanese character types
KANJI_RANGE = (0x4E00, 0x9FFF)  # CJK Unified Ideographs
HIRAGANA_RANGE = (0x3040, 0x309F)
KATAKANA_RANGE = (0x30A0, 0x30FF)

def is_kanji(char: str) -> bool:
    """Check if a character is a kanji."""
    code = ord(char)
    return KANJI_RANGE[0] <= code <= KANJI_RANGE[1]

def is_kana(char: str) -> bool:
    """Check if a character is hiragana or katakana."""
    code = ord(char)
    return (HIRAGANA_RANGE[0] <= code <= HIRAGANA_RANGE[1] or
            KATAKANA_RANGE[0] <= code <= KATAKANA_RANGE[1])

def is_special_char(char: str) -> bool:
    """Check if a character is a special character (punctuation, symbol, etc.)."""
    return not (is_kanji(char) or is_kana(char))

# Batch processing configuration
class BatchConfig:
    """Configuration for batch processing."""
    def __init__(
        self,
        max_words_per_translation_batch: int = 30,  # Maximum words per translation batch
        max_sentences_per_word_split_batch: int = 5,  # Maximum sentences per word split batch
        max_validation_retries: int = 50,  # Maximum number of retries for validation errors
        max_api_retries: int = 10,  # Maximum number of retries for API errors
        delay_between_batches: int = 2,  # Delay between successful batches in seconds
    ):
        self.max_words_per_translation_batch = max_words_per_translation_batch
        self.max_sentences_per_word_split_batch = max_sentences_per_word_split_batch
        self.max_validation_retries = max_validation_retries
        self.max_api_retries = max_api_retries
        self.delay_between_batches = delay_between_batches

def get_retry_delay(retry_count: int, is_validation_error: bool = False) -> int:
    """Calculate retry delay based on retry count and error type."""
    # For validation errors (incorrect LLM responses), use shorter delays
    if is_validation_error:
        if retry_count == 1: return 1
        if retry_count == 2: return 2
        return 3
    
    # For API errors (rate limits, timeouts), use longer delays
    if retry_count == 1: return 30
    if retry_count == 2: return 60
    if retry_count == 3: return 120
    if retry_count == 4: return 180
    return 300  # 5th retry and beyond

class ValidationError(Exception):
    """Custom exception for validation errors that can be fixed by the LLM."""
    def __init__(self, message: str, original_sentence: str, current_words: List[str]):
        super().__init__(message)
        self.original_sentence = original_sentence
        self.current_words = current_words

def validate_word_splits(original_sentence: str, words: List[str]) -> None:
    """Validate that word splits match the original sentence exactly, excluding special characters.
    
    Args:
        original_sentence: Original Japanese sentence
        words: List of words to validate
        
    Raises:
        ValidationError: If validation fails and can be fixed by LLM
        ValueError: If validation fails due to other issues
    """
    # Remove any whitespace and special characters from original sentence
    original = ''.join(c for c in original_sentence if not is_special_char(c))
    
    # Concatenate all words, remove whitespace, and then remove special characters
    reconstructed = ''.join(words).replace(' ', '')
    reconstructed = ''.join(c for c in reconstructed if not is_special_char(c))
    
    if original != reconstructed:
        error_msg = (
            f"Word splits do not match original sentence (excluding special characters).\n"
            f"Original (without special chars): {original}\n"
            f"Reconstructed (without special chars): {reconstructed}\n"
            f"Words: {words}"
        )
        raise ValidationError(error_msg, original_sentence, words)


def try_fix_word_splits(client: CompletionClient, sentence: str, error: ValidationError) -> Tuple[List[str], List[List[str]]]:
    """Attempt to fix word splits using a follow-up request to the LLM.
    
    Args:
        client: AI completion client
        sentence: Original Japanese sentence
        error: Validation error that occurred
        
    Returns:
        Tuple of (List of words, List of per-character romaji for each word)
        
    Raises:
        RuntimeError: If the fix attempt fails
    """
    try:
        # Create follow-up prompt with error details
        prompt = jp_word_split_fix_prompt(sentence, str(error), error.current_words)
        
        # Get new attempt from LLM
        completion = client.complete(prompt)
        result = json.loads(completion)
        
        # Validate the new attempt
        if not isinstance(result, dict) or "words" not in result or "phonetics" not in result:
            raise ValueError("Invalid response format in fix attempt")
        
        # Validate the new word splits
        validate_word_splits(sentence, result["words"])
        
        return result["words"], result["phonetics"]
        
    except Exception as e:
        # Re-raise as ValidationError to get the shorter retry delay
        if isinstance(e, (ValidationError, ValueError)):
            raise ValidationError(str(e), sentence, error.current_words)
        raise RuntimeError(f"Failed to fix word splits: {e}")

def split_japanese_words_batch(client: CompletionClient, sentences: List[str], batch_config: BatchConfig) -> List[Tuple[List[str], List[List[str]]]]:
    """Get word splits for a batch of Japanese sentences using LLM.
    
    Args:
        client: AI completion client
        sentences: List of Japanese sentences to split
        batch_config: Batch processing configuration
        
    Returns:
        List of tuples, each containing (List of words, List of per-character romaji for each word)
    """
    results = []
    total_sentences = len(sentences)
    current_idx = 0
    
    while current_idx < total_sentences:
        # Get batch of sentences
        batch_end = min(current_idx + batch_config.max_sentences_per_word_split_batch, total_sentences)
        batch_sentences = sentences[current_idx:batch_end]
        
        # Log the batch being processed
        logger.info(f"Processing batch {current_idx}-{batch_end-1} with {len(batch_sentences)} sentences:")
        for i, sentence in enumerate(batch_sentences):
            logger.info(f"  {current_idx + i}: {sentence}")
        
        # Create batch prompt
        prompt = jp_word_split_prompt(json.dumps(batch_sentences, ensure_ascii=False))
        
        validation_retry_count = 0
        api_retry_count = 0
        success = False
        batch_results = []
        accumulated_errors = []  # Track all validation errors for this batch
    
        while not success:
            try:
                if validation_retry_count > 0 or api_retry_count > 0:
                    total_retries = validation_retry_count + api_retry_count
                    logger.info(f"Retry attempt {total_retries} for batch {current_idx}-{batch_end-1} "
                              f"(validation: {validation_retry_count}, API: {api_retry_count})")
                    if accumulated_errors:
                        logger.info(f"Previous validation errors in this batch:\n" + "\n".join(f"- {err}" for err in accumulated_errors))
                
                # If we have accumulated errors, use the fix prompt instead
                if accumulated_errors:
                    error_summary = "\n".join(f"- {err}" for err in accumulated_errors)
                    prompt = jp_word_split_fix_prompt(
                        json.dumps(batch_sentences, ensure_ascii=False),
                        f"Previous attempts had these validation errors:\n{error_summary}",
                        []  # No current words since we're retrying the whole batch
                    )
                
                completion = client.complete(prompt)
                response = json.loads(completion)
                
                # Handle different response formats
                if isinstance(response, dict):
                    # If we got a single object, wrap it in a list
                    if "words" in response and "phonetics" in response:
                        logger.warning("Received single object instead of array, wrapping in list")
                        batch_results = [response]
                    else:
                        raise ValueError(f"Invalid response format. Got a dictionary but it doesn't have the expected fields")
                elif isinstance(response, list):
                    batch_results = response
                else:
                    raise ValueError(f"Invalid response format. Expected list or dict, got {type(response)}")
                
                # Validate and process results
                if len(batch_results) != len(batch_sentences):
                    raise ValueError(
                        f"Invalid response format. Expected {len(batch_sentences)} results, got {len(batch_results)}. "
                        f"Response: {json.dumps(batch_results, ensure_ascii=False)}"
                    )
                
                # Process each sentence in the batch
                fixed_results = []
                for i, (sentence, result) in enumerate(zip(batch_sentences, batch_results)):
                    try:
                        if not isinstance(result, dict) or "words" not in result or "phonetics" not in result:
                            raise ValueError(
                                f"Result {i} must have 'words' and 'phonetics' fields. "
                                f"Got: {json.dumps(result, ensure_ascii=False)}"
                            )
                        if not isinstance(result["words"], list) or not isinstance(result["phonetics"], list):
                            raise ValueError(
                                f"Result {i}: 'words' and 'phonetics' must be lists. "
                                f"Got: {json.dumps(result, ensure_ascii=False)}"
                            )
                        if len(result["words"]) != len(result["phonetics"]):
                            raise ValueError(
                                f"Result {i}: Number of words and phonetics must match. "
                                f"Got: {json.dumps(result, ensure_ascii=False)}"
                            )
                        
                        # Validate word splits and phonetics
                        validate_word_splits(sentence, result["words"])
                        
                        fixed_results.append(result)
                        
                    except ValidationError as e:
                        # Add this error to our accumulated errors
                        error_msg = f"Sentence {i} ('{sentence}'): {str(e)}"
                        if error_msg not in accumulated_errors:  # Avoid duplicate errors
                            accumulated_errors.append(error_msg)
                        
                        # Try to fix this specific sentence
                        logger.info(f"Attempting to fix word splits for sentence {i} in batch {current_idx}-{batch_end-1}: {sentence}")
                        fixed_words, fixed_phonetics = try_fix_word_splits(client, sentence, e)
                        fixed_results.append({
                            "words": fixed_words,
                            "phonetics": fixed_phonetics
                        })
                        logger.info(f"Successfully fixed word splits for sentence {i}")
                
                # All sentences in batch processed successfully
                results.extend([(r["words"], r["phonetics"]) for r in fixed_results])
                success = True
                logger.info(f"Successfully processed word split batch {current_idx}-{batch_end-1}")
                
            except Exception as e:
                is_validation_error = isinstance(e, (ValidationError, ValueError))
                if is_validation_error:
                    validation_retry_count += 1
                    # Add validation errors to our accumulated list
                    error_msg = str(e)
                    if error_msg not in accumulated_errors:  # Avoid duplicate errors
                        accumulated_errors.append(error_msg)
                    
                    if validation_retry_count > batch_config.max_validation_retries:
                        raise RuntimeError(f"Failed to split words batch after {validation_retry_count} validation retries. "
                                         f"Accumulated errors:\n" + "\n".join(f"- {err}" for err in accumulated_errors))
                else:
                    api_retry_count += 1
                    if api_retry_count > batch_config.max_api_retries:
                        raise RuntimeError(f"Failed to split words batch after {api_retry_count} API retries")
                
                total_retries = validation_retry_count + api_retry_count
                logger.warning(f"Failed to split words batch (attempt {total_retries}): {e}")
                
                delay = get_retry_delay(total_retries, is_validation_error)
                logger.info(f"Waiting {delay} seconds before retry... (validation error: {is_validation_error})")
                time.sleep(delay)
        
        # Move to next batch
        current_idx = batch_end
        
        # Add delay between batches if successful
        if success and current_idx < total_sentences:
            time.sleep(batch_config.delay_between_batches)
    
    return results

def merge_timestamps(words: List[str], word_phonetics: List[List[str]], chars: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Merge character timestamps into word timestamps.
    
    Args:
        words: List of words from the sentence
        word_phonetics: List of per-character romaji for each word
        chars: List of character-level timestamps
        
    Returns:
        List of word-level timestamps with the same structure as input chars
    """
    result = []
    char_idx = 0
    
    # Build a set of all characters that appear in the words list
    word_chars = set()
    for word in words:
        word_chars.update(word)
    
    # Process each word
    for word, phonetics in zip(words, word_phonetics):
        if not word:  # Skip empty words
            continue
            
        # Find the sequence of characters that make up this word
        word_chars_list = []
        remaining_chars = chars[char_idx:]
        
        # Build up the word character by character
        current_word = ""
        for char in remaining_chars:
            # Skip characters that aren't part of any word
            if char['text'] not in word_chars:
                char_idx += 1
                continue
                
            current_word += char['text']
            word_chars_list.append(char)
            if current_word == word:
                break
            if len(current_word) > len(word):
                # Log the mismatch and skip this word instead of failing
                logger.warning(f"Could not match word '{word}' in character sequence. Found '{current_word}'. Skipping word.")
                word_chars_list = []  # Clear the partial match
                break
        
        if not word_chars_list:
            # If no characters found or word was skipped, continue to next word
            continue
            
        # Create word object with timestamps from first and last character
        word_obj = {
            'text': word,
            'start': word_chars_list[0]['start'],
            'end': word_chars_list[-1]['end'],
            'phonetic': phonetics,  # Add the per-character romaji
        }
        
        # Copy any additional fields from the first character
        for key, value in word_chars_list[0].items():
            if key not in word_obj:
                word_obj[key] = value
        
        result.append(word_obj)
        char_idx += len(word_chars_list)
    
    return result

def preprocess_japanese_transcript(transcript: List[Dict[str, Any]], client: CompletionClient, batch_config: BatchConfig) -> List[Dict[str, Any]]:
    """Preprocess Japanese transcript to merge character-level timestamps into word-level.
    
    Args:
        transcript: List of transcript segments
        client: AI completion client
        batch_config: Batch processing configuration
        
    Returns:
        Preprocessed transcript with word-level timestamps
    """
    # Extract all sentences for batch processing
    sentences = [segment['text'] for segment in transcript]
    
    # Get word splits and phonetics for all sentences in batches
    word_splits = split_japanese_words_batch(client, sentences, batch_config)
    
    # Update transcript with word splits
    for segment, (words, word_phonetics) in zip(transcript, word_splits):
        segment['words'] = merge_timestamps(words, word_phonetics, segment['words'])
    
    return transcript

def augment_transcript(youtube_id: str, language: str = 'de', batch_config: BatchConfig = None) -> None:
    """
    Process a transcript file and augment it with AI-generated translations and word-level information.
    
    Args:
        youtube_id: YouTube video ID
        language: Language code ('de' for German, 'ja' for Japanese)
        batch_config: Batch processing configuration
    """
    if batch_config is None:
        batch_config = BatchConfig()
        
    DATA_FOLDER = 'data'
    transcript_path = os.path.join(DATA_FOLDER, youtube_id + '.json')
    output_path = os.path.join(DATA_FOLDER, youtube_id + '.json.2')

    with open(transcript_path, 'r', encoding='utf-8') as file:
        text = file.read()
        transcript: List[Dict[str, Any]] = json.loads(text)
        client = CompletionClient(backend='gemini', language=language)
        
        try:
            # Preprocess Japanese transcripts
            if language == 'ja':
                transcript = preprocess_japanese_transcript(transcript, client, batch_config)
            
            total_sentences = len(transcript)
            
            # Process in batches based on word count
            current_idx = 0
            batch_number = 1
            
            while current_idx < total_sentences:
                batch_sentences: List[Dict[str, Any]] = []
                word_count = 0
                batch_start_idx = current_idx
                
                # Build batch until we hit the word limit or run out of sentences
                while current_idx < total_sentences and word_count < batch_config.max_words_per_translation_batch:
                    current_sentence = transcript[current_idx]
                    sentence_word_count = len(current_sentence["words"])
                    
                    if word_count + sentence_word_count > batch_config.max_words_per_translation_batch and batch_sentences:
                        break
                    
                    batch_sentences.append(current_sentence)
                    word_count += sentence_word_count
                    current_idx += 1
                
                batch_end_idx = current_idx - 1
                
                # Create batch prompt
                sentences_json = json.dumps(batch_sentences, ensure_ascii=False)
                logger.debug(f"About to process batch {batch_number} with {word_count} words (sentences {batch_start_idx} to {batch_end_idx})")
                prompt = aug_transcript_prompt(sentences_json, language=language)
                
                validation_retry_count = 0
                api_retry_count = 0
                success = False
                
                while not success:
                    try:
                        # Use the schema-based completion
                        completion = client.complete(prompt, response_schema=Transcript)
                        processed_batch: List[Dict[str, Any]] = Transcript.model_validate_json(completion).root
                        
                        # Update the original transcript with processed data
                        for i, sentence in enumerate(processed_batch):
                            original_idx = batch_start_idx + i
                            if original_idx < total_sentences:
                                # Add translation to original sentence
                                transcript[original_idx]["translation"] = sentence.translation
                                # Update word data in original sentence
                                for j, (orig_word, proc_word) in enumerate(
                                    zip(transcript[original_idx]["words"], [w.model_dump() for w in sentence.words])
                                ):
                                    # Merge the processed word info with original word data
                                    transcript[original_idx]["words"][j] = proc_word | orig_word
                        
                        logger.info(f"Processed batch {batch_number} (sentences {batch_start_idx} to {batch_end_idx}, {word_count} words)")
                        success = True
                        batch_number += 1
                        
                    except Exception as err:
                        is_validation_error = isinstance(err, (ValidationError, ValueError))
                        if is_validation_error:
                            validation_retry_count += 1
                            if validation_retry_count > batch_config.max_validation_retries:
                                logger.error(f"Failed to process batch after {validation_retry_count} validation retries. Moving to next batch.")
                                batch_number += 1
                                break
                        else:
                            api_retry_count += 1
                            if api_retry_count > batch_config.max_api_retries:
                                logger.error(f"Failed to process batch after {api_retry_count} API retries. Moving to next batch.")
                                batch_number += 1
                                break
                        
                        total_retries = validation_retry_count + api_retry_count
                        logger.info(f"❌ Error processing batch with sentences {batch_start_idx}-{batch_end_idx}: {err}")
                        
                        delay = get_retry_delay(total_retries, is_validation_error)
                        logger.info(f"Waiting {delay} seconds before retry {total_retries}... (validation error: {is_validation_error})")
                        time.sleep(delay)
                
                # Wait between batches (only if successful)
                if success:
                    time.sleep(batch_config.delay_between_batches)

            # Save the augmented transcript
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            
            logger.info(f"✅ Augmented transcript saved to {output_path}")
            
        except Exception as err:
            logger.error(f"❌ Error processing {youtube_id}: {err}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Augment transcript with AI-generated translations and word-level information')
    parser.add_argument('--youtube_id', type=str, required=True, help='YouTube video ID')
    parser.add_argument('--language', type=str, default='de', choices=['de', 'ja'], help='Language code (de/ja)')
    parser.add_argument('--max-words-per-translation-batch', type=int, default=30, help='Maximum number of words per translation batch')
    parser.add_argument('--max-sentences-per-word-split-batch', type=int, default=1, help='Maximum number of sentences per word split batch')
    parser.add_argument('--max-validation-retries', type=int, default=50, help='Maximum number of retries for validation errors')
    parser.add_argument('--max-api-retries', type=int, default=10, help='Maximum number of retries for API errors')
    parser.add_argument('--delay-between-batches', type=int, default=2, help='Delay between successful batches in seconds')
    
    args = parser.parse_args()
    
    batch_config = BatchConfig(
        max_words_per_translation_batch=args.max_words_per_translation_batch,
        max_sentences_per_word_split_batch=args.max_sentences_per_word_split_batch,
        max_validation_retries=args.max_validation_retries,
        max_api_retries=args.max_api_retries,
        delay_between_batches=args.delay_between_batches
    )
    
    augment_transcript(args.youtube_id, args.language, batch_config) 