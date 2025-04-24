#!/usr/bin/env python3

import multiprocessing as mp
import os
import argparse

# Buzz model loader & downloader
from buzz.model_loader import (
    TranscriptionModel, ModelType, WhisperModelSize, ModelDownloader
)
# Task definitions and helpers
from buzz.transcriber.transcriber import (
    TranscriptionOptions, FileTranscriptionOptions,
    FileTranscriptionTask, Task, OutputFormat,
    get_output_file_path
)
# Core transcription engine
from buzz.transcriber.whisper_file_transcriber import WhisperFileTranscriber
# Output writer (.txt/.srt)
from buzz.transcriber.file_transcriber import write_output

def transcribe_with_buzz(
    audio_path: str,
    huggingface_model_id: str,
    output_dir: str | None = None
) -> None:
    # 1. Download & cache model
    model = TranscriptionModel(
        model_type=ModelType.HUGGING_FACE,
        whisper_model_size=WhisperModelSize.CUSTOM,
        hugging_face_model_id=huggingface_model_id
    )
    ModelDownloader(model).run()
    model_path = model.get_local_model_path()
    if model_path is None:
        raise RuntimeError("Failed to download or locate model")

    # 2. Configure transcription options
    transcription_opts = TranscriptionOptions(
        language="de",
        task=Task.TRANSCRIBE,
        model=model,
        word_level_timings=True
    )
    file_opts = FileTranscriptionOptions(
        file_paths=[audio_path],
        output_formats={OutputFormat.TXT, OutputFormat.SRT}
    )

    # 3. Build transcription task
    task = FileTranscriptionTask(
        transcription_options=transcription_opts,
        file_transcription_options=file_opts,
        model_path=model_path,
        source=FileTranscriptionTask.Source.FILE_IMPORT,
        file_path=audio_path,
        output_directory=output_dir
    )

    # 4. Run transcription
    transcriber = WhisperFileTranscriber(task)
    segments = transcriber.transcribe()

    # 5. Write outputs
    for fmt in file_opts.output_formats:
        out_path = get_output_file_path(
            file_path=audio_path,
            task=Task.TRANSCRIBE,
            language=transcription_opts.language,
            model=model,
            output_format=fmt,
            output_directory=output_dir
        )
        write_output(path=out_path, segments=segments, output_format=fmt)
        print(f"Written {fmt.value.upper()} → {out_path}")

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio.mp3 using Buzz + Whisper-v3-turbo"
    )
    parser.add_argument(
        "audio_path", help="Path to your input .mp3 file (e.g. audio.mp3)"
    )
    parser.add_argument(
        "--model-id",
        default="openai/whisper-large-v3-turbo",
        help="Hugging Face model ID"
    )
    parser.add_argument(
        "--out-dir",
        default=None,
        help="Directory to save .txt and .srt outputs"
    )
    args = parser.parse_args()

    transcribe_with_buzz(
        audio_path=args.audio_path,
        huggingface_model_id=args.model_id,
        output_dir=args.out_dir
    )

if __name__ == "__main__":
    # Ensure CUDA contexts aren’t inherited via fork—use spawn instead :contentReference[oaicite:9]{index=9}
    mp.set_start_method("spawn", force=True)
    main()
