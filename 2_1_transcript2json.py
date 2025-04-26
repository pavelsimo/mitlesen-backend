import argparse
import json
import os
import whisper_timestamped as wts

def transcribe(audio_path: str, model_name: str = "large-v3", device: str = "cpu") -> str:
    audio = wts.load_audio(audio_path)
    model = wts.load_model(model_name)
    # try:
    #     model.to(device)
    # except AttributeError:
    #     pass
    result = wts.transcribe(
        model,
        audio,
        temperature=(0.0, 0.2, 0.4, 0.6, 0.8, 1.0),
        beam_size=5,
        best_of=5,
        language="de"
    )
    return json.dumps(clean_whisper_output(result), indent=2, ensure_ascii=False)


def clean_whisper_output(data):
    cleaned = []
    for seg in data.get('segments', []):
        cleaned.append({
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
    return cleaned


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