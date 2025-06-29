from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple


# ──────────────────────────────────────────────────────────────────────────────
# EXCEPTIONS
# ──────────────────────────────────────────────────────────────────────────────
class SentenceMatchError(Exception):
    """Raised when a sentence cannot be matched exactly in the original text."""
    def __init__(self, sentence: str, original_text: str, reason: str):
        super().__init__(
            f"Failed to match sentence '{sentence}' in text '{original_text}': "
            f"{reason}"
        )
        self.sentence = sentence
        self.original_text = original_text
        self.reason = reason

class BaseTokenizer(ABC):
    """Abstract base class for text tokenization"""

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into individual tokens"""
        pass

class BaseSegmenter(ABC):
    """Abstract base class for text segmentation using template method pattern."""

    @abstractmethod
    def segment_text(self, text: str, max_len: int = 30) -> List[str]:
        """Segment text into sentences with maximum length"""
        pass

    def segment_transcripts(self, segments: List[Dict[str, Any]], max_len: int = 30) -> List[Dict[str, Any]]:
        """
        Template method for segmenting transcript segments into smaller sentence-level segments.

        This method implements the common algorithm while delegating language-specific
        operations to abstract hook methods.
        """
        from mitlesen.logger import logger

        new_segments = []
        current_segment_id = 0

        for segment in segments:
            words = segment.get("words", [])
            if not words:
                continue

            logger.info(f"{self._get_processing_log_prefix()}segment: {segment.get('start', 0):.2f}s - {segment.get('end', 0):.2f}s")

            # Extract text using language-specific concatenation strategy
            text = self._extract_text_from_words(words)

            # Segment the text into sentences
            sentences = self.segment_text(text, max_len)
            logger.info(f"Split into {len(sentences)} sentences: {[s[:50] + '...' if len(s) > 50 else s for s in sentences]}")

            # Align words to sentences using language-specific algorithm
            current_word_idx = 0
            for sentence in sentences:
                try:
                    aligned_words, current_word_idx = self._align_words_to_sentence(
                        sentence, words, current_word_idx
                    )

                    # Create new segment with aligned words
                    new_segment = self._create_segment_from_words(
                        aligned_words, current_segment_id, segment
                    )
                    new_segments.append(new_segment)
                    current_segment_id += 1

                except SentenceMatchError as e:
                    logger.error(f"Failed to align sentence '{sentence}': {e}")
                    # Continue with next sentence to avoid breaking the entire process
                    continue

        return new_segments

    @abstractmethod
    def _extract_text_from_words(self, words: List[Dict[str, Any]]) -> str:
        """
        Extract text from word list using language-specific concatenation strategy.

        Args:
            words: List of word dictionaries with 'text' field

        Returns:
            Concatenated text string
        """
        pass

    @abstractmethod
    def _align_words_to_sentence(self, sentence: str, words: List[Dict[str, Any]], start_idx: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Align words from the original transcript to a segmented sentence using language-specific matching.

        Args:
            sentence: The sentence text to align words to
            words: List of all word dictionaries from the segment
            start_idx: Starting index in the words list

        Returns:
            Tuple of (aligned_words, next_start_idx)
        """
        pass

    @abstractmethod
    def _get_processing_log_prefix(self) -> str:
        """Get language-specific log prefix for processing messages."""
        pass

    def _create_segment_from_words(self, words: List[Dict[str, Any]], segment_id: int, original_segment: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new segment dictionary from aligned words.

        This is common logic used by all segmenters.
        """
        if not words:
            raise ValueError("Cannot create segment from empty words list")

        start_time = words[0].get("start", 0.0)
        end_time = words[-1].get("end", 0.0)
        text = "".join(word.get("text", "") for word in words).strip()

        return {
            "id": segment_id,
            "text": text,
            "start": start_time,
            "end": end_time,
            "words": words
        }

class BaseWordSplitter(ABC):
    """Abstract base class for word-level analysis and splitting"""

    @abstractmethod
    def split_sentence(self, sentence: str) -> Tuple[List[str], ...]:
        """Split sentence into words with linguistic analysis"""
        pass

class BaseTranscriptProcessor(ABC):
    """Abstract base class for language-specific transcript preprocessing"""

    @abstractmethod
    def preprocess_transcript(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Preprocess transcript with language-specific logic.

        Args:
            transcript: List of transcript segments

        Returns:
            Preprocessed transcript with linguistic annotations
        """
        pass