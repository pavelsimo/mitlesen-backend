#!/usr/bin/env python3
import os
import sys
import subprocess
import csv
from typing import List, Dict

from mitlesen.db import Video, Database
from mitlesen.logger import logger

# Define data directory and CSV file
DATA_DIR = "data"
VIDEOS_CSV = "videos.csv"
CUDA_LIBRARY_PATH = "/home/ubuntu/.virtualenvs/mitlesen-backend/lib/python3.12/site-packages/nvidia/cudnn/lib/"

def ensure_data_dir():
    """Ensure data directory exists."""
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        logger.info(f"📁 Created data directory: {DATA_DIR}")

        
    else:
        logger.info(f"📁 Using existing data directory: {DATA_DIR}")

def read_videos_from_csv() -> List[Dict[str, str]]:
    """Read videos from the CSV file."""
    if not os.path.exists(VIDEOS_CSV):
        logger.error(f"❌ CSV file not found: {VIDEOS_CSV}")
        return []
        
    videos = []
    with open(VIDEOS_CSV, 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            videos.append(row)
    
    logger.info(f"📋 Read {len(videos)} videos from {VIDEOS_CSV}")
    return videos

def video_exists_in_database(youtube_id: str) -> bool:
    """Check if a video already exists in the Supabase database."""
    logger.info(f"🔍 Checking if video exists in database: {youtube_id}")
    db = Database()
    exists = Video.exists(db.client, youtube_id)
    db.close()
    
    if exists:
        logger.info(f"✅ Video already exists in database: {youtube_id}")
    else:
        logger.info(f"🆕 Video not found in database: {youtube_id}")
    
    return exists

def run_command(cmd: List[str], step_name: str) -> bool:
    """Run a command and return whether it succeeded."""
    cmd_str = " ".join(cmd)
    logger.info(f"⚙️ Running {step_name}: {cmd_str}")
    
    try:
        result = subprocess.run(cmd, check=True, text=True, capture_output=False)
        logger.info(f"✅ {step_name} completed successfully")
        if result.stdout:
            logger.debug(f"📄 {step_name} output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ {step_name} failed with exit code {e.returncode}")
        logger.error(f"❌ Command output: {e.stdout}")
        logger.error(f"❌ Command error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ {step_name} failed with exception: {str(e)}")
        return False

def download_audio(youtube_id: str) -> bool:
    """Step 1: Download audio from YouTube."""
    logger.info(f"🎵 Starting Step 1: Download audio for {youtube_id}")
    audio_file = os.path.join(DATA_DIR, f"{youtube_id}.mp3")
    
    if os.path.exists(audio_file):
        logger.warning(f"⚠️ Audio file already exists: {audio_file}. Skipping download.")
        return True
    
    # Use a list for command arguments to properly handle YouTube IDs starting with "-"
    cmd = [
        sys.executable,
        "1_download_youtube_audio.py",
        "--",
        youtube_id,
        DATA_DIR
    ]
    result = run_command(cmd, "Audio download")
    
    if result:
        logger.info(f"✅ Step 1 completed: Audio downloaded for {youtube_id}")
    else:
        logger.error(f"❌ Step 1 failed: Audio download failed for {youtube_id}")
    
    return result

def generate_transcript(youtube_id: str, language: str) -> bool:
    """Step 2: Generate transcript from audio."""
    logger.info(f"🔊 Starting Step 2: Generate transcript for {youtube_id}")
    audio_file = os.path.join(DATA_DIR, f"{youtube_id}.mp3")
    if not os.path.exists(audio_file):
        logger.error(f"❌ Audio file not found: {audio_file}")
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
        "--device", "cuda",
        "--language", language
    ]
    
    # Pass the environment to the subprocess
    try:
        logger.info(f"⚙️ Running Transcript generation: {' '.join(cmd)}")
        result = subprocess.run(cmd, check=True, text=True, capture_output=True, env=env)
        logger.info("✅ Step 2 completed: Transcript generation successful")
        if result.stdout:
            logger.debug(f"📄 Transcript generation output: {result.stdout}")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"❌ Step 2 failed: Transcript generation failed with exit code {e.returncode}")
        logger.error(f"❌ Command output: {e.stdout}")
        logger.error(f"❌ Command error: {e.stderr}")
        return False
    except Exception as e:
        logger.error(f"❌ Step 2 failed: Transcript generation failed with exception: {str(e)}")
        return False

def augment_transcript(youtube_id: str, language: str) -> bool:
    """Step 3: Augment transcript with AI-generated translations and word-level information."""
    logger.info(f"🤖 Starting Step 3: Augment transcript for {youtube_id}")
    transcript_file = os.path.join(DATA_DIR, f"{youtube_id}.json")
    if not os.path.exists(transcript_file):
        logger.error(f"❌ Transcript file not found: {transcript_file}")
        return False

    # Check if augmented transcript already exists
    augmented_file = os.path.join(DATA_DIR, f"{youtube_id}.json.2")
    if os.path.exists(augmented_file):
        logger.warning(f"⚠️ Augmented transcript file already exists: {augmented_file}. Skipping augmentation.")
        return True

    cmd = [
        sys.executable,
        "3_augment_transcript.py",
        f"--youtube_id={youtube_id}",
        f"--language={language}"
    ]
    result = run_command(cmd, "Transcript augmentation")
    if result:
        logger.info(f"✅ Step 3 completed: Transcript augmented for {youtube_id}")
    else:
        logger.error(f"❌ Step 3 failed: Transcript augmentation failed for {youtube_id}")
    return result

def insert_transcript(youtube_id: str, title: str, is_premium: str, language: str) -> bool:
    """Step 4: Insert augmented transcript into database."""
    logger.info(f"💾 Starting Step 4: Insert transcript for {youtube_id}")
    augmented_file = os.path.join(DATA_DIR, f"{youtube_id}.json.2")
    if not os.path.exists(augmented_file):
        logger.error(f"❌ Augmented transcript file not found: {augmented_file}")
        return False

    cmd = [
        sys.executable,
        "4_transcript_to_supabase.py",
        f"--youtube_id={youtube_id}",
        f"--title={title}",
        f"--is_premium={is_premium}",
        f"--language={language}"
    ]
    result = run_command(cmd, "Transcript database insertion")
    if result:
        logger.info(f"✅ Step 4 completed: Transcript inserted for {youtube_id}")
    else:
        logger.error(f"❌ Step 4 failed: Transcript insertion failed for {youtube_id}")
    return result

def process_video(video: Dict[str, str]) -> bool:
    """Process a single video through the entire pipeline."""
    youtube_id = video["youtube_id"]
    title = video["title"]
    is_premium = video["is_premium"]
    language = video.get("language", "de")  # Default to German if language not specified
    
    # Check if video already exists in database
    if video_exists_in_database(youtube_id):
        logger.info(f"⏭️ Skipping video as it already exists in database: {youtube_id}")
        return True
    
    logger.info(f"🎬 Starting pipeline for video: {title} ({youtube_id})")
    
    # Step 1: Download audio
    if not download_audio(youtube_id):
        logger.error(f"❌ Pipeline failed at step 1 for video: {youtube_id}")
        return False
    
    # Step 2: Generate transcript
    if not generate_transcript(youtube_id, language):
        logger.error(f"❌ Pipeline failed at step 2 for video: {youtube_id}")
        return False
    
    # Step 3: Augment transcript
    if not augment_transcript(youtube_id, language):
        logger.error(f"❌ Pipeline failed at step 3 for video: {youtube_id}")
        return False
    
    # Step 4: Insert transcript into database
    if not insert_transcript(youtube_id, title, is_premium, language):
        logger.error(f"❌ Pipeline failed at step 4 for video: {youtube_id}")
        return False
    
    logger.info(f"🏁 Pipeline completed successfully for video: {youtube_id}")
    return True

def main():
    """Main function to process all videos."""
    logger.info("🚀 ===== Starting Video Processing Pipeline =====")
    ensure_data_dir()
    videos = read_videos_from_csv()
    
    if not videos:
        logger.error(f"❌ No videos found in CSV file: {VIDEOS_CSV}")
        return
    
    successful = 0
    failed = 0
    skipped = 0
    
    logger.info(f"📋 Found {len(videos)} videos to process")
    
    for i, video in enumerate(videos, 1):
        logger.info(f"🎬 Processing video {i}/{len(videos)}: {video['youtube_id']} - {video['title']}")
        
        if video_exists_in_database(video["youtube_id"]):
            logger.info(f"⏭️ Skipping video already in database: {video['youtube_id']} - {video['title']}")
            skipped += 1
            continue
            
        if process_video(video):
            successful += 1
        else:
            failed += 1
    
    logger.info("📊 ===== Pipeline Summary =====")
    logger.info(f"📈 Total videos: {len(videos)}")
    logger.info(f"✅ Successful: {successful}")
    logger.info(f"❌ Failed: {failed}")
    logger.info(f"⏭️ Skipped: {skipped}")
    logger.info("🏁 ===== Pipeline Completed =====")

if __name__ == "__main__":
    main() 