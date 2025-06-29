import json
import whisperx

from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from mitlesen.nlp import get_segmenter

class TranscribeStep(PipelineStep):
    def __init__(self, name: str, model_name: str = "large-v2", device: str = "cuda"):
        super().__init__(name)
        self.model_name = model_name
        self.device = device

    def execute(self, context: PipelineContext) -> bool:
        logger.info(f"🔊 Starting transcription for {context.youtube_id}")
        if context.transcript_path.exists():
            logger.warning(f"⚠️ Transcript already exists: {context.transcript_path}")
            return self.run_next(context)
        try:
            audio = whisperx.load_audio(str(context.audio_path))
            compute_type = "float16" if self.device.startswith("cuda") else "float32"
            model = whisperx.load_model(
                self.model_name,
                self.device,
                compute_type=compute_type,
                language=context.language
            )
            if context.language.lower() == "ja":
                result = model.transcribe(audio, batch_size=batch_size, chunk_size=6)
                align_model_name = "jonatasgrosman/wav2vec2-large-xlsr-53-japanese"
            else:
                result = model.transcribe(audio, batch_size=batch_size, chunk_size=30)
                align_model_name = None
            align_model, metadata = whisperx.load_align_model(
                model_name=align_model_name,
                language_code=context.language,
                device=self.device
            )
            aligned = whisperx.align(
                result["segments"],
                align_model,
                metadata,
                audio,
                device=self.device,
                return_char_alignments=False,
            )
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

            # Apply sentence segmentation for supported languages
            try:
                segmenter = get_segmenter(context.language)
                segments = segmenter.segment_transcripts(segments)
                logger.info(f"Applied {context.language} sentence segmentation")
            except ValueError as e:
                logger.info(f"No segmentation available for {context.language}: {e}")
                # Continue without segmentation for unsupported languages

            context.transcript_path.write_text(
                json.dumps(segments, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            logger.info(f"✅ Transcription completed for {context.youtube_id}")
            return self.run_next(context)
        except Exception as e:
            logger.error(f"❌ Transcription failed: {str(e)}")
            return False