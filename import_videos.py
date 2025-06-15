#!/usr/bin/env python3
import os
from dotenv import load_dotenv

load_dotenv()

import csv
from pathlib import Path
from mitlesen import VIDEOS_DIR
from mitlesen.pipeline.runner import PipelineRunner
from mitlesen.logger import logger

VIDEOS_CSV = "videos.csv"

def read_videos_from_csv():
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

def main():
    logger.info("🚀 ===== Starting Video Processing Pipeline =====")
    working_dir = Path(VIDEOS_DIR)
    working_dir.mkdir(parents=True, exist_ok=True)
    runner = PipelineRunner(working_dir)
    videos = read_videos_from_csv()
    if not videos:
        logger.error(f"❌ No videos found in CSV file: {VIDEOS_CSV}")
        return
    stats = runner.process_videos(videos)
    logger.info("📊 ===== Pipeline Summary =====")
    logger.info(f"📈 Total videos: {len(videos)}")
    logger.info(f"✅ Successful: {stats['successful']}")
    logger.info(f"❌ Failed: {stats['failed']}")
    logger.info(f"⏭️ Skipped: {stats['skipped']}")
    logger.info("🏁 ===== Pipeline Completed =====")

if __name__ == "__main__":
    main() 