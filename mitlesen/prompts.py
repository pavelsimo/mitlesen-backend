"""Prompts used for AI operations in the mitlesen package."""

from typing import Dict, List
import json

# Language-specific system prompts for AI models
LANGUAGE_SYSTEM_PROMPTS: Dict[str, str] = {
    'de': "You are a precise language-processing assistant. You will receive a raw transcript from a German video.",
    'ja': "You are a professional Japanese-to-English translator specializing in natural, emotionally authentic translations, particularly for dialogue and anime-style content.",
}

def get_system_instruction(language: str) -> str:
    """Get language-specific system instruction for the AI model.
    
    Args:
        language: Language code ('de' for German, 'ja' for Japanese)
        
    Returns:
        System instruction string appropriate for the language
        
    Raises:
        ValueError: If the language is not supported
    """
    if language not in LANGUAGE_SYSTEM_PROMPTS:
        raise ValueError(f"Unsupported language: {language}")
    return LANGUAGE_SYSTEM_PROMPTS[language]

def get_german_transcript_prompt(sentences_json: str) -> str:
    """Generate prompt for augmenting German transcript with translations and word-level information.
    
    Args:
        sentences_json: JSON string containing the sentences to process
        
    Returns:
        Formatted prompt string for the AI model
    """
    return f"""
          You will be given multiple German sentences in JSON format to translate.
          
          # Task
          Your task is to add the missing translation for both sentences and words:
           For each Sentence:
           - An English translation (natural, fluent English that preserves the original meaning)
                        
           For each Word within the sentences: 
           - An English translation
           - Its part‑of‑speech tag (use exactly: verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle)
           - If applicable (nouns and pronouns), include grammatical case (nominativ, akkusativ, dativ, genitiv)

        # Guidelines
        - For each sentence, provide a natural, fluent English translation
        - For each word, use concise, literal translations
        - Maintain grammatical accuracy in word-level information

        # Constraints
        - Only return the JSON output. Do not include any explanations, comments, or additional text.
        - Do not use markdown formatting or code blocks.
        - Make sure the words appear in the same order as given in the transcript.
        - Return an array of JSON objects, one for each input sentence.
        
        # Input JSON Array
        {sentences_json}
    """

def get_japanese_transcript_prompt(sentences_json: str) -> str:
    """Generate prompt for augmenting Japanese transcript with translations and word-level information.
    
    Args:
        sentences_json: JSON string containing the sentences to process
        
    Returns:
        Formatted prompt string for the AI model
    """
    return f"""
          You are a professional Japanese-to-English translator. Your goal is to provide natural, emotionally authentic translations 
          that capture the true meaning and tone of Japanese dialogue, especially for anime-style content.

          # Task
          For each sentence in the input, you will provide:
          1. A natural English translation that captures the emotional intent and tone
          2. For each word within the sentence:
             - An English translation
             - Its part‑of‑speech tag (use exactly: verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle)
             - Romaji (phonetic transcription) of the word

          # Translation Guidelines
          For each sentence:
          - First, understand the literal meaning
          - Consider the emotional context and speaker's intent
          - Provide a natural English translation that:
            * Maintains the emotional impact of the original
            * Uses appropriate English expressions for the context
            * Preserves the speaker's personality and tone
            * Feels natural and authentic in English
          - Prioritize emotional authenticity over literal accuracy when needed

          For each word:
          - Provide accurate romaji transcription
          - Use concise, literal translations
          - Include correct part-of-speech tags

          # Example
          Japanese: とてもプロの彼女ができてるとは思えませんし、こんな形でお題をいただくわけには...
          Natural English: "No way anyone would believe you're just pretending to be some pro girlfriend. And seriously, how can you even bring up something like this?"

          # Constraints
          - Only return the JSON output. Do not include any explanations, comments, or additional text.
          - Do not use markdown formatting or code blocks.
          - Make sure the words appear in the same order as given in the transcript.
          - Return an array of JSON objects, one for each input sentence.
          
          # Input JSON Array
          {sentences_json}
    """

def aug_transcript_prompt(sentences_json: str, language: str = 'de') -> str:
    """Generate prompt for augmenting transcript with translations and word-level information.
    
    Args:
        sentences_json: JSON string containing the sentences to process
        language: Language code ('de' for German, 'ja' for Japanese)
        
    Returns:
        Formatted prompt string for the AI model
    """
    if language == 'ja':
        return get_japanese_transcript_prompt(sentences_json)
    else:
        return get_german_transcript_prompt(sentences_json)

def jp_word_split_prompt(sentences_json: str) -> str:
    """
    Build a prompt that asks a large-language model to
      1. segment Japanese sentences into words, and
      2. output a per-word list of romaji syllables.
    The prompt is designed to prevent the most common LLM errors.
    """
    return f"""
You are a meticulous Japanese tokenizer and phonetic transcriber.

TASK
-----
For **each** sentence in the JSON array below, return a JSON object with:

  "words"     : the sentence split into words  
  "phonetics" : an array where the i-th element is an **array of romaji
                syllables** for the i-th word

Return **one valid JSON array** only — no headings, comments, code fences,
or extra keys.

STRICT OUTPUT CONTRACT
----------------------
1. Output *valid JSON* (UTF-8), never wrapped in ``` and with no trailing commas.  
2. Preserve every original character exactly as written.  
3. Skip punctuation, emoji, numbers, and symbols; they do **not** become words.

WORD-SEGMENTATION RULES
-----------------------
▪ A word is a continuous span of the original string (keep characters contiguous).  
▪ Preserve order.  
▪ Do **not** fuse particles with neighbouring words.  
▪ Treat katakana loan-words (アイロン, コーヒー, etc.) as single words.

ROMAJI RULES
------------
Romanisation scheme: **Modified Hepburn**, lower-case ASCII, *no* macrons  
(おう → "ou", えい → "ei").

**A. Kanji** — *one character → one token*  
1. Output **exactly one** romaji token **per kanji character**, even if that
   reading contains several morae or a long vowel.  
   • 本当 → ["hon", "tou"] ✅ NOT ["hon", "to", "u"] ❌  
   • 見下り → ["mi", "kuda", "ri"] ✅ NOT ["mi", "ku", "da", "ri"] ❌  
   • 話 → ["hanashi"] (single kanji, multi-mora reading)  
2. If a word contains several kanji, still obey the one-kanji-one-token rule.  
   • 電話 → ["den", "wa"]  
3. When kanji are followed by okurigana, treat the okurigana with the kana
   rules (section B).  
   • 話す → ["hana", "su"] (話 = “hana”, す = “su”)

**B. Pure kana words** — list **every kana separately**  
   • ある → ["a", "ru"]  
   • わかれた → ["wa", "ka", "re", "ta"]

**C. Digraphs, small っ/ッ, ー, ん, small vowels**  
1. **Digraphs (拗音)** – base kana + small ゃ/ゅ/ょ is *one* syllable.  
   • しょっぱい → ["sho", "p", "pa", "i"]  
2. **Geminate consonant っ/ッ** – output "xtsu" as its own token.  
   • がっこう → ["ga", "xtsu", "ko", "u"]  
3. **Prolonged-sound mark ー** – repeat the preceding vowel.  
   • コーヒー → ["ko", "o", "hi", "i"]  
4. **Syllabic ん/ン** – always its own token "n"; **never** fuse it with the
   preceding syllable, even after a digraph.  
   • ばあちゃん → ["ba", "a", "cha", "n"]  
5. **Small vowels ぁぃぅぇぉ** – merge with the preceding consonant.  
   • むずかしぃ → ["mu", "zu", "ka", "shi", "i"]

QUICK KANA→ROMAJI CHEAT-SHEET
-----------------------------
あ a   い i   う u   え e   お o  
か ka  き ki  く ku  け ke  こ ko  
さ sa  し shi す su  せ se  そ so  
た ta  ち chi つ tsu て te  と to  
な na  に ni  ぬ nu  ね ne  の no  
は ha  ひ hi  ふ fu  へ he  ほ ho  
ま ma  み mi  む mu  め me  も mo  
や ya      ゆ yu      よ yo  
ら ra  り ri  る ru  れ re  ろ ro  
わ wa      を wo  
ん n  
(Apply dakuten/handakuten normally: が ga, ぱ pa, etc.)

COMMON PITFALLS TO AVOID
------------------------
✗ Never split a single kanji reading into multiple tokens  
  ("tou" → "to","u" ✗; "kuda" → "ku","da" ✗).  
✗ Never collapse multiple kana into one romaji token ("sore" ✗).  
✗ Never split digraphs ("shi", "sho" must stay whole).  
✗ Never fuse ん/ン with the previous syllable ("chan" ✗).  
✗ Never assign readings to punctuation or emojis.  
✗ Never invent macrons or capital letters.

EXAMPLES
--------
Input: ["本当のことも切り出せず見苦しく取り付け",
        "ばあちゃんに話す",
        "地堕落なお前に愛想をつかして見下り範"]  
Output:
[
  {{
    "words": ["本当", "の", "こと", "も", "切り出せ", "ず", "見苦しく", "取り付け"],
    "phonetics": [
      ["hon", "tou"],
      ["no"],
      ["ko", "to"],
      ["mo"],
      ["ki", "ri", "da", "se"],
      ["zu"],
      ["mi", "gu", "ru", "shi", "ku"],
      ["to", "ri", "tsu", "ke"]
    ]
  }},
  {{
    "words": ["ばあちゃん", "に", "話", "す"],
    "phonetics": [
      ["ba", "a", "cha", "n"],
      ["ni"],
      ["hanashi"],
      ["su"]
    ]
  }},
  {{
    "words": ["地堕落", "な", "お前", "に", "愛想", "を", "つかし", "て", "見下り", "範"],
    "phonetics": [
      ["ji", "da", "raku"],
      ["na"],
      ["o", "mae"],
      ["ni"],
      ["ai", "so"],
      ["wo"],
      ["tsu", "ka", "shi"],
      ["te"],
      ["mi", "kuda", "ri"],
      ["han"]
    ]
  }}
]

SENTENCES
---------
{sentences_json}
""".strip()


def jp_word_split_fix_prompt(sentence: str, error_msg: str, current_words: List[str]) -> str:
    """Generate prompt for fixing word splits that failed validation.
    
    Args:
        sentence: Original Japanese sentence
        error_msg: Error message explaining what went wrong
        current_words: Current (incorrect) word splits
        
    Returns:
        Formatted prompt string for the AI model
    """
    return f"""The previous attempt to split the Japanese sentence failed validation. Please fix the word splits.

Error message: {error_msg}

Current (incorrect) word splits: {json.dumps(current_words, ensure_ascii=False)}

TASK
-----
Return a single JSON object (not an array) with:

  "words"     : the sentence split into words  
  "phonetics" : an array where the i-th element is an array of romaji syllables for the i-th word

STRICT OUTPUT CONTRACT
----------------------
1. Output *valid JSON* (UTF-8), never wrapped in ``` and with no trailing commas.  
2. Preserve every original character exactly as written.  
3. Skip punctuation, emoji, numbers, and symbols; they do **not** become words.
4. Return a single object, not an array, since this is a fix for a single sentence.

WORD-SEGMENTATION RULES
-----------------------
▪ A word is a continuous span of the original string (keep characters contiguous).  
▪ Preserve order.  
▪ Do **not** fuse particles with neighbouring words.  
▪ Treat katakana loan-words (アイロン, コーヒー, etc.) as single words.

ROMAJI RULES
------------
Romanisation scheme: **Modified Hepburn**, lower-case ASCII, *no* macrons  
(おう → "ou", えい → "ei").

**A. Kanji** — *one character → one token*  
1. Output **exactly one** romaji token **per kanji character**, even if that
   reading contains several morae or a long vowel.  
   • 本当 → ["hon", "tou"] ✅ NOT ["hon", "to", "u"] ❌  
   • 見下り → ["mi", "kuda", "ri"] ✅ NOT ["mi", "ku", "da", "ri"] ❌  
   • 話 → ["hanashi"] (single kanji, multi-mora reading)  
2. If a word contains several kanji, still obey the one-kanji-one-token rule.  
   • 電話 → ["den", "wa"]  
3. When kanji are followed by okurigana, treat the okurigana with the kana
   rules (section B).  
   • 話す → ["hana", "su"] (話 = "hana", す = "su")

**B. Pure kana words** — list **every kana separately**  
   • ある → ["a", "ru"]  
   • わかれた → ["wa", "ka", "re", "ta"]

**C. Digraphs, small っ/ッ, ー, ん, small vowels**  
1. **Digraphs (拗音)** – base kana + small ゃ/ゅ/ょ is *one* syllable.  
   • しょっぱい → ["sho", "p", "pa", "i"]  
2. **Geminate consonant っ/ッ** – output "xtsu" as its own token.  
   • がっこう → ["ga", "xtsu", "ko", "u"]  
3. **Prolonged-sound mark ー** – repeat the preceding vowel.  
   • コーヒー → ["ko", "o", "hi", "i"]  
4. **Syllabic ん/ン** – always its own token "n"; **never** fuse it with the
   preceding syllable, even after a digraph.  
   • ばあちゃん → ["ba", "a", "cha", "n"]  
5. **Small vowels ぁぃぅぇぉ** – merge with the preceding consonant.  
   • むずかしぃ → ["mu", "zu", "ka", "shi", "i"]

EXAMPLE
-------
Input: "ばあちゃんに話す"
Output:
{{
  "words": ["ばあちゃん", "に", "話", "す"],
  "phonetics": [
    ["ba", "a", "cha", "n"],
    ["ni"],
    ["hanashi"],
    ["su"]
  ]
}}

SENTENCE TO FIX
--------------
{sentence}
""".strip() 
