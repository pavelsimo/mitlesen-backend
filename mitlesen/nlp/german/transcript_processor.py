import re
from typing import List, Dict, Any
from mitlesen.nlp.base import BaseTranscriptProcessor
from mitlesen.dictionary import SqliteDictionary
from mitlesen import DICTIONARIES_DIR


class GermanTranscriptProcessor(BaseTranscriptProcessor):
    """German-specific transcript preprocessing"""

    def preprocess_transcript(self, transcript: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Preprocess German transcript with dictionary lookups and linguistic analysis.
        
        Args:
            transcript: List of transcript segments
            
        Returns:
            Preprocessed transcript with German linguistic annotations
        """
        dict_path = DICTIONARIES_DIR + '/output/dictionary.sqlite'
        dictionary = SqliteDictionary(dict_path)
        
        try:
            for segment in transcript:
                if 'words' in segment:
                    for word in segment['words']:
                        text = word.get('text', '')
                        # Remove any non-German text symbols except spaces (keep only letters, umlauts, ß, and spaces)
                        cleaned_text = re.sub(r'[^a-zA-ZäöüÄÖÜß ]', '', text)
                        cleaned_text = cleaned_text.lower()
                        lemma = word.get('base_form') or cleaned_text
                        pos = word.get('pos')
                        
                        if lemma:
                            entries = dictionary.search_by_lemma(lemma.lower(), lang='de')
                            entry = None
                            
                            # Try to find entry matching POS tag
                            for e in entries:
                                if e.get('pos') == pos:
                                    entry = e
                                    break
                            
                            # Fallback: use first entry if no POS match
                            if not entry and entries:
                                entry = entries[0]
                            
                            if entry:
                                word['id'] = entry['id']
        finally:
            dictionary.close()
            
        return transcript