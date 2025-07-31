"""Natural Language Processing module for mitlesen

This module provides language-specific text processing capabilities including
tokenization, segmentation, and word-level analysis.
"""

from .base import BaseTokenizer, BaseSegmenter, BaseWordSplitter, BaseTranscriptProcessor

def get_segmenter(language: str) -> BaseSegmenter:
    """Get a sentence segmenter for the specified language.

    Args:
        language: Language code ('de' for German, 'es' for Spanish, 'ja'/'jp' for Japanese)

    Returns:
        Language-specific sentence segmenter instance

    Raises:
        ValueError: If language is not supported
    """
    language = language.lower()

    if language == 'de':
        from .german.segmenter import GermanSentenceSegmenter
        return GermanSentenceSegmenter()
    elif language == 'es':
        from .spanish.segmenter import SpanishSentenceSegmenter
        return SpanishSentenceSegmenter()
    elif language in ['ja', 'jp']:
        from .japanese.segmenter import JapaneseSentenceSegmenter
        return JapaneseSentenceSegmenter()
    else:
        raise ValueError(f"Unsupported language for segmentation: {language}")

def get_word_splitter(language: str) -> BaseWordSplitter:
    """Get a word splitter for the specified language.

    Args:
        language: Language code ('ja'/'jp' for Japanese)

    Returns:
        Language-specific word splitter instance

    Raises:
        ValueError: If language is not supported
    """
    language = language.lower()

    if language in ['ja', 'jp']:
        from .japanese.tokenizer import JapaneseWordSplitter
        return JapaneseWordSplitter()
    else:
        raise ValueError(f"Unsupported language for word splitting: {language}")

def get_transcript_processor(language: str) -> BaseTranscriptProcessor:
    """Get a transcript processor for the specified language.

    Args:
        language: Language code ('de' for German, 'es' for Spanish, 'ja'/'jp' for Japanese)

    Returns:
        Language-specific transcript processor instance

    Raises:
        ValueError: If language is not supported
    """
    language = language.lower()

    if language == 'de':
        from .german.transcript_processor import GermanTranscriptProcessor
        return GermanTranscriptProcessor()
    elif language == 'es':
        from .spanish.transcript_processor import SpanishTranscriptProcessor
        return SpanishTranscriptProcessor()
    elif language in ['ja', 'jp']:
        from .japanese.transcript_processor import JapaneseTranscriptProcessor
        return JapaneseTranscriptProcessor()
    else:
        raise ValueError(f"Unsupported language for transcript processing: {language}")

def get_language_processor(language: str, processor_type: str):
    """Get a language processor instance (backward compatibility).

    Args:
        language: Language code ('de' for German, 'es' for Spanish, 'ja' for Japanese)
        processor_type: Type of processor ('segmenter', 'splitter', or 'transcript_processor')

    Returns:
        Language-specific processor instance

    Raises:
        ValueError: If language/processor combination is not supported
    """
    if processor_type == 'segmenter':
        return get_segmenter(language)
    elif processor_type == 'splitter':
        return get_word_splitter(language)
    elif processor_type == 'transcript_processor':
        return get_transcript_processor(language)
    else:
        raise ValueError(f"Unsupported processor type: {processor_type}")

__all__ = [
    'BaseTokenizer',
    'BaseSegmenter',
    'BaseWordSplitter',
    'BaseTranscriptProcessor',
    'get_segmenter',
    'get_word_splitter',
    'get_transcript_processor',
    'get_language_processor'
]