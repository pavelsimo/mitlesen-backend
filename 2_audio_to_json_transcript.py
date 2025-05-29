import argparse
import json
import os
import whisperx

from mitlesen.logger import logger

# IMPORTANT: cudnn libs
# export LD_LIBRARY_PATH=/home/ubuntu/.virtualenvs/mitlesen-backend/lib/python3.12/site-packages/nvidia/cudnn/lib/

def transcribe(
    audio_path: str,
    model_name: str = "large-v2",
    device: str = "cpu",
    language: str = "de",
) -> str:

    # load audio & Whisper model
    audio = whisperx.load_audio(audio_path)
    compute_type = "float16" if device.startswith("cuda") else "float32"
    model = whisperx.load_model(model_name, device, compute_type=compute_type, language=language)
    # pick a custom aligner for Japanese
    if language.lower() == "ja":
        result = model.transcribe(audio, batch_size=4, chunk_size=6)
        align_model_name = "jonatasgrosman/wav2vec2-large-xlsr-53-japanese"
    else:
        result = model.transcribe(audio, batch_size=4, chunk_size=30)
        align_model_name = None  # use WhisperX default

    # load the align model (custom or default)
    align_model, metadata = whisperx.load_align_model(
        model_name=align_model_name,
        language_code=language,
        device=device
    )

    # forced alignment
    aligned = whisperx.align(
        result["segments"],
        align_model,
        metadata,
        audio,
        device=device,
        return_char_alignments=False,
    )

    # build word-level JSON
    segments = []
    for idx, seg in enumerate(aligned["segments"]):
        words = []
        for w in seg["words"]:
            start, end = w.get("start", None), w.get("end", None)
            if start is not None and end is not None:
                words.append({
                    "text": w["word"],
                    "start": start,
                    "end": end,
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
        help="Language code for transcription (e.g., 'de' for German, 'ja' for Japanese)",
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
    logger.info(transcription)

    # Determine output path
    out_path = args.output_json or os.path.splitext(args.audio)[0] + ".json"

    # Write to file
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(transcription)

    logger.info(f"Transcription saved to {out_path}")
