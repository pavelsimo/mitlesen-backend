from pathlib import Path
from typing import Optional

try:
    from TTS.api import TTS          # Coqui-TTS main entry-point
except ImportError as exc:           # Fail fast if the library is missing
    raise ImportError(
        "Coqui-TTS is not installed. Install it with `pip install TTS`."
    ) from exc


class TextToSpeech:

    def __init__(
        self,
        model: str = "tts_models/de/thorsten/tacotron2-DDC",
        *,
        use_gpu: bool = False,
        progress_bar: bool = False,
        **kwargs,
    ):
        self.engine = TTS(
            model_name=model,
            gpu=use_gpu,
            progress_bar=progress_bar,
            **kwargs,
        )
        self.file_ext: str = "wav"
        self.mime_type: str = "audio/wav"

    def synthesize(self, text: str, output_path: str | Path) -> Path:
        output_path = Path(output_path).with_suffix(f".{self.file_ext}")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        self.engine.tts_to_file(text=text, file_path=str(output_path))
        return output_path


