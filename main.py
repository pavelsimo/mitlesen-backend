#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import csv
from typing import List, Dict, Any, Optional, Union, Tuple

from db import MitLesenDatabase  # Import the database class

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('pipeline.log')
    ]
)
logger = logging.getLogger(__name__)

# Define data directory and CSV file
DATA_DIR = "data"
VIDEOS_CSV = "videos.csv"
CUDA_LIBRARY_PATH =  "/home/ubuntu/.virtualenvs/mitlesen-backend/lib/python3.12/site-packages/nvidia/cudnn/lib/"

def ensure_data_dir():
    """Ensure data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.info(f"Created data directory: {DATA_DIR}")

def read_videos_from_csv() -> List[Dict[str, str]]:
    """Read videos from the CSV file."""
    videos = []
    with open(VIDEOS_CSV, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            videos.append(row)
    
    logger.info(f"Read {len(videos)} videos from {VIDEOS_CSV}")
    return videos

def video_exists_in_database(youtube_id: str) -> bool:
    """Check if a video already exists in the Supabase database."""
    db = MitLesenDatabase()
    exists = db.video_exists(youtube_id)
    db.close()
    return exists

def run_command(cmd: List[str], step_name: str) -> bool:
    """Run a command and return whether it succeeded."""
    cmd_str = " ".join(cmd)
    logger.info(f"Running {step_name}: {cmd_str}")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=True)
        logger.info(f"{step_name} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"{step_name} failed with exit code {e.returncode}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"{step_name} failed with exception: {str(e)}")
        return False

def download_audio(youtube_id: str) -> bool:
    """Step 1: Download audio from YouTube."""
    audio_file = os.path.join(DATA_DIR, f"{youtube_id}.mp3")
    
    if os.path.exists(audio_file):
        logger.warning(f"⚠️ Audio file already exists: {audio_file}. Skipping download.")
        return True
    
    cmd = [sys.executable, "1_download_youtube_audio.py", youtube_id, DATA_DIR]
    return run_command(cmd, "Audio download")

def generate_transcript(youtube_id: str) -> bool:
    """Step 2: Generate transcript from audio."""
    audio_file = os.path.join(DATA_DIR, f"{youtube_id}.mp3")
    if not os.path.exists(audio_file):
        logger.error(f"Audio file not found: {audio_file}")
        return False
    
    # Set the required environment variable for CUDA libraries
    env = os.environ.copy()
    env["LD_LIBRARY_PATH"] = CUDA_LIBRARY_PATH
    # Check if transcript file already exists
    transcript_file = os.path.join(DATA_DIR, f"{youtube_id}.json")
    if os.path.exists(transcript_file):
        logger.warning(f"⚠️ Transcript file already exists: {transcript_file}. Skipping generation.")
        return True
    
    cmd = [
        sys.executable, 
        "2_audio_to_json_transcript.py", 
        audio_file, 
        "--model", "large-v2", 
        "--device", "cuda"
    ]
    
    # Pass the environment to the subprocess
    try:
        logger.info(f"Running Transcript generation: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, text=True, capture_output=True, env=env)
        logger.info("Transcript generation completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Transcript generation failed with exit code {e.returncode}")
        logger.error(f"Command output: {e.stdout}")
        logger.error(f"Command error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"Transcript generation failed with exception: {str(e)}")
        return False
    
def process_transcript(youtube_id: str, title: str, is_premium: str) -> bool:
    """Step 3: Process transcript and upload to database."""
    transcript_file = os.path.join(DATA_DIR, f"{youtube_id}.json")
    if not os.path.exists(transcript_file):
        logger.error(f"Transcript file not found: {transcript_file}")
        return False
    
    cmd = [
        sys.executable, 
        "3_json_transcript_to_supabase.py", 
        "--youtube_id", youtube_id, 
        "--title", title, 
        "--is_premium", is_premium
    ]
    return run_command(cmd, "Transcript processing and upload")

def process_video(video: Dict[str, str]) -> bool:
    """Process a single video through the entire pipeline."""
    youtube_id = video["youtube_id"]
    title = video["title"]
    is_premium = video["is_premium"]
    
    # Check if video already exists in database
    if video_exists_in_database(youtube_id):
        logger.info(f"Skipping video as it already exists in database: {youtube_id}")
        return True
    
    logger.info(f"Starting pipeline for video: {title} ({youtube_id})")
    
    # Step 1: Download audio
    if not download_audio(youtube_id):
        logger.error(f"Pipeline failed at step 1 for video: {youtube_id}")
        return False
    
    # Step 2: Generate transcript
    if not generate_transcript(youtube_id):
        logger.error(f"Pipeline failed at step 2 for video: {youtube_id}")
        return False
    
    # Step 3: Process transcript and upload
    if not process_transcript(youtube_id, title, is_premium):
        logger.error(f"Pipeline failed at step 3 for video: {youtube_id}")
        return False
    
    logger.info(f"Pipeline completed successfully for video: {youtube_id}")
    return True

def main():
    """Main function to process all videos."""
    ensure_data_dir()
    videos = read_videos_from_csv()
    
    successful = 0
    failed = 0
    skipped = 0
    for video in videos:
        if video_exists_in_database(video["youtube_id"]):
            logger.info(f"Skipping video already in database: {video['youtube_id']} - {video['title']}")
            skipped += 1
            continue
            
        if process_video(video):
            successful += 1
        else:
            failed += 1
    
    logger.info(f"Pipeline completed. Successful: {successful}, Failed: {failed}, Skipped: {skipped}")

if __name__ == "__main__":
    main() 