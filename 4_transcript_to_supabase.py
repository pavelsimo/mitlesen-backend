#!/usr/bin/env python3
import json
import os.path
import argparse
from typing import Dict, List, Any

from dotenv import load_dotenv
from mitlesen.db import Database, Video
from mitlesen.logger import logger

load_dotenv()

def insert_transcript(youtube_id: str, title: str, is_premium: bool) -> None:
    """
    Insert an augmented transcript into the database.
    
    Args:
        youtube_id: YouTube video ID
        title: Title of the YouTube video
        is_premium: Boolean indicating if video is premium
    """
    DATA_FOLDER = 'data'
    db = Database()

    transcript_path = os.path.join(DATA_FOLDER, youtube_id + '.json.2')

    try:
        # Check if video already exists
        if Video.exists(db.client, youtube_id):
            logger.info(f"Video {youtube_id} already exists in database, skipping...")
            return

        with open(transcript_path, 'r', encoding='utf-8') as file:
            transcript: List[Dict[str, Any]] = json.load(file)
            
            # Insert the processed transcript into the database
            Video.insert(
                client=db.client,
                title=title,
                youtube_id=youtube_id,
                is_premium=is_premium,
                transcript=json.dumps(transcript)
            )

            logger.info(f"✅ Transcript inserted successfully")
            
    except Exception as err:
        logger.error(f"❌ Error processing {youtube_id}: {err}")
    finally:
        db.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Insert augmented transcript into database')
    parser.add_argument('--youtube_id', type=str, required=True, help='YouTube video ID')
    parser.add_argument('--title', type=str, required=True, help='Title of the YouTube video')
    parser.add_argument('--is_premium', type=str, choices=['true', 'false'], default='false', 
                       help='Whether the video is premium or not (true/false)')
    
    args = parser.parse_args()
    
    # Convert string to boolean
    is_premium_bool = args.is_premium.lower() == "true"
    
    insert_transcript(args.youtube_id, args.title, is_premium_bool) 