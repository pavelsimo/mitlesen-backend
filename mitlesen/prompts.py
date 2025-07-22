"""Prompts used for AI operations in the mitlesen package."""

from typing import Dict, List
import json

# Language-specific system prompts for AI models
LANGUAGE_SYSTEM_PROMPTS: Dict[str, str] = {
    'de': "You are a precise language-processing assistant. You will receive a raw transcript from a German video.",
    'ja': "You are a professional Japanese-to-English translator specializing in natural, emotionally authentic translations, particularly for dialogue and anime-style content.",
}


def get_system_instruction(language: str) -> str:
    if language not in LANGUAGE_SYSTEM_PROMPTS:
        raise ValueError(f"Unsupported language: {language}")
    return LANGUAGE_SYSTEM_PROMPTS[language]

def get_german_transcript_prompt(sentences_json: str) -> str:
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
    return f"""
          You are a professional Japanese-to-English translator. Your goal is to provide natural, emotionally authentic translations
          that capture the true meaning and tone of Japanese dialogue, especially for anime-style content.

          # Task
          For each sentence in the input, you will provide:
          1. A natural English translation that captures the emotional intent and tone
          2. For each word within the sentence:
             - An English translation
             - Its part‑of‑speech tag (use exactly: verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle)

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

# Language-specific transcript prompt factories (defined after functions)
TRANSCRIPT_PROMPT_FACTORIES = {
    'de': get_german_transcript_prompt,
    'ja': get_japanese_transcript_prompt,
}

def aug_transcript_prompt(sentences_json: str, language: str = 'de') -> str:
    prompt_factory = TRANSCRIPT_PROMPT_FACTORIES.get(language)
    if prompt_factory is None:
        raise ValueError(f"Unsupported language for transcript prompts: {language}")
    return prompt_factory(sentences_json)