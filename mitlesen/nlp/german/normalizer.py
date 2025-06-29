"""German text normalization utilities."""

import re

def normalize_text(text: str) -> str:
    """Strip punctuation & collapse whitespace for robust comparisons.

    This function normalizes text by removing all punctuation and collapsing
    multiple whitespace characters into single spaces. Used for robust text
    matching and comparison.

    Args:
        text: The text to normalize

    Returns:
        Normalized text string
    """
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()

# Backward compatibility alias
def _normalise(text: str) -> str:
    """Legacy alias for normalize_text (British spelling)."""
    return normalize_text(text)