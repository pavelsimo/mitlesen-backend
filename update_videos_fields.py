#!/usr/bin/env python3
import csv
from typing import Dict, List

from mitlesen import VIDEOS_CSV_FILES
from mitlesen.db import Database
from mitlesen.logger import logger

def read_videos_from_csv() -> List[Dict[str, str]]:
    """Read videos from all CSV files."""
    all_videos = []
    
    for csv_file in VIDEOS_CSV_FILES:
        try:
            videos = []
            with open(csv_file, 'r', encoding='utf-8') as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    videos.append(row)
            logger.info(f"📋 Read {len(videos)} videos from {csv_file}")
            all_videos.extend(videos)
        except FileNotFoundError:
            logger.warning(f"⚠️ CSV file not found: {csv_file}")
            continue
    
    logger.info(f"📋 Total videos read: {len(all_videos)}")
    return all_videos

def update_video_fields(db: Database, video: Dict[str, str], columns: List[str]) -> bool:
    """
    Update all fields (except youtube_id) for a video in the database.
    Args:
        db: Database instance
        video: Dict of video fields
        columns: List of columns to update
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        update_data = {}
        for col in columns:
            if col == 'serie_id':
                # Convert serie_id to integer if not empty
                update_data[col] = int(video[col]) if video[col] else None
            elif col == 'is_premium':
                # Convert is_premium to boolean
                update_data[col] = video[col].lower() == 'true'
            elif col == 'language':
                # Ensure language is a string
                update_data[col] = str(video[col]) if video[col] else 'de'
            else:
                update_data[col] = video[col]
        response = db.client.table('videos').update(update_data).eq('youtube_id', video['youtube_id']).execute()
        if not response.data:
            logger.error(f"❌ No video found with youtube_id {video['youtube_id']}")
            return False
        logger.info(f"✅ Updated video {video['youtube_id']} with fields: {update_data}")
        return True
    except Exception as e:
        logger.error(f"❌ Error updating video {video['youtube_id']}: {e}")
        return False

def main():
    """Main function to update all fields for all videos."""
    logger.info("🚀 Starting Video Fields Sync Process")
    videos = read_videos_from_csv()
    if not videos:
        logger.error("❌ No videos found in CSV files")
        return
    db = Database()
    successful = 0
    failed = 0
    # Get all columns except youtube_id
    columns = [col for col in videos[0].keys() if col != 'youtube_id']
    for video in videos:
        logger.info(f"🔄 Processing video: {video['youtube_id']}")
        if update_video_fields(db, video, columns):
            successful += 1
        else:
            failed += 1
    db.close()
    logger.info("📊 ===== Sync Summary =====")
    logger.info(f"📈 Total videos processed: {len(videos)}")
    logger.info(f"✅ Successful updates: {successful}")
    logger.info(f"❌ Failed updates: {failed}")
    logger.info("🏁 ===== Sync Process Completed =====")

if __name__ == "__main__":
    main() 