from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple

class BaseTokenizer(ABC):
    """Abstract base class for text tokenization"""

    @abstractmethod
    def tokenize(self, text: str) -> List[str]:
        """Tokenize text into individual tokens"""
        pass

class BaseSegmenter(ABC):
    """Abstract base class for text segmentation"""

    @abstractmethod
    def segment_text(self, text: str, max_len: int = 30) -> List[str]:
        """Segment text into sentences with maximum length"""
        pass

    @abstractmethod
    def segment_transcripts(self, segments: List[Dict[str, Any]], max_len: int = 30) -> List[Dict[str, Any]]:
        """Segment transcript segments into smaller sentence-level segments"""
        pass

class BaseWordSplitter(ABC):
    """Abstract base class for word-level analysis and splitting"""

    @abstractmethod
    def split_sentence(self, sentence: str) -> Tuple[List[str], ...]:
        """Split sentence into words with linguistic analysis"""
        pass