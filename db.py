import os
import supabase
from dotenv import load_dotenv

load_dotenv()

class MitLesenDatabase:
    def __init__(self):
        self.client = supabase.create_client(
            os.environ.get("SUPABASE_URL"),
            os.environ.get("SUPABASE_KEY")
        )

    def insert(self, title, youtube_id, is_premium, transcript):
        return self.client.table('videos').insert({
            'title': title,
            'youtube_id': youtube_id,
            'is_premium': is_premium,
            'transcript': transcript
        }).execute()

    def video_exists(self, youtube_id):
        """Check if a video with the given youtube_id exists in the database."""
        response = self.client.table('videos').select('id') .eq('youtube_id', youtube_id).execute()
        # If there are any rows in the response, the video exists
        return len(response.data) > 0

    def close(self):
        # There's no explicit close method in the supabase-py client,
        # but we include this method for consistency and future-proofing
        pass 