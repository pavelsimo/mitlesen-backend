import json
import os
from openai import OpenAI
from google import genai
from dotenv import load_dotenv

load_dotenv()

BACKEND = 'gemini' # openai, gemini
transcript_schema = {
    "type": "object",
    "properties": {
        "videoId": {
            "type": "string",
            "minLength": 1
        },
        "sentences": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[0-9]+-[0-9]+$"
                    },
                    "startTime": {
                        "type": "integer",
                        "minimum": 0
                    },
                    "endTime": {
                        "type": "integer",
                        "minimum": 0
                    },
                    "text": {
                        "type": "string",
                        "minLength": 1
                    },
                    "translation": {
                        "type": "string",
                        "minLength": 1
                    }
                },
                "required": [
                    "id", "startTime", "endTime", "text", "translation"
                ],
                "additionalProperties": False
            }
        }
    },
    "required": ["videoId", "sentences"],
    "additionalProperties": False
}

vocabulary_schema = {
    "type": "object",
    "properties": {
        "videoId": {
            "type": "string",
            "minLength": 1
        },
        "words": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "pattern": "^[0-9]+-[0-9]+-[0-9]+$"
                    },
                    "sentenceId": {
                        "type": "string",
                        "pattern": "^[0-9]+-[0-9]+$"
                    },
                    "text": {
                        "type": "string",
                        "minLength": 1
                    },
                    "translation": {
                        "type": "string",
                        "minLength": 1
                    },
                    "type": {
                        "type": "string",
                        "enum": [
                            "verb", "noun", "pronoun", "adjective",
                            "adverb", "preposition", "conjunction",
                            "article", "numeral", "particle"
                        ]
                    },
                    "case": {
                        "type": "string",
                        "enum": ["nominativ", "akkusativ", "dativ", "genitiv"]
                    }
                },
                "required": ["id", "sentenceId", "text", "translation", "type"],
                "additionalProperties": False
            }
        }
    },
    "required": ["videoId", "words"],
    "additionalProperties": False
}


def fetch_completion(prompt: str) -> str:

    if BACKEND == 'openai':
        client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        completion = client.chat.completions.create(
            model="gpt-4o-mini",
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You are a precise language‑processing assistant. You will receive a raw transcript from a German video, containing timestamp markers and caption fragments."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
        )
        response_content = completion.choices[0].message.content
        return response_content
    elif BACKEND == 'gemini':
        client = genai.Client(api_key=os.getenv("GEMINI_KEY"))
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=prompt,
            config = {
                'response_mime_type': 'application/json',
            },
        )
        return response.text
    return ''

def fetch_transcript(video_id: str, transcript: str, max_retries: int = 4) -> str | None:
    # Extract timestamp and text information from the raw transcript
    timestamp_data = []
    for line in transcript.strip().split('\n'):
        if line and '[' in line and ']' in line:
            time_str = line[line.find('[')+1:line.find(']')]
            text = line[line.find(']')+1:].strip()
            
            # Convert HH:MM:SS to seconds
            time_parts = time_str.split(':')
            if len(time_parts) == 3:  # HH:MM:SS
                seconds = int(time_parts[0]) * 3600 + int(time_parts[1]) * 60 + int(time_parts[2])
            elif len(time_parts) == 2:  # MM:SS
                seconds = int(time_parts[0]) * 60 + int(time_parts[1])
            else:
                seconds = int(time_parts[0])
                
            timestamp_data.append({"timestamp": seconds, "text": text})
    
    # Calculate end times (end time is the start time of the next segment, or +5 seconds for the last one)
    for i in range(len(timestamp_data) - 1):
        timestamp_data[i]["end_time"] = timestamp_data[i + 1]["timestamp"]
    if timestamp_data:
        timestamp_data[-1]["end_time"] = timestamp_data[-1]["timestamp"] + 5
    
    # Prepare prompt with timestamp information
    timestamp_info = json.dumps(timestamp_data)
    transcript_schema_text = json.dumps(transcript_schema)
    prompt_template = f"""
        # Task
        1. For each resulting sentence:
           a. Provide an English translation.
        
        # Guidelines
        - Preserve the order and content of the transcript exactly.
        - Use the exact timestamps provided in the timestamp_data.
        - Use concise, literal translations.
        - Output valid JSON matching the schema below.
        - Fix any spelling discrepancies in the transcribed German text.
        - Only add necessary punctuation such as periods, commas, and capitalization, and use only the context provided.

        # Constraints
        - Do not output any explanatory text—only the JSON.
        - Follow this sample schema exactly: {transcript_schema_text}
        - Use the exact original timestamps provided in the transcript.
        
        # Timestamp Data (IMPORTANT: Use these exact timestamps in your response)
        {timestamp_info}
        
        # Sample Output
        {{
          "videoId": "{video_id}",
          "sentences": [
            {{
              "id": "1-1",
              "startTime": 27,
              "endTime": 31,
              "text": "Wenn wir gewinnen, geht's zur Meisterschaft.",
              "translation": "If we win, we'll go to the championship."
            }},
            …
          ]
        }}
        
        # Transcript        
        {transcript}
    """

    print(prompt_template)

    for attempt in range(max_retries):
        response = fetch_completion(prompt_template)

        try:
            json.loads(response)
            return response
        except json.JSONDecodeError as e:
            error_msg = str(e)
            print(f"[Attempt {attempt+1}] JSON parsing failed:\n{error_msg}\nResponse:\n{response}")

            # Regenerate the prompt by including the bad JSON and error message
            prompt_template = f"""
                # ERROR CORRECTION
                The following output could not be parsed as JSON. Please correct it and return ONLY valid JSON.
                
                # Error
                {error_msg}
                
                # Invalid Output
                {response}
                
                # Constraints
                - Return only corrected JSON. No explanatory text.
            """

    return None

def process_vocabulary(video_id: str, sentences: list, max_retries: int = 4) -> str | None:
    """
    Process vocabulary for the sentences.
    
    Args:
        video_id: YouTube video ID
        sentences: List of sentences from the transcript
        max_retries: Number of retries for API calls
        
    Returns:
        JSON string with vocabulary data
    """
    vocabulary_schema_text = json.dumps(vocabulary_schema)
    sentences_json = json.dumps(sentences)
    
    prompt_template = f"""
        # Task
        For each sentence in the transcript:
        1. Break the sentence into words or tokens.
        2. For each word/token, supply:
           • The original word text.
           • An English translation.
           • Its part‑of‑speech tag (use exactly: verb, noun, pronoun, adjective, adverb, preposition, conjunction, article, numeral, particle).
           • If applicable (German nouns and pronouns), include grammatical case (nominativ, akkusativ, dativ, genitiv).
        
        # Guidelines
        - Make sure each word has a reference to its original sentence via sentenceId.
        - For each word, include its text, translation, and grammatical information.
        - Use concise, literal translations.
        
        # Constraints
        - Do not output any explanatory text—only the JSON.
        - Follow this sample schema exactly: {vocabulary_schema_text}
        
        # Sample Output
        {{
          "videoId": "{video_id}",
          "words": [
            {{ 
              "id": "1-1-1", 
              "sentenceId": "1-1",
              "text": "Wenn", 
              "translation": "If", 
              "type": "conjunction" 
            }},
            {{ 
              "id": "1-1-2", 
              "sentenceId": "1-1",
              "text": "wir", 
              "translation": "we", 
              "type": "pronoun", 
              "case": "nominativ" 
            }},
            …
          ]
        }}
        
        # Sentences
        {sentences_json}
    """

    for attempt in range(max_retries):
        response = fetch_completion(prompt_template)

        try:
            json.loads(response)
            return response
        except json.JSONDecodeError as e:
            error_msg = str(e)
            print(f"[Attempt {attempt+1}] Vocabulary JSON parsing failed:\n{error_msg}\nResponse:\n{response}")

            # Regenerate the prompt by including the bad JSON and error message
            prompt_template = f"""
                # ERROR CORRECTION
                The following output could not be parsed as JSON. Please correct it and return ONLY valid JSON.
                
                # Error
                {error_msg}
                
                # Invalid Output
                {response}
                
                # Constraints
                - Return only corrected JSON. No explanatory text.
            """

    return None

def improve_transcript(video_id: str, raw_transcript: str) -> str:
    """
    Improves the transcript by detecting complete sentences, combining lines, and fixing grammar.
    
    Args:
        video_id: YouTube video ID
        raw_transcript: Raw transcript with timestamps
        
    Returns:
        Improved transcript with properly formed sentences
    """
    # Step 1: Detect sentence ranges
    ranges = detect_sentence_ranges(raw_transcript)
    
    # Step 2: Combine lines based on ranges
    combined_transcript = combine_transcript_lines(raw_transcript, ranges)
    
    # Step 3: Improve grammar
    improved_transcript = fix_grammar(combined_transcript)
    
    # Step 4: Return the improved transcript (reprocessing with chunks happens in main.py)
    return improved_transcript

def detect_sentence_ranges(transcript: str) -> list:
    """
    Sends transcript to LLM to detect ranges of lines that form complete sentences.
    
    Args:
        transcript: Raw transcript with timestamps
        
    Returns:
        List of line ranges (e.g., [[0], [1,2], [3], ...])
    """
    prompt = f"""
    # Task
    Analyze the following transcript and return a JSON array of arrays, where each inner array 
    contains the indices of lines that should be combined to form complete sentences.
    
    # Guidelines
    - Line indices start from 0
    - Group lines that form part of the same sentence together
    - Sound effects or music in square brackets should be separate entries
    - Return only the JSON array, nothing else
    
    # Example
    For this transcript:
    ```
    [0:00:21] [Applause]  
    [0:00:27] if we win, we go to the  
    [0:00:29] championship  
    [0:00:31] [Music]  
    ```
    
    Return:
    ```
    [[0], [1, 2], [3]]
    ```
    
    # Transcript
    ```
    {transcript}
    ```
    """
    
    for attempt in range(3):
        response = fetch_completion(prompt)
        try:
            # The response might contain markdown formatting, so we need to extract just the JSON
            if "```" in response:
                response = response[response.find("["):response.rfind("]")+1]
            return json.loads(response)
        except json.JSONDecodeError:
            print(f"[Attempt {attempt+1}] Failed to parse JSON response: {response}")
    
    # If all attempts fail, return a default that treats each line as its own sentence
    return [[i] for i in range(len(transcript.strip().split('\n')))]

def combine_transcript_lines(transcript: str, ranges: list) -> str:
    """
    Combines transcript lines based on the provided ranges.
    
    Args:
        transcript: Raw transcript with timestamps
        ranges: List of line ranges to combine
        
    Returns:
        Combined transcript with adjusted timestamps
    """
    lines = [line.strip() for line in transcript.strip().split('\n') if line.strip()]
    combined_lines = []
    
    for range_group in ranges:
        if not range_group or max(range_group) >= len(lines):
            continue
            
        # Extract first and last timestamps
        first_line = lines[range_group[0]]
        last_line = lines[range_group[-1]]
        
        # Extract timestamp from first line
        start_time = first_line[first_line.find('[')+1:first_line.find(']')]
        
        # Combine the text content
        combined_text = ""
        for idx in range_group:
            line = lines[idx]
            text = line[line.find(']')+1:].strip()
            combined_text += " " + text if combined_text else text
        
        # Create combined line
        combined_line = f"[{start_time}] {combined_text.strip()}"
        combined_lines.append(combined_line)
    
    return "\n".join(combined_lines)

def fix_grammar(transcript: str) -> str:
    """
    Improves grammar and fixes incomplete phrases in the transcript.
    
    Args:
        transcript: Combined transcript with timestamps
        
    Returns:
        Transcript with improved grammar
    """
    prompt = f"""
    # Task
    Fix grammar errors and incomplete phrases in the following transcript, keeping the timestamp format intact.
    
    # Guidelines
    - Fix grammar and complete incomplete sentences
    - Maintain the original meaning
    - Substitute square brackets like [Applaus], [Musik] with matching emojis
    - Return a transcript with fixed grammar, preserving all timestamps
    
    # Transcript
    ```
    {transcript}
    ```
    """
    
    for attempt in range(3):
        response = fetch_completion(prompt)
        try:
            # Strip any markdown code blocks if present
            if "```" in response:
                response = response[response.find("```")+3:response.rfind("```")]
            
            # Validate that each line still has a timestamp
            lines = response.strip().split('\n')
            valid = all(line.strip()[0] == '[' for line in lines if line.strip())
            
            if valid:
                return response.strip()
            else:
                print(f"[Attempt {attempt+1}] Response does not preserve timestamps: {response}")
        except Exception as e:
            print(f"[Attempt {attempt+1}] Error processing response: {e}")
    
    # If all attempts fail, return the original transcript
    return transcript
