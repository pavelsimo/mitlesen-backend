"""Japanese text processing utilities using Janome."""

import json
import unicodedata
from typing import List, Dict, Optional, Tuple
from janome.tokenizer import Tokenizer

# Comprehensive map for all hiragana & katakana characters → one romaji token
KANA_ROMAJI = {
    # Katakana
    'ア':'a','イ':'i','ウ':'u','エ':'e','オ':'o',
    'カ':'ka','キ':'ki','ク':'ku','ケ':'ke','コ':'ko',
    'サ':'sa','シ':'shi','ス':'su','セ':'se','ソ':'so',
    'タ':'ta','チ':'chi','ツ':'tsu','テ':'te','ト':'to',
    'ナ':'na','ニ':'ni','ヌ':'nu','ネ':'ne','ノ':'no',
    'ハ':'ha','ヒ':'hi','フ':'fu','ヘ':'he','ホ':'ho',
    'マ':'ma','ミ':'mi','ム':'mu','メ':'me','モ':'mo',
    'ヤ':'ya','ユ':'yu','ヨ':'yo',
    'ラ':'ra','リ':'ri','ル':'ru','レ':'re','ロ':'ro',
    'ワ':'wa','ヲ':'wo','ン':'n',
    'ガ':'ga','ギ':'gi','グ':'gu','ゲ':'ge','ゴ':'go',
    'ザ':'za','ジ':'ji','ズ':'zu','ゼ':'ze','ゾ':'zo',
    'ダ':'da','ヂ':'ji','ヅ':'zu','デ':'de','ド':'do',
    'バ':'ba','ビ':'bi','ブ':'bu','ベ':'be','ボ':'bo',
    'パ':'pa','ピ':'pi','プ':'pu','ペ':'pe','ポ':'po',

    # Small katakana
    'ァ':'a','ィ':'i','ゥ':'u','ェ':'e','ォ':'o',
    'ャ':'ya','ュ':'yu','ョ':'yo',
    'ッ':'xtsu','ー':None,   # ー handled by "duplicate previous vowel"

    # Hiragana (same mappings)
    'あ':'a','い':'i','う':'u','え':'e','お':'o',
    'か':'ka','き':'ki','く':'ku','け':'ke','こ':'ko',
    'さ':'sa','し':'shi','す':'su','せ':'se','そ':'so',
    'た':'ta','ち':'chi','つ':'tsu','て':'te','と':'to',
    'な':'na','に':'ni','ぬ':'nu','ね':'ne','の':'no',
    'は':'ha','ひ':'hi','ふ':'fu','へ':'he','ほ':'ho',
    'ま':'ma','み':'mi','む':'mu','め':'me','も':'mo',
    'や':'ya','ゆ':'yu','よ':'yo',
    'ら':'ra','り':'ri','る':'ru','れ':'re','ろ':'ro',
    'わ':'wa','を':'wo','ん':'n',
    'ぁ':'a','ぃ':'i','ぅ':'u','ぇ':'e','ぉ':'o',
    'ゃ':'ya','ゅ':'yu','ょ':'yo',
    'っ':'xtsu',
    'が':'ga','ぎ':'gi','ぐ':'gu','げ':'ge','ご':'go',
    'ざ':'za','じ':'ji','ず':'zu','ぜ':'ze','ぞ':'zo',
    'だ':'da','ぢ':'ji','づ':'zu','で':'de','ど':'do',
    'ば':'ba','び':'bi','ぶ':'bu','べ':'be','ぼ':'bo',
    'ぱ':'pa','ぴ':'pi','ぷ':'pu','ぺ':'pe','ぽ':'po'
}

# Map for katakana to hiragana conversion
KATAKANA_TO_HIRAGANA = {
    'ア':'あ','イ':'い','ウ':'う','エ':'え','オ':'お',
    'カ':'か','キ':'き','ク':'く','ケ':'け','コ':'こ',
    'サ':'さ','シ':'し','ス':'す','セ':'せ','ソ':'そ',
    'タ':'た','チ':'ち','ツ':'つ','テ':'て','ト':'と',
    'ナ':'な','ニ':'に','ヌ':'ぬ','ネ':'ね','ノ':'の',
    'ハ':'は','ヒ':'ひ','フ':'ふ','ヘ':'へ','ホ':'ほ',
    'マ':'ま','ミ':'み','ム':'む','メ':'め','モ':'も',
    'ヤ':'や','ユ':'ゆ','ヨ':'よ',
    'ラ':'ら','リ':'り','ル':'る','レ':'れ','ロ':'ろ',
    'ワ':'わ','ヲ':'を','ン':'ん',
    'ガ':'が','ギ':'ぎ','グ':'ぐ','ゲ':'げ','ゴ':'ご',
    'ザ':'ざ','ジ':'じ','ズ':'ず','ゼ':'ぜ','ゾ':'ぞ',
    'ダ':'だ','ヂ':'ぢ','ヅ':'づ','デ':'で','ド':'ど',
    'バ':'ば','ビ':'び','ブ':'ぶ','ベ':'べ','ボ':'ぼ',
    'パ':'ぱ','ピ':'ぴ','プ':'ぷ','ペ':'ぺ','ポ':'ぽ',
    'ァ':'ぁ','ィ':'ぃ','ゥ':'ぅ','ェ':'ぇ','ォ':'ぉ',
    'ャ':'ゃ','ュ':'ゅ','ョ':'ょ','ッ':'っ','ー':'ー'
}

def is_kanji(ch: str) -> bool:
    """Check if a character is a kanji."""
    return 'CJK UNIFIED' in unicodedata.name(ch, '')

def is_special_char(ch: str) -> bool:
    """Check if a character is a special character (punctuation, symbol, number)."""
    cat = unicodedata.category(ch)[0]
    return cat in ('P', 'S', 'N')

def split_kana_reading(reading: str) -> List[str]:
    """
    Break a Katakana string into per-character units,
    treating small-kana and sokuon/long-mark as separate.
    """
    return list(reading)

def katakana_to_hiragana(text: str) -> str:
    """Convert katakana to hiragana."""
    result = []
    for char in text:
        result.append(KATAKANA_TO_HIRAGANA.get(char, char))
    return ''.join(result)

class JapaneseWordSplitter:
    """Japanese word splitting and phonetic transcription using Janome."""
    
    def __init__(self):
        """Initialize the word splitter with Janome tokenizer."""
        self.tokenizer = Tokenizer()  # Janome pure-python tokenizer
    
    def split_sentence(self, sentence: str) -> Tuple[List[str], List[List[str]], List[List[str]]]:
        """
        Split a Japanese sentence into words and their phonetic transcriptions.
        
        Args:
            sentence: Japanese sentence to process
            
        Returns:
            Tuple of (list of words, list of romaji phonetic units for each word, list of hiragana phonetic units for each word)
        """
        words = []
        romaji_phonetics = []
        hiragana_phonetics = []
        
        for token in self.tokenizer.tokenize(sentence):
            # Skip pure symbols/punctuation
            if token.part_of_speech.startswith("記号"):
                continue
                
            surface = token.surface
            words.append(surface)
            
            # Use Janome's reading if available, otherwise use surface form
            kana_reading = token.reading if token.reading != "*" else surface
            
            # Break reading into per-character units
            kana_units = split_kana_reading(kana_reading)
            
            # Map each unit to romaji tokens and hiragana
            romaji_tokens = []
            hiragana_tokens = []
            
            if token.reading == "*":
                # Fallback: always split surface into chars and map each
                for unit in list(surface):
                    rom = KANA_ROMAJI.get(unit)
                    if rom is not None:
                        romaji_tokens.append(rom)
                        hiragana_tokens.append(katakana_to_hiragana(unit))
                    elif is_kanji(unit):
                        romaji_tokens.append(unit)
                        hiragana_tokens.append(unit)
                    else:
                        romaji_tokens.append("")
                        hiragana_tokens.append("")
            else:
                for idx, unit in enumerate(kana_units):
                    if unit == 'ー':
                        # Duplicate the last vowel of the previous romaji token
                        if romaji_tokens:
                            prev = romaji_tokens[-1]
                            romaji_tokens.append(prev[-1])
                            hiragana_tokens.append('ー')
                    else:
                        rom = KANA_ROMAJI.get(unit)
                        if rom is not None:
                            romaji_tokens.append(rom)
                            hiragana_tokens.append(katakana_to_hiragana(unit))
                        else:
                            romaji_tokens.append("")
                            hiragana_tokens.append("")
            
            romaji_phonetics.append(romaji_tokens)
            hiragana_phonetics.append(hiragana_tokens)
            
        return words, romaji_phonetics, hiragana_phonetics
    
    def split_sentences(self, sentences: List[str]) -> List[Dict[str, List]]:
        """
        Split multiple Japanese sentences into words and their phonetic transcriptions.
        
        Args:
            sentences: List of Japanese sentences to process
            
        Returns:
            List of dicts with "words", "phonetic_romaji" and "phonetic_hiragana" for each sentence
        """
        output = []
        for sentence in sentences:
            words, romaji_phonetics, hiragana_phonetics = self.split_sentence(sentence)
            output.append({
                "words": words,
                "phonetic_romaji": romaji_phonetics,
                "phonetic_hiragana": hiragana_phonetics
            })
        return output
    
    def split_sentences_json(self, sentences_json: str) -> str:
        """
        Process a JSON array of Japanese sentences.
        
        Args:
            sentences_json: JSON string containing array of Japanese sentences
            
        Returns:
            JSON string containing array of objects with "words", "phonetic_romaji" and "phonetic_hiragana"
        """
        sentences = json.loads(sentences_json)
        result = self.split_sentences(sentences)
        return json.dumps(result, ensure_ascii=False, indent=2) 