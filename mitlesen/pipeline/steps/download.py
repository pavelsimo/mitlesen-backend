import time
import random
from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

class DownloadStep(PipelineStep):
    def __init__(self, name: str, max_retries: int = 3):
        super().__init__(name)
        self.max_retries = max_retries

    def execute(self, context: PipelineContext) -> bool:
        """Download audio from YouTube with robust error handling and retry logic."""
        logger.info(f"🎵 Starting download for {context.youtube_id}")
        
        # Check if audio already exists
        if context.audio_path.exists():
            logger.info(f"ℹ️ Audio file already exists: {context.audio_path}")
            return self.run_next(context)
            
        url = f"https://www.youtube.com/watch?v={context.youtube_id}"
        
        # Try download with retries
        for attempt in range(1, self.max_retries + 1):
            logger.info(f"🔄 Download attempt {attempt}/{self.max_retries} for {context.youtube_id}")
            
            try:
                success = self._attempt_download(url, context)
                if success:
                    logger.info(f"✅ Download completed for {context.youtube_id}")
                    return self.run_next(context)
                    
            except (DownloadError, ExtractorError) as e:
                self._handle_download_error(e, attempt, context.youtube_id)
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)
                    continue
                else:
                    logger.error(f"❌ All download attempts failed for {context.youtube_id}")
                    return False
                    
            except Exception as e:
                logger.error(f"❌ Unexpected error during download attempt {attempt}: {str(e)}")
                if attempt < self.max_retries:
                    self._wait_before_retry(attempt)
                    continue
                else:
                    return False
                    
        return False

    def _attempt_download(self, url: str, context: PipelineContext) -> bool:
        """Attempt a single download with robust yt-dlp options."""
        ydl_opts = {
            # Basic options
            "format": "bestaudio/best",
            "outtmpl": str(context.working_dir / context.youtube_id),
            
            # Audio processing
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "192",
            }],
            "postprocessor_args": ["-ar", "16000"],
            
            # Robust download options
            "http_headers": {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-us,en;q=0.5",
                "Accept-Encoding": "gzip, deflate",
                "DNT": "1",
                "Connection": "keep-alive",
                "Upgrade-Insecure-Requests": "1"
            },
            
            # Network and retry options
            "socket_timeout": 30,
            "retries": 3,
            "fragment_retries": 3,
            "retry_sleep_functions": {"http": lambda n: 2 ** n + random.uniform(0, 1)},
            
            # Error handling
            "ignoreerrors": False,
            "no_warnings": False,
            "quiet": False,
            
            # Additional robustness options
            "prefer_insecure": False,
            "check_formats": "selected",
        }
        
        try:
            with YoutubeDL(ydl_opts) as ydl:
                # First, try to extract info to check if video is accessible
                info = ydl.extract_info(url, download=False)
                logger.info(f"📋 Video info extracted: {info.get('title', 'Unknown Title')}")
                
                # Check for potential issues
                if info.get('is_live'):
                    logger.warning(f"⚠️ Video {context.youtube_id} is a live stream")
                    
                if info.get('age_limit', 0) > 0:
                    logger.warning(f"⚠️ Video {context.youtube_id} has age restriction: {info.get('age_limit')}")
                
                # Proceed with download
                ydl.download([url])
                return True
                
        except ExtractorError as e:
            if "403" in str(e) or "Forbidden" in str(e):
                raise DownloadError(f"HTTP 403 Forbidden - Video may be region-locked or require authentication: {str(e)}")
            elif "404" in str(e) or "not available" in str(e).lower():
                raise DownloadError(f"Video not found or unavailable: {str(e)}")
            else:
                raise e
                
        except Exception as e:
            raise e

    def _handle_download_error(self, error: Exception, attempt: int, youtube_id: str):
        """Handle and log download errors with specific guidance."""
        error_msg = str(error)
        
        if "403" in error_msg or "Forbidden" in error_msg:
            logger.warning(f"🚫 HTTP 403 Forbidden (attempt {attempt}): {youtube_id}")
            logger.info("💡 This could be due to: rate limiting, region restrictions, or authentication requirements")
            
        elif "404" in error_msg or "not available" in error_msg:
            logger.error(f"🔍 Video not found or unavailable: {youtube_id}")
            logger.error("💡 Video may have been deleted, made private, or is region-locked")
            
        elif "timeout" in error_msg.lower():
            logger.warning(f"⏱️ Network timeout (attempt {attempt}): {youtube_id}")
            logger.info("💡 This may be a temporary network issue")
            
        else:
            logger.warning(f"❓ Download error (attempt {attempt}): {error_msg}")

    def _wait_before_retry(self, attempt: int):
        """Wait before retry with exponential backoff plus jitter."""
        wait_time = (2 ** attempt) + random.uniform(0.5, 1.5)
        logger.info(f"⏳ Waiting {wait_time:.1f}s before retry...")
        time.sleep(wait_time) 