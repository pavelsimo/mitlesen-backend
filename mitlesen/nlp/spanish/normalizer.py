"""Spanish text normalization utilities."""

import re
import unicodedata

def normalize_spanish_text(text: str) -> str:
    """
    Normalize Spanish text for robust comparisons.

    This function normalizes Spanish text by:
    - Removing punctuation (including Spanish-specific ¿¡)
    - Normalizing accented characters (optional - preserves original accents by default)
    - Collapsing multiple whitespace characters into single spaces
    - Converting to lowercase for case-insensitive matching

    Used for robust text matching and comparison in transcript alignment.

    Args:
        text: The Spanish text to normalize

    Returns:
        Normalized text string
    """
    # Convert to lowercase for case-insensitive matching
    text = text.lower()
    
    # Remove all punctuation including Spanish-specific characters (¿¡)
    # Keep accented characters intact for proper Spanish matching
    text = re.sub(r"[^\w\sáéíóúñü]", "", text)
    
    # Collapse multiple whitespace into single spaces
    text = re.sub(r"\s+", " ", text)
    
    return text.strip()

def remove_spanish_accents(text: str) -> str:
    """
    Remove Spanish accents from text for fallback matching.
    
    Converts accented characters to their base forms:
    á → a, é → e, í → i, ó → o, ú → u, ñ → n, ü → u
    
    This is useful for fallback matching when accent differences
    might cause alignment issues.
    
    Args:
        text: Spanish text with potential accents
        
    Returns:
        Text with Spanish accents removed
    """
    # Manual mapping for Spanish characters to preserve ñ → n specifically
    accent_map = {
        'á': 'a', 'é': 'e', 'í': 'i', 'ó': 'o', 'ú': 'u',
        'ñ': 'n', 'ü': 'u',
        'Á': 'A', 'É': 'E', 'Í': 'I', 'Ó': 'O', 'Ú': 'U', 
        'Ñ': 'N', 'Ü': 'U'
    }
    
    for accented, base in accent_map.items():
        text = text.replace(accented, base)
    
    return text

def normalize_spanish_text_strict(text: str) -> str:
    """
    Strict normalization that removes accents for very robust matching.
    
    This is a more aggressive normalization that removes accents entirely.
    Use this for fallback matching when standard normalization fails.
    
    Args:
        text: The Spanish text to normalize
        
    Returns:
        Strictly normalized text string
    """
    # Start with standard normalization
    text = normalize_spanish_text(text)
    
    # Additionally remove accents for very robust matching
    text = remove_spanish_accents(text)
    
    return text

# Legacy compatibility functions
def normalize_text(text: str) -> str:
    """Legacy alias for normalize_spanish_text."""
    return normalize_spanish_text(text)