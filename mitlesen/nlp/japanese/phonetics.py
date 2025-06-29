"""Japanese phonetic processing utilities."""

import re
from typing import List
import jaconv
import pykakasi

class JapanesePhonetics:
    """Japanese phonetic transcription processor."""

    def __init__(self):
        """Initialize the phonetics processor with pykakasi."""
        self._kks = pykakasi.kakasi()

    def to_romaji(self, kata: str) -> List[str]:
        """Convert *kata* (katakana string) to a list of Hepburn syllables
        **aligned 1-to-1 with the corresponding hiragana characters**.

        Long-vowel mark "ー" is expanded into the preceding vowel so that
        Romaji and Hiragana stay the same length.
        """
        hira = jaconv.kata2hira(kata)
        romaji: List[str] = []

        for i, ch in enumerate(hira):
            if ch == "ー":
                # Prolong the previous vowel; default to a bare hyphen if
                # this is the first char (degenerate case).
                prev = romaji[-1] if romaji else "-"
                match = re.search(r"[aeiou]$", prev)
                romaji.append(match.group(0) if match else "-")
                continue

            # pykakasi on a single character returns a list with one dict
            ro = self._kks.convert(ch)[0]["hepburn"]
            romaji.append(ro)

        return romaji

    @staticmethod
    def to_hiragana(kata: str) -> List[str]:
        """Convert *kata* to a list of individual hiragana characters."""
        return list(jaconv.kata2hira(kata))