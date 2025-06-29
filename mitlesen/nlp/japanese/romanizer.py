"""Japanese romanization and kanji conversion utilities."""

import re
from jamdict import Jamdict

class JapaneseRomanizer:
    """Japanese kanji/kana conversion processor."""

    def __init__(self):
        """Initialize the romanizer with Jamdict dictionary."""
        self._jam = Jamdict()  # heavy-weight but cached for the life of the process
        self._kana_only_re = re.compile(r"^[ぁ-んゔゕゖァ-ヴー]+$")

    def kana_to_kanji(self, lemma_kana: str) -> str:
        """Return a plausible kanji representation of *lemma_kana*.

        We consult **Jamdict**; if multiple entries match, we choose the first
        available kanji form of the first hit.  If no kanji is found, the
        original kana string is returned untouched.
        """
        try:
            result = self._jam.lookup(lemma_kana)
        except Exception:
            # Any Jamdict I/O/parsing hiccup → graceful degradation.
            return lemma_kana

        if result.entries:
            entry = result.entries[0]
            if entry.kanji_forms:
                return entry.kanji_forms[0].text
        return lemma_kana

    def is_kana_only(self, text: str) -> bool:
        """Check if text contains only kana characters."""
        return bool(self._kana_only_re.match(text))