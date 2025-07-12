from pathlib import Path
from typing import List, Dict
from mitlesen.logger import logger
from mitlesen.pipeline.base import PipelineContext
from mitlesen.pipeline.steps.download import DownloadStep
from mitlesen.pipeline.steps.elevenlabs_transcribe import ElevenLabsTranscribeStep
from mitlesen.pipeline.steps.augment import AugmentStep
from mitlesen.pipeline.steps.upload import UploadStep
import signal

class PipelineRunner:
    """Main pipeline runner (replaces import_videos.py)"""
    def __init__(self, working_dir: Path):
        self.working_dir = working_dir
        self._setup_pipeline()
        self._interrupted = False
        # Set up signal handler
        signal.signal(signal.SIGINT, self._handle_interrupt)
        signal.signal(signal.SIGTERM, self._handle_interrupt)

    def _handle_interrupt(self, signum, frame):
        """Handle keyboard interrupt (Ctrl+C) and termination signals"""
        if self._interrupted:
            logger.warning("⚠️ Force quitting...")
            raise KeyboardInterrupt()
        logger.warning("⚠️ Interrupt received. Finishing current task and stopping gracefully...")
        self._interrupted = True

    def _setup_pipeline(self):
        """Setup the pipeline steps in the correct order"""
        download = DownloadStep("download")
        transcribe = ElevenLabsTranscribeStep("transcribe")
        augment = AugmentStep("augment")
        upload = UploadStep("upload")
        download.set_next(transcribe).set_next(augment).set_next(upload)
        self.pipeline = download  # Start from the first step!

    def process_video(self, video: Dict[str, str]) -> bool:
        """Process a single video through the pipeline"""
        if self._interrupted:
            return False
        context = PipelineContext(
            youtube_id=video["youtube_id"],
            title=video["title"],
            is_premium=video["is_premium"],
            language=video.get("language", "de"),
            working_dir=self.working_dir
        )
        return self.pipeline.execute(context)

    def process_videos(self, videos: List[Dict[str, str]]) -> Dict[str, int]:
        """Process multiple videos and return statistics"""
        stats = {"successful": 0, "failed": 0, "skipped": 0}
        try:
            for video in videos:
                if self._interrupted:
                    logger.warning("⚠️ Pipeline interrupted. Stopping after current video...")
                    break
                # Skipping logic can be added here if needed
                if self.process_video(video):
                    stats["successful"] += 1
                else:
                    stats["failed"] += 1
        except KeyboardInterrupt:
            logger.warning("⚠️ Pipeline interrupted by user")
        finally:
            # Restore default signal handlers
            signal.signal(signal.SIGINT, signal.SIG_DFL)
            signal.signal(signal.SIGTERM, signal.SIG_DFL)
        return stats 