from dotenv import load_dotenv
import os

load_dotenv()

from typing import Optional, List
from supabase import create_client, Client

class Video:
    """
    Data model for a video entry.
    """
    def __init__(
        self,
        id: int,
        title: str,
        youtube_id: str,
        is_premium: bool,
        transcript: str,
        vocabulary: str = None
    ):
        self.id = id
        self.title = title
        self.youtube_id = youtube_id
        self.is_premium = is_premium
        self.transcript = transcript
        self.vocabulary = vocabulary

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "youtube_id": self.youtube_id,
            "is_premium": self.is_premium,
            "transcript": self.transcript,
            "vocabulary": self.vocabulary
        }

class MitLesenDatabase:
    """
    Manage a Supabase table of YouTube videos.
    """
    def __init__(self):
        # Initialize Supabase client from environment variables
        url: str = os.getenv('SUPABASE_URL')
        key: str = os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        self.client: Client = create_client(url, key)
        self.table = self.client.table('videos')

    def insert(
        self,
        title: str,
        youtube_id: str,
        is_premium: bool,
        transcript: str,
        vocabulary: str = None
    ) -> None:
        """
        Insert a new video record.

        Args:
            title: Title of the video.
            youtube_id: YouTube video ID.
            is_premium: Whether the video is premium.
            transcript: Transcript JSON as a string.
            vocabulary: Vocabulary JSON as a string (optional).
        """
        record = {
            'title': title,
            'youtube_id': youtube_id,
            'is_premium': is_premium,
            'transcript': transcript
        }
        
        if vocabulary:
            record['vocabulary'] = vocabulary
            
        response = self.table.insert(record).execute()
        print("✅ Transcript inserted successfully.")

    def delete(self, record_id: int) -> None:
        """
        Delete a video record by ID.
        """
        response = self.table.delete().eq('id', record_id).execute()
        if response.error:
            raise RuntimeError(f"Failed to delete record {record_id}: {response.error.message}")
        print(f"🗑️ Record {record_id} deleted.")

    def fetch_all(self) -> List[Video]:
        """
        Fetch all transcript records.
        """
        response = self.table.select('*').execute()
        if response.error:
            raise RuntimeError(f"Failed to fetch records: {response.error.message}")
        records: List[Video] = []
        for row in response.data:
            record = Video(
                id=row['id'],
                title=row['title'],
                youtube_id=row['youtube_id'],
                is_premium=row['is_premium'],
                transcript=row['transcript'],
                vocabulary=row.get('vocabulary')
            )
            records.append(record)
        return records

    def fetch_by_id(self, record_id: int) -> Optional[Video]:
        """
        Fetch a transcript record by its ID.
        """
        response = self.table.select('*').eq('id', record_id).single().execute()
        if response.error and 'no rows found' in response.error.message.lower():
            return None
        if response.error:
            raise RuntimeError(f"Failed to fetch record {record_id}: {response.error.message}")
        row = response.data
        return Video(
            id=row['id'],
            title=row['title'],
            youtube_id=row['youtube_id'],
            is_premium=row['is_premium'],
            transcript=row['transcript'],
            vocabulary=row.get('vocabulary')
        )

    def close(self) -> None:
        """
        Close any resources if needed (Supabase uses HTTP so no persistent connection).
        """
        pass
