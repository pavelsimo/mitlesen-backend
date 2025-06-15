import spacy
import re
from typing import List, Dict, Any
from mitlesen.logger import logger

# ──────────────────────────────────────────────────────────────────────────────
# INITIALISATION
# ──────────────────────────────────────────────────────────────────────────────
try:
    nlp = spacy.load("de_core_news_sm")
except OSError:
    logger.warning("German spaCy model not found. Downloading …")
    spacy.cli.download("de_core_news_sm")
    nlp = spacy.load("de_core_news_sm")

# make absolutely sure a sentence‐boundary detector is in place
if "sentencizer" not in nlp.pipe_names and "senter" not in nlp.pipe_names:
    nlp.add_pipe("sentencizer", first=True)


# ──────────────────────────────────────────────────────────────────────────────
# EXCEPTIONS
# ──────────────────────────────────────────────────────────────────────────────
class SentenceMatchError(Exception):
    """Raised when a sentence cannot be matched exactly in the original text."""
    def __init__(self, sentence: str, original_text: str, reason: str):
        super().__init__(
            f"Failed to match sentence '{sentence}' in text '{original_text}': "
            f"{reason}"
        )
        self.sentence = sentence
        self.original_text = original_text
        self.reason = reason


# ──────────────────────────────────────────────────────────────────────────────
# HELPER FUNCTIONS
# ──────────────────────────────────────────────────────────────────────────────
def _normalise(text: str) -> str:
    """Strip punctuation & collapse whitespace for robust comparisons."""
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


# ──────────────────────────────────────────────────────────────────────────────
# SENTENCE-SPLITTING LOGIC
# ──────────────────────────────────────────────────────────────────────────────
def split_long_sentence(sent: spacy.tokens.Span, max_len: int = 100) -> List[str]:
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


def split_german_text_into_sentences(text: str, max_len: int = 60) -> List[str]:
    """
    Use spaCy for coarse sentence segmentation and `split_long_sentence`
    for further, length-bound splitting.
    """
    doc = nlp(text)
    sentences: List[str] = []
    for sent in doc.sents:
        sentences.extend(split_long_sentence(sent, max_len=max_len))
    return sentences


# ──────────────────────────────────────────────────────────────────────────────
# MAIN SEGMENT-SPLITTING PIPELINE
# ──────────────────────────────────────────────────────────────────────────────
def split_german_segments(
    segments: List[Dict[str, Any]],
    max_len: int = 60,
) -> List[Dict[str, Any]]:
    """
    Take whisper-like `segments` (each with a *words* list) and cut them into
    smaller sentence-level segments whose *word* sub-lists line up exactly with
    the emitted sentences.
    """
    new_segments: List[Dict[str, Any]] = []
    current_segment_id = 0

    for segment in segments:
        words = segment["words"]
        text = " ".join(w["text"] for w in words)

        logger.info(f"\nProcessing segment: '{text}'")
        sentences = split_german_text_into_sentences(text, max_len=max_len)
        logger.info(f"Split into sentences: {sentences}")

        current_word_idx = 0
        for sentence in sentences:
            target_norm = _normalise(sentence)
            start_idx = None

            # locate sentence start
            for i in range(current_word_idx, len(words)):
                if _normalise(" ".join(w["text"] for w in words[i:])).startswith(
                    target_norm
                ):
                    start_idx = i
                    break

            if start_idx is None:
                raise SentenceMatchError(
                    sentence, text, "Could not locate sentence start"
                )

            # walk tokens until we hit the *exact* sentence
            sentence_words = []
            running_norm = ""

            for j in range(start_idx, len(words)):
                word = words[j]["text"]
                running_norm = _normalise(
                    (running_norm + " " + word).strip()
                )
                if running_norm == target_norm:
                    sentence_words = words[start_idx : j + 1]
                    current_word_idx = j + 1
                    break
                if len(running_norm) > len(target_norm):
                    raise SentenceMatchError(
                        sentence,
                        text,
                        f"Ran past target while matching "
                        f"(got '{running_norm}' vs '{target_norm}')",
                    )

            if not sentence_words:
                raise SentenceMatchError(
                    sentence, text, "Could not find matching word sequence"
                )

            new_segments.append(
                {
                    "id": current_segment_id,
                    "text": sentence,
                    "start": sentence_words[0]["start"],
                    "end": sentence_words[-1]["end"],
                    "words": sentence_words,
                }
            )
            current_segment_id += 1

    return new_segments


def get_german_segmenter():
    """Get a callable for splitting German segments (for migration compatibility)."""
    return split_german_segments
