import json
import time
from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from mitlesen.ai import get_ai_client
from mitlesen.prompts import aug_transcript_prompt
from mitlesen.schema import Transcript
from mitlesen.japanese import get_japanese_splitter
from mitlesen.dictionary import SqliteDictionary
from mitlesen import DICTIONARIES_DIR

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
        logger.info(f"🤖 Starting augmentation for {context.youtube_id}")
        logger.info(f"Transcript path: {context.transcript_path}")
        logger.info(f"Augmented transcript path: {context.augmented_transcript_path}")
        if context.augmented_transcript_path.exists():
            logger.warning(f"⚠️ Augmented transcript already exists: {context.augmented_transcript_path}")
            return self.run_next(context)
        try:
            logger.info(f"Opening transcript file: {context.transcript_path}")
            with open(context.transcript_path, 'r', encoding='utf-8') as file:
                transcript = json.load(file)
            logger.info(f"Loaded transcript with {len(transcript)} segments.")
            client = get_ai_client('gemini', language=context.language)
            if context.language == 'ja':
                logger.info("Preprocessing Japanese transcript...")
                transcript = self.preprocess_japanese_transcript(transcript)
            total_sentences = len(transcript)
            current_idx = 0
            batch_number = 1
            while current_idx < total_sentences:
                batch_sentences = []
                word_count = 0
                batch_start_idx = current_idx
                while current_idx < total_sentences and word_count < self.batch_config.max_words_per_translation_batch:
                    current_sentence = transcript[current_idx]
                    sentence_word_count = len(current_sentence["words"])
                    if word_count + sentence_word_count > self.batch_config.max_words_per_translation_batch and batch_sentences:
                        break
                    batch_sentences.append(current_sentence)
                    word_count += sentence_word_count
                    current_idx += 1
                batch_end_idx = current_idx - 1
                sentences_json = json.dumps(batch_sentences, ensure_ascii=False)
                logger.info(f"About to process batch {batch_number} with {word_count} words (sentences {batch_start_idx} to {batch_end_idx})")
                prompt = aug_transcript_prompt(sentences_json, language=context.language)
                api_retry_count = 0
                success = False
                while not success:
                    try:
                        logger.debug(f"Sending batch {batch_number} to AI client...")
                        completion = client.complete(prompt, response_schema=Transcript)
                        processed_batch = Transcript.model_validate_json(completion).root
                        for i, sentence in enumerate(processed_batch):
                            original_idx = batch_start_idx + i
                            if original_idx < total_sentences:
                                transcript[original_idx]["translation"] = sentence.translation
                                for j, (orig_word, proc_word) in enumerate(
                                    zip(transcript[original_idx]["words"], [w.model_dump() for w in sentence.words])
                                ):
                                    transcript[original_idx]["words"][j] = proc_word | orig_word
                        logger.info(f"Processed batch {batch_number} (sentences {batch_start_idx} to {batch_end_idx}, {word_count} words)")
                        success = True
                        batch_number += 1
                    except Exception as err:
                        api_retry_count += 1
                        logger.error(f"Exception in batch {batch_number}: {err}")
                        if api_retry_count > self.batch_config.max_api_retries:
                            logger.error(f"Failed to process batch after {api_retry_count} API retries. Moving to next batch.")
                            batch_number += 1
                            break
                        logger.info(f"❌ Error processing batch with sentences {batch_start_idx}-{batch_end_idx}: {err}")
                        delay = get_retry_delay(api_retry_count)
                        logger.info(f"Waiting {delay} seconds before retry {api_retry_count}...")
                        time.sleep(delay)
                if success:
                    logger.debug(f"Sleeping {self.batch_config.delay_between_batches} seconds after batch {batch_number-1}...")
                    time.sleep(self.batch_config.delay_between_batches)
            # Ensure parent directory exists
            logger.info(f"Ensuring parent directory exists for: {context.augmented_transcript_path.parent}")
            context.augmented_transcript_path.parent.mkdir(parents=True, exist_ok=True)
            logger.info(f"Writing augmented transcript to: {context.augmented_transcript_path}")
            with open(context.augmented_transcript_path, 'w', encoding='utf-8') as f:
                json.dump(transcript, f, ensure_ascii=False, indent=2)
            logger.info(f"✅ Augmentation completed for {context.youtube_id}")
            return self.run_next(context)
        except Exception as e:
            logger.error(f"❌ Augmentation failed: {str(e)}")
            logger.exception(e)
            return False

    def preprocess_japanese_transcript(self, transcript):
        dict_path = DICTIONARIES_DIR + '/output/dictionary.sqlite'
        dictionary = SqliteDictionary(dict_path)
        try:
            splitter = get_japanese_splitter()
            for segment in transcript:
                if 'words' in segment:
                    new_words = self.merge_timestamps(segment['words'], splitter)
                    for word in new_words:
                        entry = dictionary.search_japanese_word(word)
                        if entry:
                            word['id'] = entry['id']
                    segment['text'] = ''.join(word['text'] for word in new_words)
                    segment['words'] = new_words
        finally:
            dictionary.close()
        return transcript

    def merge_timestamps(self, words, splitter):
        new_sentence = ''.join(word['text'] for word in words)
        split_words, lemmas_kana, lemmas_kanji, romaji_phonetics, hiragana_phonetics, pos_tags = splitter.split_sentence(new_sentence)
        new_words = []
        current_pos = 0
        for word_text, lemma_kana, lemma_kanji, romaji_phonetic, hiragana_phonetic, pos_tag in zip(split_words, lemmas_kana, lemmas_kanji, romaji_phonetics, hiragana_phonetics, pos_tags):
            word_chars = []
            start_time = None
            end_time = None
            while current_pos < len(words) and len(''.join(word_chars)) < len(word_text):
                current_word = words[current_pos]
                word_chars.append(current_word['text'])
                if start_time is None:
                    start_time = current_word['start']
                end_time = current_word['end']
                current_pos += 1
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