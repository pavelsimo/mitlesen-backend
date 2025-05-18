#!/usr/bin/env python3
import csv
from typing import Dict, List
from mitlesen.db import Database
from mitlesen.logger import logger

def read_videos_from_csv() -> List[Dict[str, str]]:
    """Read videos from the CSV file."""
    videos = []
    with open('videos.csv', 'r', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            videos.append(row)
    
    logger.info(f"📋 Read {len(videos)} videos from videos.csv")
    return videos

def update_video_series(db: Database, youtube_id: str, serie_id: str) -> bool:
    """
    Update the serie_id for a video in the database.
    
    Args:
        db: Database instance
        youtube_id: YouTube video ID
        serie_id: Series ID to update
        
    Returns:
        bool: True if update was successful, False otherwise
    """
    try:
        # Convert serie_id to integer if it's not empty
        serie_id_int = int(serie_id) if serie_id else None
        
        # Update the video record
        response = db.client.table('videos').update(
            {'serie_id': serie_id_int}
        ).eq('youtube_id', youtube_id).execute()
        
        # Check if the update was successful by looking at the data
        if not response.data:
            logger.error(f"❌ No video found with youtube_id {youtube_id}")
            return False
            
        logger.info(f"✅ Updated serie_id for video {youtube_id} to {serie_id_int}")
        return True
        
    except ValueError as e:
        logger.error(f"❌ Invalid serie_id value for video {youtube_id}: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Error updating video {youtube_id}: {e}")
        return False

def main():
    """Main function to update series IDs for all videos."""
    logger.info("🚀 Starting Series ID Update Process")
    
    # Read videos from CSV
    videos = read_videos_from_csv()
    if not videos:
        logger.error("❌ No videos found in CSV file")
        return
        
    # Initialize database connection
    db = Database()
    
    successful = 0
    failed = 0
    
    # Process each video
    for video in videos:
        youtube_id = video['youtube_id']
        serie_id = video['serie_id']
        
        logger.info(f"🔄 Processing video: {youtube_id} (serie_id: {serie_id})")
        
        if update_video_series(db, youtube_id, serie_id):
            successful += 1
        else:
            failed += 1
    
    # Close database connection
    db.close()
    
    # Print summary
    logger.info("📊 ===== Update Summary =====")
    logger.info(f"📈 Total videos processed: {len(videos)}")
    logger.info(f"✅ Successful updates: {successful}")
    logger.info(f"❌ Failed updates: {failed}")
    logger.info("🏁 ===== Update Process Completed =====")

if __name__ == "__main__":
    main() 