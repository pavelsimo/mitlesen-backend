from pydantic import BaseModel, RootModel
from typing import List, Optional

class Word(BaseModel):
    text: str
    translation: str
    type: str  # verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle
    case: str  # nominativ, akkusativ, dativ, genitiv, or empty string
    romanji: Optional[List[str]] = None  # list of romaji for each character in Japanese words, None for other languages
    hiragana: Optional[List[str]] = None  # list of hiragana for each character in Japanese words, None for other languages

class Sentence(BaseModel):
    id: int
    text: str
    translation: str
    words: List[Word]

class Transcript(RootModel[List[Sentence]]):
    pass