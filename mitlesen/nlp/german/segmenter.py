"""German sentence segmentation using spaCy."""

import spacy
import re
from typing import List, Dict, Any, Tuple
from mitlesen.logger import logger
from mitlesen.nlp.base import BaseSegmenter, SentenceMatchError
from .normalizer import normalize_text

class GermanSentenceSegmenter(BaseSegmenter):
    """German sentence segmenter using spaCy for natural language processing."""

    def __init__(self):
        """Initialize the German segmenter with spaCy model."""
        # ──────────────────────────────────────────────────────────────────────────────
        # INITIALISATION
        # ──────────────────────────────────────────────────────────────────────────────
        try:
            self.nlp = spacy.load("de_core_news_sm")
        except OSError:
            logger.warning("German spaCy model not found. Downloading …")
            spacy.cli.download("de_core_news_sm")
            self.nlp = spacy.load("de_core_news_sm")

        # make absolutely sure a sentence‐boundary detector is in place
        if "sentencizer" not in self.nlp.pipe_names and "senter" not in self.nlp.pipe_names:
            self.nlp.add_pipe("sentencizer", first=True)

    def split_long_sentence(self, sent: spacy.tokens.Span, max_len: int = 100) -> List[str]:
        """
        Break *one* spaCy sentence into shorter chunks *without* losing any original
        spaces or punctuation.
        – Walk token-by-token, accumulating `token.text_with_ws`.
        – As soon as the running chunk exceeds `max_len`, split **after the last
          comma/semicolon/colon** seen inside that chunk.  If none is present,
          split immediately before the token that caused the overflow.

        The algorithm therefore produces chunks that are 100 % subsequences of the
        original token stream, so later word-level alignment can never fail.
        """
        text = sent.text.strip()
        if len(text) <= max_len:
            return [text]

        tokens = [tok.text_with_ws for tok in sent]
        chunks: List[str] = []

        current: List[str] = []
        current_len = 0
        last_punct_pos = None                      # position of last "safe" split

        def flush(upto: int | None = None) -> None:
            """Emit current[:upto] and keep the rest for the next round."""
            nonlocal current, current_len, last_punct_pos
            if upto is None:
                upto = len(current)
            chunk = "".join(current[:upto]).strip()
            if chunk:
                chunks.append(chunk)
            current = current[upto:]
            current_len = sum(len(tok) for tok in current)
            # update punctuation memory for what remains
            last_punct_pos = None
            for idx, tok in enumerate(current):
                if tok.strip() and tok.strip()[-1] in ",;:":
                    last_punct_pos = idx

        for tok in tokens:
            current.append(tok)
            current_len += len(tok)

            if tok.strip() and tok.strip()[-1] in ",;:":
                last_punct_pos = len(current) - 1

            if current_len > max_len:
                # prefer the last punctuation position, *unless* the overflow token
                # itself *is* that punctuation – in that case we include it
                split_at = (
                    last_punct_pos + 1
                    if last_punct_pos is not None and last_punct_pos != len(current) - 1
                    else len(current) - 1
                )
                flush(split_at)

        flush()                                    # emit whatever is still in buffer
        return chunks

    def segment_text(self, text: str, max_len: int = 60) -> List[str]:
        """
        Use spaCy for coarse sentence segmentation and `split_long_sentence`
        for further, length-bound splitting.
        """
        doc = self.nlp(text)
        sentences: List[str] = []
        for sent in doc.sents:
            sentences.extend(self.split_long_sentence(sent, max_len=max_len))
        return sentences

    def _extract_text_from_words(self, words: List[Dict[str, Any]]) -> str:
        """Extract text using German space-separated concatenation."""
        return " ".join(w["text"] for w in words)

    def _align_words_to_sentence(self, sentence: str, words: List[Dict[str, Any]], start_idx: int) -> Tuple[List[Dict[str, Any]], int]:
        """
        Align words to sentence using German normalization-based matching.
        
        Uses normalize_text() for fuzzy matching to handle spacing and punctuation differences.
        """
        target_norm = normalize_text(sentence)
        sentence_start_idx = None

        # Locate sentence start
        for i in range(start_idx, len(words)):
            if normalize_text(" ".join(w["text"] for w in words[i:])).startswith(target_norm):
                sentence_start_idx = i
                break

        if sentence_start_idx is None:
            raise SentenceMatchError(
                sentence, 
                " ".join(w["text"] for w in words), 
                "Could not locate sentence start"
            )

        # Walk tokens until we hit the exact sentence
        sentence_words = []
        running_norm = ""

        for j in range(sentence_start_idx, len(words)):
            word = words[j]["text"]
            running_norm = normalize_text((running_norm + " " + word).strip())
            
            if running_norm == target_norm:
                sentence_words = words[sentence_start_idx : j + 1]
                return sentence_words, j + 1
                
            if len(running_norm) > len(target_norm):
                raise SentenceMatchError(
                    sentence,
                    " ".join(w["text"] for w in words),
                    f"Ran past target while matching (got '{running_norm}' vs '{target_norm}')",
                )

        raise SentenceMatchError(
            sentence, 
            " ".join(w["text"] for w in words), 
            "Could not find matching word sequence"
        )

    def _get_processing_log_prefix(self) -> str:
        """Get German-specific log prefix."""
        return "Processing "