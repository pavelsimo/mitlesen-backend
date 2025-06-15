#!/usr/bin/env python3
import json
import os.path
import time
import argparse
from typing import Dict, List, Any, Tuple

from dotenv import load_dotenv

from mitlesen import VIDEOS_DIR
from mitlesen.ai import CompletionClient
from mitlesen.logger import logger
from mitlesen.prompts import aug_transcript_prompt
from mitlesen.schema import Transcript
from mitlesen.japanese import JapaneseWordSplitter
from mitlesen.dictionary import SqliteDictionary
from mitlesen import DICTIONARIES_DIR

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
    """Check if a character is a special character (punctuation, symbol, number, etc.)."""
    # Check if it's a number
    if char.isdigit():
        return True
    # Check if it's not kanji or kana
    return not (is_kanji(char) or is_kana(char))

# Batch processing configuration
class BatchConfig:
    """Configuration for batch processing."""
    def __init__(
        self,
        max_words_per_translation_batch: int = 30,  # Maximum words per translation batch
        max_api_retries: int = 10,  # Maximum number of retries for API errors
        delay_between_batches: int = 2,  # Delay between successful batches in seconds
    ):
        self.max_words_per_translation_batch = max_words_per_translation_batch
        self.max_api_retries = max_api_retries
        self.delay_between_batches = delay_between_batches

def get_retry_delay(retry_count: int) -> int:
    """Calculate retry delay based on retry count."""
    if retry_count == 1: return 30
    if retry_count == 2: return 60
    if retry_count == 3: return 120
    if retry_count == 4: return 180
    return 300  # 5th retry and beyond

def merge_timestamps(words: List[Dict[str, Any]], splitter: JapaneseWordSplitter) -> List[Dict[str, Any]]:
    """Process phonetic transcriptions for words that already have timestamps.
    
    Args:
        words: List of word objects with text and timestamps
        splitter: Japanese word splitter instance
        
    Returns:
        List of word objects with added phonetic transcriptions and adjusted timestamps
    """
    # Step 1: Concatenate all word texts to create new sentence
    new_sentence = ''.join(word['text'] for word in words)
    
    # Step 2: Split the new sentence using the splitter
    split_words, lemmas_kana, lemmas_kanji, romaji_phonetics, hiragana_phonetics, pos_tags = splitter.split_sentence(new_sentence)
    
    # Step 3: Create new words with timestamps and phonetics
    new_words = []
    current_pos = 0
    
    for word_text, lemma_kana, lemma_kanji, romaji_phonetic, hiragana_phonetic, pos_tag in zip(split_words, lemmas_kana, lemmas_kanji, romaji_phonetics, hiragana_phonetics, pos_tags):
        # Find the original words that make up this new word
        word_chars = []
        start_time = None
        end_time = None
        
        # Collect all characters and their timestamps that make up this word
        while current_pos < len(words) and len(''.join(word_chars)) < len(word_text):
            current_word = words[current_pos]
            word_chars.append(current_word['text'])
            if start_time is None:
                start_time = current_word['start']
            end_time = current_word['end']
            current_pos += 1
        
        # Create new word object
        new_word = {
            'text': word_text,
            'base_form': lemma_kana,
            'base_form2': lemma_kanji,
            'pos': pos_tag,
            'start': start_time,
            'end': end_time,
            'phonetic_romaji': romaji_phonetic,
            'phonetic_hiragana': hiragana_phonetic
        }
        new_words.append(new_word)
    
    return new_words

def preprocess_japanese_transcript(transcript: List[Dict[str, Any]], batch_config: BatchConfig) -> List[Dict[str, Any]]:
    """Preprocess Japanese transcript to add phonetic transcriptions to existing word timestamps and enrich with dictionary entries."""
    # Path to the Japanese dictionary
    dict_path = os.path.join(DICTIONARIES_DIR, 'output', 'dictionary.sqlite')
    dictionary = SqliteDictionary(dict_path)
    try:
        # Initialize the Japanese word splitter
        splitter = JapaneseWordSplitter()
        
        # Process each segment
        for segment in transcript:
            if 'words' in segment:
                # Get new words with phonetics and adjusted timestamps
                new_words = merge_timestamps(segment['words'], splitter)
                
                # For each word, look up its base_form (lemma) in the dictionary
                for word in new_words:
                    entry = dictionary.search_japanese_word(word)
                    if entry:
                        # Attach the id of the matching dictionary entry
                        word['id'] = entry['id']
                
                # Update segment with new sentence and words
                segment['text'] = ''.join(word['text'] for word in new_words)
                segment['words'] = new_words
    finally:
        dictionary.close()

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

    transcript_path = os.path.join(VIDEOS_DIR, youtube_id + '.json')
    output_path = os.path.join(VIDEOS_DIR, youtube_id + '.json.2')
    with open(transcript_path, 'r', encoding='utf-8') as file:
        text = file.read()
        transcript: List[Dict[str, Any]] = json.loads(text)
        client = CompletionClient(backend='gemini', language=language)
        
        try:
            # Preprocess Japanese transcripts
            if language == 'ja':
                transcript = preprocess_japanese_transcript(transcript, batch_config)
            
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
                        api_retry_count += 1
                        if api_retry_count > batch_config.max_api_retries:
                            logger.error(f"Failed to process batch after {api_retry_count} API retries. Moving to next batch.")
                            batch_number += 1
                            break
                        
                        logger.info(f"❌ Error processing batch with sentences {batch_start_idx}-{batch_end_idx}: {err}")
                        
                        delay = get_retry_delay(api_retry_count)
                        logger.info(f"Waiting {delay} seconds before retry {api_retry_count}...")
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
    parser.add_argument('--delay-between-batches', type=int, default=2, help='Delay between successful batches in seconds')
    
    args = parser.parse_args()
    
    batch_config = BatchConfig(
        max_words_per_translation_batch=args.max_words_per_translation_batch,
        delay_between_batches=args.delay_between_batches
    )
    
    augment_transcript(args.youtube_id, args.language, batch_config) 