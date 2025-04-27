import argparse
import json
import os
import whisperx


# export LD_LIBRARY_PATH=/home/ubuntu/.virtualenvs/mitlesen-backend/lib/python3.12/site-packages/nvidia/cudnn/lib/
def transcribe(
    audio_path: str,
    model_name: str = "large-v2",
    device: str = "cpu",
    language: str = "de",
) -> str:

    audio = whisperx.load_audio(audio_path)
    compute_type = "float16" if device.startswith("cuda") else "float32"
    batch_size = 6
    print('compute_type=', compute_type)
    model = whisperx.load_model(model_name, device, compute_type=compute_type, language=language)
    result = model.transcribe(audio, batch_size=batch_size)


    align_model, metadata = whisperx.load_align_model(
        language_code=language,
        device=device
    )
    print(metadata)

    aligned = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device=device,
        return_char_alignments=False,
    )

    segments = []
    print(json.dumps(aligned, indent=2))
    for idx, seg in enumerate(aligned["segments"]):
        words = []
        for w in seg["words"]:
            print(w)
            w_start = w.get("start", -1)
            w_end = w.get("end", -1)
            if w_start == -1 or w_end == -1:
                pass
            else:
                words.append({
                    "text": w["word"],
                    "start": w_start,
                    "end": w_end,
                })
        segments.append({
            "id": idx,
            "text": seg["text"],
            "start": seg["start"],
            "end": seg["end"],
            "words": words,
        })

    return json.dumps(segments, indent=2, ensure_ascii=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transcribe an audio file with WhisperX and output word-level timestamps as JSON."
    )
    parser.add_argument(
        "audio",
        help="Path to input audio file (wav/mp3/etc.)",
    )
    parser.add_argument(
        "--model",
        default="large-v3",
        help="Whisper model to use (e.g., large-v2, large-v3)",
    )
    parser.add_argument(
        "--device",
        default="cpu",
        help="Device for inference (cpu or cuda)",
    )
    parser.add_argument(
        "--language",
        default="de",
        help="Language code for transcription (e.g., 'de' for German)",
    )
    parser.add_argument(
        "--output-json",
        help="Path to save the transcription JSON (defaults to <audio_basename>.json)",
    )
    args = parser.parse_args()

    # Run transcription
    transcription = transcribe(
        audio_path=args.audio,
        model_name=args.model,
        device=args.device,
        language=args.language,
    )

    # Determine output path
    if args.output_json:
        out_path = args.output_json
    else:
        base, _ = os.path.splitext(args.audio)
        out_path = base + ".json"

    # Write to file
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    print(f"Transcription saved to {out_path}")
