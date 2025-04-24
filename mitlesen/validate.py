from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field, ConfigDict

class WordType(str, Enum):
    verb = "verb"
    noun = "noun"
    pronoun = "pronoun"
    adjective = "adjective"
    adverb = "adverb"
    preposition = "preposition"
    conjunction = "conjunction"
    article = "article"
    numeral = "numeral"
    particle = "particle"

class CaseType(str, Enum):
    nominativ = "nominativ"
    akkusativ = "akkusativ"
    dativ     = "dativ"
    genitiv  = "genitiv"

class Word(BaseModel):
    id: str = Field(..., pattern=r"^[0-9]+-[0-9]+-[0-9]+$")
    text: str = Field(..., min_length=1)
    translation: str = Field(..., min_length=1)
    type: WordType
    case: Optional[CaseType] = None
    model_config = ConfigDict(extra="forbid")

class Sentence(BaseModel):
    id: str = Field(..., pattern=r"^[0-9]+-[0-9]+$")
    startTime: int = Field(..., ge=0)
    endTime:   int = Field(..., ge=0)
    text:       str = Field(..., min_length=1)
    translation:str = Field(..., min_length=1)
    words:      List[Word] = Field(..., min_length=1)
    model_config = ConfigDict(extra="forbid")

class Transcript(BaseModel):
    videoId:    str         = Field(..., min_length=1)
    sentences:  List[Sentence] = Field(..., min_length=1)
    model_config = ConfigDict(extra="forbid")

