"""
Spanish language processing module for Mitlesen.

This module provides Spanish-specific implementations of text processing,
segmentation, and linguistic analysis following the established patterns
for German and Japanese language support.
"""

from .segmenter import SpanishSentenceSegmenter
from .transcript_processor import SpanishTranscriptProcessor
from .normalizer import normalize_spanish_text

__all__ = [
    "SpanishSentenceSegmenter",
    "SpanishTranscriptProcessor", 
    "normalize_spanish_text",
]