from __future__ import annotations

import json
import re
from typing import List, Dict, Tuple

from janome.tokenizer import Tokenizer
import pykakasi
import jaconv
from jamdict import Jamdict
from mitlesen.dictionary import canonicalise_pos

# Mapping from Janome Japanese POS tags to canonical English tags
JANOME_POS_MAP = {
    "名詞": "noun",
    "動詞": "verb",
    "形容詞": "adjective",
    "副詞": "adverb",
    "連体詞": "adjective",  # prenominal adjective
    "接続詞": "conjunction",
    "感動詞": "interjection",
    "助詞": "particle",
    "助動詞": "auxiliary",
    "記号": "symbol",
    "フィラー": "filler",
    "その他": "other",
    "接頭詞": "prefix",
    "名詞,代名詞": "pronoun",
}

class JapaneseWordSplitter:
    """High-accuracy word splitter with phonetic transcription
    and multiple lemma representations (kana/kanji)."""

    _tokenizer = Tokenizer()
    _kks = pykakasi.kakasi()
    _jam = Jamdict()  # heavy-weight but cached for the life of the process

    @classmethod
    def _to_romaji(cls, kata: str) -> List[str]:
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
            ro = cls._kks.convert(ch)[0]["hepburn"]
            romaji.append(ro)

        return romaji

    @staticmethod
    def _to_hiragana(kata: str) -> List[str]:
        """Convert *kata* to a list of individual hiragana characters."""
        return list(jaconv.kata2hira(kata))

    _kana_only_re = re.compile(r"^[ぁ-んゔゕゖァ-ヴー]+$")

    @classmethod
    def _kana_to_kanji(cls, lemma_kana: str) -> str:
        """Return a plausible kanji representation of *lemma_kana*.

        We consult **Jamdict**; if multiple entries match, we choose the first
        available kanji form of the first hit.  If no kanji is found, the
        original kana string is returned untouched.
        """

        try:
            result = cls._jam.lookup(lemma_kana)
        except Exception:
            # Any Jamdict I/O/parsing hiccup → graceful degradation.
            return lemma_kana

        if result.entries:
            entry = result.entries[0]
            if entry.kanji_forms:
                return entry.kanji_forms[0].text
        return lemma_kana

    # ---------------------------------------------------------------------
    # ――― public API -------------------------------------------------------
    # ---------------------------------------------------------------------

    def split_sentence(
        self, sentence: str
    ) -> Tuple[
        List[str],
        List[str],
        List[str],
        List[List[str]],
        List[List[str]],
        List[str],
    ]:
        """Tokenise *sentence* and return six parallel arrays.

        Returns
        -------
        words : list[str]
            Surface forms as they appear in the input text.
        lemmas : list[str]
            Dictionary (base) forms in kana/kanji as provided by *Janome*.
        lemma_kanji : list[str]
            Kanji-only representation (best-effort) looked up via *Jamdict*.
        phonetic_romaji : list[list[str]]
            **Romaji syllables for each word, one per hiragana character.**
        phonetic_hiragana : list[list[str]]
            Hiragana syllables for each word (one character each).
        pos : list[str]
            Normalized part-of-speech for each word.
        """

        words: List[str] = []
        lemmas: List[str] = []
        lemmas_kanji: List[str] = []
        romaji_phonetics: List[List[str]] = []
        hiragana_phonetics: List[List[str]] = []
        pos_tags: List[str] = []

        for token in self._tokenizer.tokenize(sentence, wakati=False):
            # Skip punctuation marks (Janome tags them as 記号, "symbols").
            if token.part_of_speech.startswith("記号"):
                continue

            surface = token.surface
            lemma_raw = (
                token.base_form if token.base_form != "*" else surface
            )
            reading_kata = (
                token.reading if token.reading != "*" else surface
            )

            # POS normalization (prefer Janome's Japanese tag mapping)
            pos_fields = token.part_of_speech.split(',')
            janome_pos = pos_fields[0].strip()
            # Special case: pronoun
            if janome_pos == "名詞" and len(pos_fields) > 1 and pos_fields[1].strip() == "代名詞":
                pos_norm = "pronoun"
            else:
                # Try full field match first (e.g., "名詞,代名詞")
                full_pos = ','.join(pos_fields[:2]).strip()
                pos_norm = JANOME_POS_MAP.get(full_pos)
                if not pos_norm:
                    pos_norm = JANOME_POS_MAP.get(janome_pos)
                if not pos_norm:
                    # fallback to canonicalise_pos for non-Japanese tags
                    pos_norm, _ = canonicalise_pos(janome_pos)
            pos_tags.append(pos_norm)

            # ------------------------------------------------------------------
            # Build lists ------------------------------------------------------
            # ------------------------------------------------------------------
            words.append(surface)
            lemmas.append(lemma_raw)

            # If lemma is pure kana, consult Jamdict for a kanji form.
            if self._kana_only_re.match(lemma_raw):
                lemma_kanji = self._kana_to_kanji(lemma_raw)
            else:
                lemma_kanji = lemma_raw
            lemmas_kanji.append(lemma_kanji)

            hiragana_chars = self._to_hiragana(reading_kata)
            romaji_chars = self._to_romaji(reading_kata)

            # Safety check: keep them aligned in case of exotic edge cases
            if len(hiragana_chars) != len(romaji_chars):
                # Fallback: regenerate using pykakasi in bulk
                romaji_chars = [
                    frag["hepburn"] for frag in self._kks.convert(reading_kata)
                ]

            hiragana_phonetics.append(hiragana_chars)
            romaji_phonetics.append(romaji_chars)

        return (
            words,
            lemmas,
            lemmas_kanji,
            romaji_phonetics,
            hiragana_phonetics,
            pos_tags,
        )

    def split_sentences(self, sentences: List[str]) -> List[Dict[str, List]]:
        results: List[Dict[str, List]] = []
        for sent in sentences:
            w, l, lk, r, h, p = self.split_sentence(sent)
            results.append(
                {
                    "words": w,
                    "lemmas": l,
                    "lemma_kanji": lk,
                    "phonetic_romaji": r,
                    "phonetic_hiragana": h,
                    "pos": p,
                }
            )
        return results

    def split_sentences_json(self, sentences_json: str) -> str:
        sentences = json.loads(sentences_json)
        enriched = self.split_sentences(sentences)
        return json.dumps(enriched, ensure_ascii=False, indent=2)


# -------------------------------------------------------------------------
# ――― demo ----------------------------------------------------------------
# -------------------------------------------------------------------------

if __name__ == "__main__":
    splitter = JapaneseWordSplitter()

    sample = "私たちもそのあたりでトレーニングしてる"
    (
        words,
        lemmas,
        lemmas_kanji,
        romaji,
        hiragana,
        pos_tags,
    ) = splitter.split_sentence(sample)

    print("Surface :", words)
    print("Lemmas  :", lemmas)
    print("Lemmas⚡ :", lemmas_kanji)
    print("Romaji  :", romaji)
    print("Hiragana:", hiragana)
    print("POS     :", pos_tags)
