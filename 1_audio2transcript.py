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

    # 2. Prepare file options (we only need TXT once, and SRT twice)
    file_opts = FileTranscriptionOptions(
        file_paths=[audio_path],
        output_formats={OutputFormat.TXT, OutputFormat.SRT}
    )

    # 3. First pass: with word-level timings
    opts_with = TranscriptionOptions(
        language="de",
        task=Task.TRANSCRIBE,
        model=model,
        word_level_timings=True
    )
    task_with = FileTranscriptionTask(
        transcription_options=opts_with,
        file_transcription_options=file_opts,
        model_path=model_path,
        source=FileTranscriptionTask.Source.FILE_IMPORT,
        file_path=audio_path,
        output_directory=output_dir
    )
    segments_with = WhisperFileTranscriber(task_with).transcribe()

    # 4. Second pass: without word-level timings
    opts_without = TranscriptionOptions(
        language="de",
        task=Task.TRANSCRIBE,
        model=model,
        word_level_timings=False
    )
    task_without = FileTranscriptionTask(
        transcription_options=opts_without,
        file_transcription_options=file_opts,
        model_path=model_path,
        source=FileTranscriptionTask.Source.FILE_IMPORT,
        file_path=audio_path,
        output_directory=output_dir
    )
    segments_without = WhisperFileTranscriber(task_without).transcribe()

    # 5. Write TXT (only once, from the first pass)
    txt_path = get_output_file_path(
        file_path=audio_path,
        task=Task.TRANSCRIBE,
        language=opts_with.language,
        model=model,
        output_format=OutputFormat.TXT,
        output_directory=output_dir
    )
    write_output(path=txt_path, segments=segments_with, output_format=OutputFormat.TXT)
    print(f"Written TXT → {txt_path}")

    # 6. Write SRTs
    base_srt = get_output_file_path(
        file_path=audio_path,
        task=Task.TRANSCRIBE,
        language=opts_with.language,
        model=model,
        output_format=OutputFormat.SRT,
        output_directory=output_dir
    )
    # with word timings
    srt_with = base_srt.replace(".srt", "_with_word_timings.srt")
    write_output(path=srt_with, segments=segments_with, output_format=OutputFormat.SRT)
    print(f"Written SRT with word timings → {srt_with}")

    # without word timings
    srt_without = base_srt.replace(".srt", "_without_word_timings.srt")
    write_output(path=srt_without, segments=segments_without, output_format=OutputFormat.SRT)
    print(f"Written SRT without word timings → {srt_without}")

def main():
    parser = argparse.ArgumentParser(
        description="Transcribe audio using Buzz + Whisper-v3-turbo"
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
        help="Directory to save outputs"
    )
    args = parser.parse_args()

    transcribe_with_buzz(
        audio_path=args.audio_path,
        huggingface_model_id=args.model_id,
        output_dir=args.out_dir
    )

if __name__ == "__main__":
    # Ensure CUDA contexts aren’t inherited via fork—use spawn instead
    mp.set_start_method("spawn", force=True)
    main()
