import argparse
import json
import os
import whisper_timestamped as wts


def transcribe(audio_path: str, model_name: str = "openai/whisper-large-v3", device: str = "cpu") -> str:
    audio = wts.load_audio(audio_path)
    model = wts.load_model(model_name)
    transcript = wts.transcribe(
        model,
        audio,
        temperature=0,
        beam_size=5,
        best_of=5,
        language="de",

    )

    """
    EXAMPLE OUTPUT: 
    
    [
      {
        "id": 1,
        "text": " Wenn wir gewinnen, geht's zur Meisterschaft!",
        "start": 28.04,
        "end": 29.84,
        "words": [
          {
            "text": "Wenn",
            "start": 28.04,
            "end": 28.18
          },
          {
            "text": "wir",
            "start": 28.18,
            "end": 28.32
          },
          {
            "text": "gewinnen,",
            "start": 28.32,
            "end": 28.72
          },
          {
            "text": "geht's",
            "start": 28.96,
            "end": 29.18
          },
          {
            "text": "zur",
            "start": 29.18,
            "end": 29.28
          },
          {
            "text": "Meisterschaft!",
            "start": 29.28,
            "end": 29.84
          }
        ]
      },
      {
        "id": 2,
        "text": " Das ist unsere Chance, Isagi, enttäusch uns nicht!",
        "start": 30.5,
        "end": 33.34,
        "words": [
          {
            "text": "Das",
            "start": 30.5,
            "end": 30.74
          },
          {
            "text": "ist",
            "start": 30.74,
            "end": 30.76
          },
          {
            "text": "unsere",
            "start": 30.76,
            "end": 31.14
          },
          {
            "text": "Chance,",
            "start": 31.14,
            "end": 32.0
          },
          {
            "text": "Isagi,",
            "start": 32.0,
            "end": 32.2
          },
          {
            "text": "enttäusch",
            "start": 33.28,
            "end": 33.3
          },
          {
            "text": "uns",
            "start": 33.3,
            "end": 33.32
          },
          {
            "text": "nicht!",
            "start": 33.32,
            "end": 33.34
          }
        ]
      },
      ...
    ]
    """
    res = []
    for seg in transcript.get('segments', []):
        res.append({
            'id': seg['id'],
            'text': seg['text'],
            'start': seg['start'],
            'end': seg['end'],
            'words': [
                {
                    'text': w['text'],
                    'start': w['start'],
                    'end': w['end']
                }
                for w in seg.get('words', [])
            ]
        })

    # 8. Return JSON string
    return json.dumps(res, indent=2, ensure_ascii=False)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(
        description="Transcribe a German audio file with sentence- and word-level timestamps."
    )
    parser.add_argument("audio", help="Path to input audio file (wav/mp3/etc.)")
    parser.add_argument("--model", default="small",
                        help="Whisper model to use (tiny, base, small, medium, large)")
    parser.add_argument("--device", default="cpu",
                        help="Device for inference (cpu or cuda)")
    parser.add_argument("--output-json",
                        help="Path to save the transcription JSON (defaults to <audio_basename>.json)")
    args = parser.parse_args()

    # run transcription
    transcription = transcribe(
        audio_path=args.audio,
        model_name=args.model,
        device=args.device
    )

    # determine output path
    if args.output_json:
        out_path = args.output_json
    else:
        base, _ = os.path.splitext(args.audio)
        out_path = base + ".json"

    # write to file
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    print(f"Transcription saved to {out_path}")