from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from yt_dlp import YoutubeDL

class DownloadStep(PipelineStep):
    def execute(self, context: PipelineContext) -> bool:
        """Download audio from YouTube (from 1_download_youtube_audio.py)"""
        logger.info(f"🎵 Starting download for {context.youtube_id}")
        
        # Check if audio already exists
        if context.audio_path.exists():
            logger.info(f"ℹ️ Audio file already exists: {context.audio_path}")
            return self.run_next(context)
        try:
            url = f"https://www.youtube.com/watch?v={context.youtube_id}"
            ydl_opts = {
                "format": "bestaudio/best",
                "outtmpl": str(context.working_dir / context.youtube_id),
                "postprocessors": [{
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": "wav",
                    "preferredquality": "192",
                }],
                "postprocessor_args": ["-ar", "16000"],
                "quiet": False,
                "no_warnings": True,
            }
            with YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
            logger.info(f"✅ Download completed for {context.youtube_id}")
            return self.run_next(context)
        except Exception as e:
            logger.error(f"❌ Download failed: {str(e)}")
            return False 