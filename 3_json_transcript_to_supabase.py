import json
import os.path
import time
import argparse
from typing import Dict, List, Any, Optional, Union, Tuple

from dotenv import load_dotenv
from mitlesen.ai import CompletionClient
from mitlesen.db import Database, Video
from mitlesen.logger import logger
from mitlesen.schema import Sentence, Transcript

load_dotenv()

def get_retry_delay(retry_count: int) -> int:
    """Calculate retry delay based on retry count."""
    if retry_count == 1:
        return 30
    elif retry_count == 2:
        return 60
    elif retry_count == 3:
        return 120
    elif retry_count == 4:
        return 180
    else:
        return 300  # 5th retry and beyond

def process_transcript(youtube_id: str, title: str, is_premium: bool) -> None:
    """
    Process a transcript file and insert it into the database.
    
    Args:
        youtube_id: YouTube video ID
        title: Title of the YouTube video
        is_premium: Boolean indicating if video is premium
    """
    DATA_FOLDER = 'data'
    MAX_WORDS_PER_BATCH = 30  # Maximum number of words per batch
    MAX_RETRIES = 10  # Maximum number of retries for a failed batch

    db = Database()

    transcript_path = os.path.join(DATA_FOLDER, youtube_id + '.json')

    with open(transcript_path, 'r', encoding='utf-8') as file:
        text = file.read()
        transcript: List[Dict[str, Any]] = json.loads(text)
        client = CompletionClient(backend='gemini')
        try:
            # Check if video already exists
            if Video.exists(db.client, youtube_id):
                logger.info(f"Video {youtube_id} already exists in database, skipping...")
                return

            total_sentences = len(transcript)
            
            # Process in batches based on word count
            current_idx = 0
            batch_number = 1
            
            while current_idx < total_sentences:
                batch_sentences: List[Dict[str, Any]] = []
                word_count = 0
                batch_start_idx = current_idx
                
                # Build batch until we hit the word limit or run out of sentences
                while current_idx < total_sentences and word_count < MAX_WORDS_PER_BATCH:
                    current_sentence = transcript[current_idx]
                    sentence_word_count = len(current_sentence["text"].split())
                    
                    if word_count + sentence_word_count > MAX_WORDS_PER_BATCH and batch_sentences:
                        break
                    
                    batch_sentences.append(current_sentence)
                    word_count += sentence_word_count
                    current_idx += 1
                
                batch_end_idx = current_idx - 1
                
                # Create batch prompt
                sentences_json = json.dumps(batch_sentences, ensure_ascii=False)
                logger.debug(f"About to process batch {batch_number} with {word_count} words (sentences {batch_start_idx} to {batch_end_idx})")
                prompt = f"""
                      You will be given multiple sentences in JSON format to translate.
                      
                      # Task
                      Your task is to add the missing translation for both sentences and words:
                       For each Sentence:
                       - An English translation.                        
                       For each Word within the sentences: 
                       - An English translation.
                       - Its part‑of‑speech tag (use exactly: verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle).
                       - If applicable (German nouns and pronouns), include grammatical case (nominativ, akkusativ, dativ, genitiv).

                    # Guidelines
                    - For each sentence, include its translation
                       - non-literal translation, natural sounding english translation 
                    - For each word, 
                       - include its text, translation, and grammatical information.
                       - use concise, literal translations.

                    # Constraints
                    - Only return the JSON output. Do not include any explanations, comments, or additional text.
                    - Do not use markdown formatting or code blocks.
                    - Make sure the words appear in the same order that are given in the transcript.
                    - Return an array of JSON objects, one for each input sentence.
                    
                    # Input JSON Array
                    {sentences_json}
                """
                
                retry_count = 0
                success = False
                
                while retry_count < MAX_RETRIES and not success:
                    try:
                        # Use the new schema-based completion
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
                        retry_count += 1
                        logger.info(f"❌ Error processing batch with sentences {batch_start_idx}-{batch_end_idx}: {err}")
                        
                        if retry_count < MAX_RETRIES:
                            delay = get_retry_delay(retry_count)
                            logger.info(f"Waiting {delay} seconds before retry {retry_count}/{MAX_RETRIES}...")
                            time.sleep(delay)
                        else:
                            logger.info(f"Failed to process batch after {MAX_RETRIES} retries. Moving to next batch.")
                            batch_number += 1
                
                # Wait between batches (only if successful)
                if success:
                    time.sleep(2)

            # Insert the processed transcript into the database
            Video.insert(
                client=db.client,
                title=title,
                youtube_id=youtube_id,
                is_premium=is_premium,
                transcript=json.dumps(transcript)
            )

            logger.info(f"✅ Transcript inserted successfully")
        except Exception as err:
            logger.error(f"❌ Error processing {youtube_id}: {err}")
        finally:
            db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process YouTube transcript and add to database')
    parser.add_argument('--youtube_id', type=str, required=True, help='YouTube video ID')
    parser.add_argument('--title', type=str, required=True, help='Title of the YouTube video')
    parser.add_argument('--is_premium', type=str, choices=['true', 'false'], default='false', 
                       help='Whether the video is premium or not (true/false)')
    
    args = parser.parse_args()
    
    # Convert string to boolean
    is_premium_bool = args.is_premium.lower() == "true"
    
    process_transcript(args.youtube_id, args.title, is_premium_bool)
