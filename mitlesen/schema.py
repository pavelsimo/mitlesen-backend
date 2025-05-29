from pydantic import BaseModel, RootModel
from typing import List, Optional

class Word(BaseModel):
    text: str
    start: float
    end: float
    translation: str
    type: str  # verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle
    case: str  # nominativ, akkusativ, dativ, genitiv, or empty string
    phonetic: Optional[List[str]] = None  # list of romaji for each character in Japanese words, None for other languages

class Sentence(BaseModel):
    id: int
    text: str
    translation: str
    start: float
    end: float
    words: List[Word]

class Transcript(RootModel[List[Sentence]]):
    pass 