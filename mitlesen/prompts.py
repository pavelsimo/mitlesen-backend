"""Prompts used for AI operations in the mitlesen package."""

def aug_transcript_prompt(sentences_json: str) -> str:
    """Generate prompt for augmenting transcript with translations and word-level information.
    
    Args:
        sentences_json: JSON string containing the sentences to process
        
    Returns:
        Formatted prompt string for the AI model
    """
    return f"""
          You will be given multiple sentences in JSON format to translate.
          
          # Task
          Your task is to add the missing translation for both sentences and words:
           For each Sentence:
           - An English translation.                        
           For each Word within the sentences: 
           - An English translation.
           - Its part‑of‑speech tag (use exactly: verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle).
           - If applicable (German nouns and pronouns), include grammatical case (nominativ, akkusativ, dativ, genitiv).

        # Guidelines
        - For each sentence, include its translation
           - non-literal translation, natural sounding english translation 
        - For each word, 
           - include its text, translation, and grammatical information.
           - use concise, literal translations.

        # Constraints
        - Only return the JSON output. Do not include any explanations, comments, or additional text.
        - Do not use markdown formatting or code blocks.
        - Make sure the words appear in the same order that are given in the transcript.
        - Return an array of JSON objects, one for each input sentence.
        
        # Input JSON Array
        {sentences_json}
    """ 