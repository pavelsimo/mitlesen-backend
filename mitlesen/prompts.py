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


def jp_word_split_prompt(sentences_json: str, error_msg: str = None, current_words: List[str] = None) -> str:
    """
    Build a prompt that asks a large-language model to
      1. segment Japanese sentences into words, and
      2. output a per-word list of romaji syllables.
    The prompt is designed to prevent the most common LLM errors.
    
    Args:
        sentences_json: JSON string containing the sentences to process
        error_msg: Optional error message from previous attempt
        current_words: Optional list of current (incorrect) word splits
    """
    error_guidance = ""
    if error_msg:
        error_guidance = f"""
PREVIOUS ATTEMPT FAILED
----------------------
Error message:
{error_msg}

Current (incorrect) word splits: {json.dumps(current_words, ensure_ascii=False) if current_words else "None"}

Please fix the above errors while following all the rules below. Pay special attention to:
1. Ensure each kanji character gets exactly one phonetic unit
2. For words with okurigana, keep the kanji reading as one unit and the okurigana as separate units
3. Never split kanji readings into multiple units
4. Never combine multiple kanji readings into one unit

"""

    return f"""
You are a meticulous Japanese tokenizer and phonetic transcriber.

{error_guidance}TASK
-----
For **each** sentence in the JSON array below, return a JSON object with:

  "words"     : the sentence split into words  
  "phonetics" : an array where the i-th element is an **array of romaji
                syllables** for the i-th word

Return **one valid JSON array** only — no headings, comments, code fences,
or extra keys.

────────────────────────────────────────────────────────
ALGORITHM  – apply these steps to **every word**
────────────────────────────────────────────────────────
1. Read the word character-by-character, left → right.
2. If the character is **kanji**  
     • Look up that single kanji's reading.  
     • Emit **one** romaji token that contains the entire reading  
       (multi-mora readings stay whole: 何 → "nani", 話 → "hanashi").  
3. If the character is **kana**  
     • Emit **one** romaji token using the mapping table (section B).  
     • Special cases  
         っ / ッ → xtsu    small ゃゅょぁぃぅぇぉ → ya/yu/yo/a/i/u/e/o  
         ー → duplicate previous vowel    ん / ン → n  
4. Ignore punctuation, emoji, symbols, and numbers (they never become words or get phonetic units).
5. Continue until the end of the word, preserving order.

────────────────────────────────────────────────────────
ABSOLUTE CONTRACT – must hold for **every word**
────────────────────────────────────────────────────────
• **One-char-one-token**   token count == character count (excluding special characters).  
• Never merge ("tachi", "ja", "deki", "hitori"), split ("na"+"ni"),
  drop, duplicate, reorder, or output placeholders.
• Numbers, punctuation, and symbols are ignored and get no phonetic units.

────────────────────────────────────────────────────────
WORD SEGMENTATION RULES
────────────────────────────────────────────────────────
• A *word* is a contiguous span of the original sentence.  
• Do **not** fuse particles with neighbours.  
• Katakana loan-words (アイロン, コーヒー, イケメン …) stay whole.

────────────────────────────────────────────────────────
A. KANJI — **one kanji ⇒ one token**
────────────────────────────────────────────────────────
              ✅ correct                    ❌ wrong
    何        ["nani"]                 ["na","ni"]
    話        ["hanashi"]              ["hana","shi"]
    出来      ["de","ki"]              ["deki"]
    上出来    ["jou","de","ki"]        ["jou","deki"]
    一人      ["hito","ri"]            ["hitori"]

If kanji are followed by okurigana, output kanji token(s) plus one token
per kana:  使い方 → ["tsuka","i","kata"] 話す → ["hana","su"]

────────────────────────────────────────────────────────
B. KANA — **one kana ⇒ one token**
────────────────────────────────────────────────────────
Canonical mapping (use **only** these spellings):

    あ a   い i   う u   え e   お o
    か ka  き ki  く ku  け ke  こ ko        が ga ぎ gi ぐ gu げ ge ご go
    さ sa  し shi す su  せ se  そ so        ざ za じ ji ず zu ぜ ze ぞ zo
    た ta  ち chi つ tsu て te  と to        だ da ぢ ji* づ zu* で de ど do
    な na  に ni  ぬ nu  ね ne  の no
    は ha  ひ hi  ふ fu  へ he  ほ ho        ば ba び bi ぶ bu べ be ぼ bo   ぱ pa ぴ pi ぷ pu ぺ pe ぽ po
    ま ma  み mi  む mu  め me  も mo
    や ya          ゆ yu          よ yo
    ら ra  り ri  る ru  れ re  ろ ro
    わ wa                    を wo
    ん n
    small ゃ ya  ゅ yu  ょ yo  ぁ a  ぃ i  ぅ u  ぇ e  ぉ o
    っ / ッ xtsu         ー duplicate previous vowel

*ぢ / づ are rare; map them to **ji / zu**.

Counter-examples  
    わけ      → ["wa","ke"]      (not "wake")  
    じゃ      → ["ji","ya"]      (not "ja")  
    しっかりと → ["shi","xtsu","ka","ri","to"]

────────────────────────────────────────────────────────
C. SELF-CHECK – run **before** replying
────────────────────────────────────────────────────────
□ token count == character count for every word  
□ no fused tokens ("ja", "tachi", "deki", "hitori")  
□ no missing small kana, っ, ン, final い, or kanji  
□ all tokens are lower-case ASCII; no macrons (ō), caps, or "X"  
□ output is **one** valid JSON array, nothing else

────────────────────────────────────────────────────────
D. EXAMPLES – imitate the format exactly
────────────────────────────────────────────────────────
    じゃない      → ["ji","ya","na","i"]
    しっかりと    → ["shi","xtsu","ka","ri","to"]
    出来          → ["de","ki"]
    上出来        → ["jou","de","ki"]
    何            → ["nani"]
    僕たち        → ["boku","ta","chi"]

────────────────────────────────────────────────────────
INPUT SENTENCES – process **exactly** these
────────────────────────────────────────────────────────
{sentences_json}
""".strip()


def jp_word_split_prompt(sentences_json: str, error_msg: str = None, current_words: List[str] = None) -> str:
    """
    Build a prompt that asks a large-language model to
      1. segment Japanese sentences into words, and
      2. output a per-word list of romaji syllables.
    The prompt is designed to prevent the most common LLM errors.
    
    Args:
        sentences_json: JSON string containing the sentences to process
        error_msg: Optional error message from previous attempt
        current_words: Optional list of current (incorrect) word splits
    """
    error_guidance = ""
    if error_msg:
        error_guidance = f"""
PREVIOUS ATTEMPT FAILED
----------------------
Error message:
{error_msg}

Current (incorrect) word splits: {json.dumps(current_words, ensure_ascii=False) if current_words else "None"}

Please fix the above errors while following all the rules below. Pay special attention to:
1. Ensure each kanji character gets exactly one phonetic unit
2. For words with okurigana, keep the kanji reading as one unit and the okurigana as separate units
3. Never split kanji readings into multiple units
4. Never combine multiple kanji readings into one unit

"""

    return f"""
You are a meticulous Japanese tokenizer and phonetic transcriber.

{error_guidance}TASK
-----
For **each** sentence in the JSON array below, return a JSON object with:

  "words"     : the sentence split into words  
  "phonetics" : an array where the i-th element is an **array of romaji
                syllables** for the i-th word

Return **one valid JSON array** only — no headings, comments, code fences,
or extra keys.

────────────────────────────────────────────────────────
ALGORITHM  – apply these steps to **every word**
────────────────────────────────────────────────────────
1. Read the word character-by-character, left → right.
2. If the character is **kanji**  
     • Look up that single kanji's reading.  
     • Emit **one** romaji token that contains the entire reading  
       (multi-mora readings stay whole: 何 → "nani", 話 → "hanashi").  
3. If the character is **kana**  
     • Emit **one** romaji token using the mapping table (section B).  
     • Special cases  
         っ / ッ → xtsu    small ゃゅょぁぃぅぇぉ → ya/yu/yo/a/i/u/e/o  
         ー → duplicate previous vowel    ん / ン → n  
4. Ignore punctuation, emoji, symbols, and numbers (they never become words or get phonetic units).
5. Continue until the end of the word, preserving order.

────────────────────────────────────────────────────────
ABSOLUTE CONTRACT – must hold for **every word**
────────────────────────────────────────────────────────
• **One-char-one-token**   token count == character count (excluding special characters).  
• Never merge ("tachi", "ja", "deki", "hitori"), split ("na"+"ni"),
  drop, duplicate, reorder, or output placeholders.
• Numbers, punctuation, and symbols are ignored and get no phonetic units.

────────────────────────────────────────────────────────
WORD SEGMENTATION RULES
────────────────────────────────────────────────────────
• A *word* is a contiguous span of the original sentence.  
• Do **not** fuse particles with neighbours.  
• Katakana loan-words (アイロン, コーヒー, イケメン …) stay whole.

────────────────────────────────────────────────────────
A. KANJI — **one kanji ⇒ one token**
────────────────────────────────────────────────────────
              ✅ correct                    ❌ wrong
    何        ["nani"]                 ["na","ni"]
    話        ["hanashi"]              ["hana","shi"]
    出来      ["de","ki"]              ["deki"]
    上出来    ["jou","de","ki"]        ["jou","deki"]
    一人      ["hito","ri"]            ["hitori"]

If kanji are followed by okurigana, output kanji token(s) plus one token
per kana:  使い方 → ["tsuka","i","kata"] 話す → ["hana","su"]

────────────────────────────────────────────────────────
B. KANA — **one kana ⇒ one token**
────────────────────────────────────────────────────────
Canonical mapping (use **only** these spellings):

    あ a   い i   う u   え e   お o
    か ka  き ki  く ku  け ke  こ ko        が ga ぎ gi ぐ gu げ ge ご go
    さ sa  し shi す su  せ se  そ so        ざ za じ ji ず zu ぜ ze ぞ zo
    た ta  ち chi つ tsu て te  と to        だ da ぢ ji* づ zu* で de ど do
    な na  に ni  ぬ nu  ね ne  の no
    は ha  ひ hi  ふ fu  へ he  ほ ho        ば ba び bi ぶ bu べ be ぼ bo   ぱ pa ぴ pi ぷ pu ぺ pe ぽ po
    ま ma  み mi  む mu  め me  も mo
    や ya          ゆ yu          よ yo
    ら ra  り ri  る ru  れ re  ろ ro
    わ wa                    を wo
    ん n
    small ゃ ya  ゅ yu  ょ yo  ぁ a  ぃ i  ぅ u  ぇ e  ぉ o
    っ / ッ xtsu         ー duplicate previous vowel

*ぢ / づ are rare; map them to **ji / zu**.

Counter-examples  
    わけ      → ["wa","ke"]      (not "wake")  
    じゃ      → ["ji","ya"]      (not "ja")  
    しっかりと → ["shi","xtsu","ka","ri","to"]

────────────────────────────────────────────────────────
C. SELF-CHECK – run **before** replying
────────────────────────────────────────────────────────
□ token count == character count for every word  
□ no fused tokens ("ja", "tachi", "deki", "hitori")  
□ no missing small kana, っ, ン, final い, or kanji  
□ all tokens are lower-case ASCII; no macrons (ō), caps, or "X"  
□ output is **one** valid JSON array, nothing else

────────────────────────────────────────────────────────
D. EXAMPLES – imitate the format exactly
────────────────────────────────────────────────────────
    じゃない      → ["ji","ya","na","i"]
    しっかりと    → ["shi","xtsu","ka","ri","to"]
    出来          → ["de","ki"]
    上出来        → ["jou","de","ki"]
    何            → ["nani"]
    僕たち        → ["boku","ta","chi"]

────────────────────────────────────────────────────────
INPUT SENTENCES – process **exactly** these
────────────────────────────────────────────────────────
{sentences_json}
""".strip() 
