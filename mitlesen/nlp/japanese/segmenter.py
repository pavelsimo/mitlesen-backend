"""Japanese sentence segmentation using Janome."""

import re
from typing import List, Dict, Any, Tuple
from janome.tokenizer import Tokenizer
from mitlesen.logger import logger
from mitlesen.nlp.base import BaseSegmenter, SentenceMatchError

class JapaneseSentenceSegmenter(BaseSegmenter):
    """Japanese sentence segmenter using Janome for natural language processing."""

    def __init__(self):
        """Initialize the Japanese segmenter with Janome tokenizer."""
        # ──────────────────────────────────────────────────────────────────────────────
        # INITIALISATION
        # ──────────────────────────────────────────────────────────────────────────────
        self._tokenizer = Tokenizer()

        # Japanese sentence ending patterns
        self._sentence_endings = re.compile(r'[。！？♪]*')
        self._minor_pause_marks = re.compile(r'[、：；（）〈〉《》「」『』【】〔〕]')

    def split_long_sentence(self, text: str, max_len: int = 100) -> List[str]:
        """
        Break one Japanese sentence into shorter chunks without losing any original
        characters or punctuation.

        Strategy:
        - Walk character-by-character through the text
        - When approaching max_len, look for safe split points:
          1. After sentence-ending punctuation (。！？)
          2. After pause marks (、：；)
          3. After closing brackets/quotes (）」』】etc.)
          4. At word boundaries (identified by Janome tokenization)
        - If no safe split point is found, split at max_len to avoid infinite loops
        """
        if len(text) <= max_len:
            return [text.strip()]

        # Tokenize to get word boundaries
        tokens = list(self._tokenizer.tokenize(text, wakati=False))
        token_positions = []
        pos = 0

        # Map character positions to token boundaries
        for token in tokens:
            start_pos = pos
            end_pos = pos + len(token.surface)
            token_positions.append((start_pos, end_pos, token.surface))
            pos = end_pos

        chunks: List[str] = []
        current_start = 0

        while current_start < len(text):
            if current_start + max_len >= len(text):
                # Last chunk - take everything remaining
                chunk = text[current_start:].strip()
                if chunk:
                    chunks.append(chunk)
                break

            # Find the best split point within max_len
            search_end = min(current_start + max_len, len(text))
            best_split = None

            # Search backwards from max position for good split points
            for i in range(search_end - 1, current_start, -1):
                char = text[i]
                next_char = text[i + 1] if i + 1 < len(text) else ''

                # Priority 1: After sentence endings
                if char in '。！？♪':
                    best_split = i + 1
                    break

                # Priority 2: After pause marks, but avoid splitting within quotes
                if char in '、：；':
                    best_split = i + 1
                    break

                # Priority 3: After closing brackets/quotes
                if char in '）」』】〕》〉':
                    best_split = i + 1
                    break

                # Priority 4: At token boundaries (word boundaries)
                for start_pos, end_pos, surface in token_positions:
                    if end_pos == i + 1 and end_pos - current_start >= max_len * 0.7:
                        # Split at word boundary if we're at least 70% of max_len
                        best_split = end_pos
                        break

                if best_split:
                    break

            # If no good split point found, split at max_len to avoid infinite loop
            if best_split is None:
                best_split = min(current_start + max_len, len(text))

            # Extract chunk and clean it
            chunk = text[current_start:best_split].strip()
            if chunk:
                chunks.append(chunk)

            current_start = best_split

            # Skip whitespace at the beginning of next chunk
            while current_start < len(text) and text[current_start].isspace():
                current_start += 1

        return chunks

    def segment_text(self, text: str, max_len: int = 15) -> List[str]:
        """
        Segment Japanese text into sentences, then split long sentences further.

        Japanese sentence segmentation is primarily based on punctuation:
        - 。(period), ！(exclamation), ？(question mark) end sentences
        - Other punctuation like 、(comma) indicates pauses within sentences
        """
        # Basic sentence splitting by sentence-ending punctuation
        sentences = re.split(r'([。！？♪]+)', text)

        # Recombine split parts (the delimiter is captured in the split)
        combined_sentences = []
        for i in range(0, len(sentences) - 1, 2):
            sentence = sentences[i]
            delimiter = sentences[i + 1] if i + 1 < len(sentences) else ''
            full_sentence = (sentence + delimiter).strip()
            if full_sentence:
                combined_sentences.append(full_sentence)

        # Handle any remaining text that doesn't end with punctuation
        if len(sentences) % 2 == 1 and sentences[-1].strip():
            combined_sentences.append(sentences[-1].strip())

        # If no sentence-ending punctuation found, treat as one sentence
        if not combined_sentences:
            combined_sentences = [text.strip()]

        # Now split long sentences further
        final_sentences: List[str] = []
        for sentence in combined_sentences:
            final_sentences.extend(self.split_long_sentence(sentence, max_len=max_len))

        return [s for s in final_sentences if s.strip()]

    def segment_transcripts(self, segments: List[Dict[str, Any]], max_len: int = 15) -> List[Dict[str, Any]]:
        """
        Override to use Japanese-specific default max_len of 15 characters.

        Args:
            segments: List of transcript segments to process
            max_len: Maximum length for sentence segments (default 15 for Japanese)

        Returns:
            List of segmented transcript segments
        """
        return super().segment_transcripts(segments, max_len)

    def _extract_text_from_words(self, words: List[Dict[str, Any]]) -> str:
        """Extract text using Japanese concatenation (no spaces)."""
        return "".join(w["text"] for w in words)

    def _align_words_to_sentence(self, sentence: str, words: List[Dict[str, Any]], start_idx: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Align words to sentence using Japanese character-by-character matching.

        Uses exact character matching since Japanese text doesn't use spaces between words.
        """
        sentence_chars = list(sentence)
        sentence_words = []
        chars_matched = 0
        current_word_idx = start_idx

        # Walk through words until we've matched all characters in the sentence
        while chars_matched < len(sentence_chars) and current_word_idx < len(words):
            word = words[current_word_idx]
            word_chars = list(word["text"])

            # Check if this word contributes to our sentence
            remaining_sentence_chars = sentence_chars[chars_matched:]

            if len(word_chars) <= len(remaining_sentence_chars):
                # Check if word chars match the beginning of remaining sentence chars
                if word_chars == remaining_sentence_chars[:len(word_chars)]:
                    sentence_words.append(word)
                    chars_matched += len(word_chars)
                    current_word_idx += 1
                else:
                    # Character mismatch - this shouldn't happen with proper alignment
                    logger.warning(f"Character mismatch in Japanese segmentation: "
                                 f"word='{word['text']}', expected='{remaining_sentence_chars[:len(word_chars)]}'")
                    break
            else:
                # Word is longer than remaining sentence - this shouldn't happen
                logger.warning(f"Word longer than remaining sentence: "
                             f"word='{word['text']}', remaining='{remaining_sentence_chars}'")
                break

        if not sentence_words:
            raise SentenceMatchError(
                sentence,
                "".join(w["text"] for w in words),
                "Could not find matching word sequence"
            )

        return sentence_words, current_word_idx

    def _get_processing_log_prefix(self) -> str:
        """Get Japanese-specific log prefix."""
        return "Processing Japanese "