from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Dict, Any
from abc import ABC, abstractmethod

@dataclass
class PipelineContext:
    """Context object passed between pipeline steps"""
    youtube_id: str
    title: str
    is_premium: bool
    language: str
    working_dir: Path
    metadata: Dict[str, Any] = None
    
    @property
    def audio_path(self) -> Path:
        mp3_path = self.working_dir / f"{self.youtube_id}.mp3"
        wav_path = self.working_dir / f"{self.youtube_id}.wav"
        return mp3_path if mp3_path.exists() else wav_path
    
    @property
    def transcript_path(self) -> Path:
        return self.working_dir / f"{self.youtube_id}.json"
    
    @property
    def augmented_transcript_path(self) -> Path:
        return self.working_dir / f"{self.youtube_id}.json.2"

class PipelineStep(ABC):
    """Base class for all pipeline steps"""
    def __init__(self, name: str):
        self.name = name
        self._next_step: Optional[PipelineStep] = None

    @abstractmethod
    def execute(self, context: 'PipelineContext') -> bool:
        pass

    def set_next(self, step: 'PipelineStep') -> 'PipelineStep':
        self._next_step = step
        return step

    def run_next(self, context: 'PipelineContext') -> bool:
        if self._next_step:
            return self._next_step.execute(context)
        return True 