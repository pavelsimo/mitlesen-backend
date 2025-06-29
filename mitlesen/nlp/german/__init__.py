"""German language processing module."""

from .normalizer import normalize_text, _normalise

# Import heavy dependencies only when needed
def get_segmenter():
    """Get German sentence segmenter (lazy import to avoid spacy dependency)."""
    from .segmenter import GermanSentenceSegmenter, SentenceMatchError
    return GermanSentenceSegmenter, SentenceMatchError

__all__ = [
    'normalize_text',
    '_normalise',
    'get_segmenter'
]