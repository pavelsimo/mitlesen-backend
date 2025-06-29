"""Natural Language Processing module for mitlesen

This module provides language-specific text processing capabilities including
tokenization, segmentation, and word-level analysis.
"""

from .base import BaseTokenizer, BaseSegmenter, BaseWordSplitter

def get_segmenter(language: str) -> BaseSegmenter:
    """Get a sentence segmenter for the specified language.

    Args:
        language: Language code ('de' for German, 'ja'/'jp' for Japanese)

    Returns:
        Language-specific sentence segmenter instance

    Raises:
        ValueError: If language is not supported
    """
    language = language.lower()

    if language == 'de':
        from .german.segmenter import GermanSentenceSegmenter
        return GermanSentenceSegmenter()
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

def get_language_processor(language: str, processor_type: str):
    """Get a language processor instance (backward compatibility).

    Args:
        language: Language code ('de' for German, 'ja' for Japanese)
        processor_type: Type of processor ('segmenter' or 'splitter')

    Returns:
        Language-specific processor instance

    Raises:
        ValueError: If language/processor combination is not supported
    """
    if processor_type == 'segmenter':
        return get_segmenter(language)
    elif processor_type == 'splitter':
        return get_word_splitter(language)
    else:
        raise ValueError(f"Unsupported processor type: {processor_type}")

__all__ = [
    'BaseTokenizer',
    'BaseSegmenter',
    'BaseWordSplitter',
    'get_segmenter',
    'get_word_splitter',
    'get_language_processor'
]