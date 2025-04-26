import json
import os.path
import time

from dotenv import load_dotenv
from ai import CompletionClient
from db import MitLesenDatabase

load_dotenv()

if __name__ == "__main__":
    DATA_FOLDER = 'data'

    videos = [
        {"youtube_id": "t0SQPbD2F08", "title": "BLUE LOCK - Folge 1", "is_premium": False},
        # {"youtube_id": "O2w9acaudd8", "title": "Shangri-La Frontier - Folge 1", "is_premium": False},
        # {"youtube_id": "CvlVuSN_twQ", "title": "JUJUTSU KAISEN - Folge 1", "is_premium": False},
    ]

    schema = """
    {
      "$schema": "http://json-schema.org/draft-07/schema#",
      "type": "object",
      "properties": {
        "id": {
          "type": "integer"
        },
        "text": {
          "type": "string"
        },
        "translation": {
          "type": "string"
        },
        "start": {
          "type": "number"
        },
        "end": {
          "type": "number"
        },
        "words": {
          "type": "array",
          "items": {
            "type": "object",
            "properties": {
              "text": {
                "type": "string"
              },
              "start": {
                "type": "number"
              },
              "end": {
                "type": "number"
              },
              "translation": {
                "type": "string"
              },
              "type": {
                "type": "string"
              },
              "case": {
                "type": "string"
              }
            },
            "required": ["text", "start", "end", "type", "case"],
            "additionalProperties": false
          }
        }
      },
      "required": ["id", "text", "translation", "start", "end", "words"],
      "additionalProperties": false
    }
    """

    db = MitLesenDatabase()

    for vid_index, video in enumerate(videos):
        youtube_id = video["youtube_id"]
        title = video["title"]
        is_premium = video["is_premium"]
        transcript_path = os.path.join(DATA_FOLDER, youtube_id + '.json')

        with open(transcript_path, 'r', encoding='utf-8') as file:
            text = file.read()
            transcript = json.loads(text)
            client = CompletionClient(backend='gemini')
            try:
                for sentence in transcript:
                    prompt = f"""
                          You will be given a JSON like the following one:                                                  
                          {{
                            "id": 0,
                            "text": "Wenn wir",
                            "start": 0.16,
                            "end": 1.48,
                            "words": [
                              {{
                                "text": "Wenn",
                                "start": 0.16,
                                "end": 1.3                                
                              }},
                              {{
                                "text": "wir",
                                "start": 1.3,
                                "end": 1.48,
                              }}
                            ]
                          }}                        
                                            
                        # Task
                        2. Your task is to add the missing translation for both sentences and words:
                           For the Sentence:
                           - An English translation.                        
                           For the Words: 
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
                        - Do not output any explanatory text—only the JSON.
                        - Do not use markdown formatting or code blocks (e.g., do not use triple backticks or any syntax highlighting).
                        - Follow this sample schema exactly: {schema}
                        - Make sure the words appears in the same order that are given in the transcript.

                        # JSON Output                          
                          {{
                            "id": 0,
                            "text": "Wenn wir",
                            "translation": "When we",
                            "start": 0.16,
                            "end": 1.48,
                            "words": [
                              {{
                                "text": "Wenn",
                                "start": 0.16,
                                "end": 1.3
                                "translation": "we",
                                "type": "pronoun",
                                "case": "nominativ"                                
                              }},
                              {{
                                "text": "wir",
                                "start": 1.3,
                                "end": 1.48,
                                "type": "pronoun",
                                "case": "nominativ"
                              }}
                            ]
                          }}                                                 
                        
                        # JSON Input
                        {sentence}
                    """
                    completion = client.complete(prompt)
                    new_sentence = json.loads(completion)
                    print(json.dumps(new_sentence, indent=2, ensure_ascii=False))
                    sentence["translation"] = new_sentence["translation"]
                    print("--")
                    for i, (t_word, v_word) in enumerate(zip(sentence["words"], new_sentence["words"])):
                        sentence["words"][i] = v_word | t_word
                    print(json.dumps(sentence, indent=2, ensure_ascii=False))
                    time.sleep(2)

                db.insert(
                    title=title,
                    youtube_id=youtube_id,
                    is_premium=is_premium,
                    transcript=json.dumps(transcript),
                )

                print(f"✅ Inserted in videos table")
            except Exception as err:
                print(f"❌ Error for {youtube_id}: {err}")

    db.close()
