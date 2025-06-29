# NOTE: This module is commented out because coqui-tts is not compatible with Python 3.13
# Uncomment and add coqui-tts to requirements.txt if TTS functionality is needed

# from pathlib import Path
# from typing import Optional

# try:
#     from TTS.api import TTS          # Coqui-TTS main entry-point
# except ImportError as exc:           # Fail fast if the library is missing
#     raise ImportError(
#         "coqui-tts is not installed. Install it with `pip install coqui-tts`."
#     ) from exc


# class TextToSpeech:

#     def __init__(
#         self,
#         model: str = "tts_models/de/thorsten/tacotron2-DDC",
#         *,
#         use_gpu: bool = False,
#         progress_bar: bool = False,
#         **kwargs,
#     ):
#         self.engine = TTS(
#             model_name=model,
#             gpu=use_gpu,
#             progress_bar=progress_bar,
#             **kwargs,
#         )
#         self.file_ext: str = "wav"
#         self.mime_type: str = "audio/wav"

#     def synthesize(self, text: str, output_path: str | Path) -> Path:
#         output_path = Path(output_path).with_suffix(f".{self.file_ext}")
#         output_path.parent.mkdir(parents=True, exist_ok=True)
#         self.engine.tts_to_file(text=text, file_path=str(output_path))
#         return output_path


