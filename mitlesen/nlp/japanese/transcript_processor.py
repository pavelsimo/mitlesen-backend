from typing import List, Dict, Any
from mitlesen.nlp.base import BaseTranscriptProcessor
from mitlesen.nlp import get_word_splitter
from mitlesen.dictionary import SqliteDictionary
from mitlesen import DICTIONARIES_DIR


class JapaneseTranscriptProcessor(BaseTranscriptProcessor):
    """Japanese-specific transcript preprocessing"""

    def preprocess_transcript(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Preprocess Japanese transcript with word splitting and dictionary lookups.

        Args:
            transcript: List of transcript segments

        Returns:
            Preprocessed transcript with Japanese linguistic annotations
        """
        dict_path = DICTIONARIES_DIR + '/output/dictionary.sqlite'
        dictionary = SqliteDictionary(dict_path)

        try:
            # Use new NLP structure for Japanese word splitting
            splitter = get_word_splitter('ja')

            for segment in transcript:
                if 'words' in segment:
                    # Don't reconstruct the sentence - work with already-segmented text
                    segment_text = segment.get('text', ''.join(word['text'] for word in segment['words']))
                    new_words = self._merge_timestamps(segment['words'], splitter)

                    # Add dictionary lookups using underscore fields
                    for word in new_words:
                        entry = dictionary.search_japanese_word(word)
                        if entry:
                            word['id'] = entry['id']

                        # Clean up temporary underscore fields after dictionary search
                        self._cleanup_temp_fields(word)

                    # Keep the existing segmented text, don't reconstruct
                    segment['text'] = segment_text
                    segment['words'] = new_words
        finally:
            dictionary.close()

        return transcript

    def _merge_timestamps(self, words: List[Dict[str, Any]], splitter) -> List[Dict[str, Any]]:
        """
        Merge timestamps from original words with new Japanese word segmentation.

        Args:
            words: Original word list with timestamps
            splitter: Japanese word splitter instance

        Returns:
            New word list with merged timestamps and linguistic annotations
        """
        new_sentence = ''.join(word['text'] for word in words)
        split_words, lemmas_kana, lemmas_kanji, romaji_phonetics, hiragana_phonetics, pos_tags = splitter.split_sentence(new_sentence)

        new_words = []
        current_pos = 0

        for word_text, lemma_kana, lemma_kanji, romaji_phonetic, hiragana_phonetic, pos_tag in zip(
            split_words, lemmas_kana, lemmas_kanji, romaji_phonetics, hiragana_phonetics, pos_tags
        ):
            word_chars = []
            start_time = None
            end_time = None

            # Merge timing information from original words
            while current_pos < len(words) and len(''.join(word_chars)) < len(word_text):
                current_word = words[current_pos]
                word_chars.append(current_word['text'])
                if start_time is None:
                    start_time = current_word['start']
                end_time = current_word['end']
                current_pos += 1

            new_word = {
                'text': word_text,
                # Use underscore-prefixed names for temporary dictionary search fields
                '_base_form': lemma_kana,
                '_base_form2': lemma_kanji,
                '_pos': pos_tag,
                'start': start_time,
                'end': end_time,
                'romanji': romaji_phonetic,
                'hiragana': hiragana_phonetic
            }
            new_words.append(new_word)

        return new_words

    def _cleanup_temp_fields(self, word: Dict[str, Any]) -> None:
        """
        Remove temporary fields (those starting with underscore) after dictionary search.

        Args:
            word: Word dictionary to clean up
        """
        fields_to_remove = [key for key in word.keys() if key.startswith('_')]
        for field in fields_to_remove:
            del word[field]