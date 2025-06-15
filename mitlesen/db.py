import os
from typing import Optional, List
from dotenv import load_dotenv
from supabase import create_client, Client

from mitlesen.logger import logger

load_dotenv()

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
        language: str = 'de',
        vocabulary: str = None
    ):
        self.id = id
        self.title = title
        self.youtube_id = youtube_id
        self.is_premium = is_premium
        self.transcript = transcript
        self.language = language
        self.vocabulary = vocabulary

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "youtube_id": self.youtube_id,
            "is_premium": self.is_premium,
            "transcript": self.transcript,
            "language": self.language,
            "vocabulary": self.vocabulary
        }

    @classmethod
    def insert(cls, client: Client, title: str, youtube_id: str, is_premium: bool, transcript: str, language: str = 'de', vocabulary: str = None) -> None:
        """
        Insert a new video record.

        Args:
            client: Supabase client instance
            title: Title of the video.
            youtube_id: YouTube video ID.
            is_premium: Whether the video is premium.
            transcript: Transcript JSON as a string.
            language: Language code of the video (e.g., 'de', 'ja').
            vocabulary: Vocabulary JSON as a string (optional).
        """
        record = {
            'title': title,
            'youtube_id': youtube_id,
            'is_premium': is_premium,
            'transcript': transcript,
            'language': language
        }
        
        if vocabulary:
            record['vocabulary'] = vocabulary
            
        response = client.table('videos').insert(record).execute()
        logger.info("✅ Transcript inserted successfully.")

    @classmethod
    def exists(cls, client: Client, youtube_id: str) -> bool:
        """
        Check if a video with the given youtube_id exists in the database.
        
        Args:
            client: Supabase client instance
            youtube_id: YouTube video ID to check
            
        Returns:
            bool: True if the video exists, False otherwise
        """
        response = client.table('videos').select('id').eq('youtube_id', youtube_id).execute()
        # If there are any rows in the response, the video exists
        return len(response.data) > 0

    @classmethod
    def delete(cls, client: Client, record_id: int) -> None:
        """
        Delete a video record by ID.
        """
        response = client.table('videos').delete().eq('id', record_id).execute()
        if response.error:
            raise RuntimeError(f"Failed to delete record {record_id}: {response.error.message}")
        logger.info(f"🗑️ Record {record_id} deleted.")

    @classmethod
    def fetch_all(cls, client: Client) -> List['Video']:
        """
        Fetch all transcript records.
        """
        response = client.table('videos').select('*').execute()
        if response.error:
            raise RuntimeError(f"Failed to fetch records: {response.error.message}")
        records: List[Video] = []
        for row in response.data:
            record = cls(
                id=row['id'],
                title=row['title'],
                youtube_id=row['youtube_id'],
                is_premium=row['is_premium'],
                transcript=row['transcript'],
                language=row.get('language', 'de'),
                vocabulary=row.get('vocabulary')
            )
            records.append(record)
        return records

    @classmethod
    def fetch_by_id(cls, client: Client, record_id: int) -> Optional['Video']:
        """
        Fetch a transcript record by its ID.
        """
        response = client.table('videos').select('*').eq('id', record_id).single().execute()
        if response.error and 'no rows found' in response.error.message.lower():
            return None
        if response.error:
            raise RuntimeError(f"Failed to fetch record {record_id}: {response.error.message}")
        row = response.data
        return cls(
            id=row['id'],
            title=row['title'],
            youtube_id=row['youtube_id'],
            is_premium=row['is_premium'],
            transcript=row['transcript'],
            language=row.get('language', 'de'),
            vocabulary=row.get('vocabulary')
        )

class Genre:
    """
    Data model for a genre entry.
    """
    def __init__(
        self,
        id: int,
        name: str,
        created_at: str = None
    ):
        self.id = id
        self.name = name
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at
        }

    @classmethod
    def insert(cls, client: Client, name: str) -> Optional['Genre']:
        """
        Insert a new genre record if it doesn't exist.
        Returns the genre record if successful.
        """
        try:
            response = client.table('genres').insert({'name': name}).execute()
            if response.error:
                if 'duplicate key value' in response.error.message.lower():
                    # If genre exists, fetch it
                    response = client.table('genres').select('*').eq('name', name).single().execute()
                    if response.error:
                        raise RuntimeError(f"Failed to fetch existing genre {name}: {response.error.message}")
                    row = response.data
                    return cls(id=row['id'], name=row['name'], created_at=row['created_at'])
                raise RuntimeError(f"Failed to insert genre {name}: {response.error.message}")
            
            row = response.data[0]
            return cls(id=row['id'], name=row['name'], created_at=row['created_at'])
        except Exception as e:
            logger.error(f"Error inserting genre {name}: {str(e)}")
            return None

class Series:
    """
    Data model for a series entry.
    """
    def __init__(
        self,
        id: int,
        title: str,
        created_at: str = None
    ):
        self.id = id
        self.title = title
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at
        }

    @classmethod
    def insert(cls, client: Client, title: str) -> Optional['Series']:
        """
        Insert a new series record if it doesn't exist.
        Returns the series record if successful.
        """
        try:
            response = client.table('series').insert({'title': title}).execute()
            if response.error:
                if 'duplicate key value' in response.error.message.lower():
                    # If series exists, fetch it
                    response = client.table('series').select('*').eq('title', title).single().execute()
                    if response.error:
                        raise RuntimeError(f"Failed to fetch existing series {title}: {response.error.message}")
                    row = response.data
                    return cls(id=row['id'], title=row['title'], created_at=row['created_at'])
                raise RuntimeError(f"Failed to insert series {title}: {response.error.message}")
            
            row = response.data[0]
            return cls(id=row['id'], title=row['title'], created_at=row['created_at'])
        except Exception as e:
            logger.error(f"Error inserting series {title}: {str(e)}")
            return None

class SeriesGenre:
    """
    Data model for a series-genre relationship entry.
    """
    def __init__(
        self,
        series_id: int,
        genre_id: int,
        created_at: str = None
    ):
        self.series_id = series_id
        self.genre_id = genre_id
        self.created_at = created_at

    def to_dict(self) -> dict:
        return {
            "series_id": self.series_id,
            "genre_id": self.genre_id,
            "created_at": self.created_at
        }

    @classmethod
    def insert(cls, client: Client, series_id: int, genre_id: int) -> Optional['SeriesGenre']:
        """
        Insert a new series-genre relationship record if it doesn't exist.
        Returns the relationship record if successful.
        """
        try:
            response = client.table('series_genres').insert({
                'series_id': series_id,
                'genre_id': genre_id
            }).execute()
            
            if response.error:
                if 'duplicate key value' in response.error.message.lower():
                    # If relationship exists, fetch it
                    response = client.table('series_genres').select('*').eq('series_id', series_id).eq('genre_id', genre_id).single().execute()
                    if response.error:
                        raise RuntimeError(f"Failed to fetch existing series-genre relationship: {response.error.message}")
                    row = response.data
                    return cls(series_id=row['series_id'], genre_id=row['genre_id'], created_at=row['created_at'])
                raise RuntimeError(f"Failed to insert series-genre relationship: {response.error.message}")
            
            row = response.data[0]
            return cls(series_id=row['series_id'], genre_id=row['genre_id'], created_at=row['created_at'])
        except Exception as e:
            logger.error(f"Error inserting series-genre relationship: {str(e)}")
            return None

class Database:
    """
    Database connection manager.
    """
    def __init__(self):
        # Initialize Supabase client from environment variables
        url: str = os.getenv('SUPABASE_URL')
        key: str = os.getenv('SUPABASE_KEY')
        if not url or not key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
        self.client: Client = create_client(url, key)

    def close(self) -> None:
        """
        Close any resources if needed (Supabase uses HTTP so no persistent connection).
        """
        pass

class Dictionary:
    """
    Data model for a dictionary entry (Supabase version).
    """
    def __init__(
        self,
        id: str,
        lang: str,
        word: str = None,
        kana: str = None,
        romaji: str = None,
        lemma: str = None,
        pos: str = None,
        pos_remarks: str = "",
        gender: str = None,
        meanings: list = None,
        furigana: str = None,
        level: str = None
    ):
        self.id = id
        self.lang = lang
        self.word = word
        self.kana = kana
        self.romaji = romaji
        self.lemma = lemma
        self.pos = pos
        self.pos_remarks = pos_remarks
        self.gender = gender
        self.meanings = meanings
        self.furigana = furigana
        self.level = level

    def to_dict(self) -> dict:
        import json
        return {
            "id": self.id,
            "lang": self.lang,
            "word": self.word,
            "kana": self.kana,
            "romaji": self.romaji,
            "lemma": self.lemma,
            "pos": self.pos,
            "pos_remarks": self.pos_remarks,
            "gender": self.gender,
            "meanings": json.dumps(self.meanings, ensure_ascii=False) if self.meanings else None,
            "furigana": self.furigana,
            "level": self.level
        }

    @classmethod
    def insert(cls, client: Client, entry: dict) -> None:
        """
        Insert a new dictionary record.
        Args:
            client: Supabase client instance
            entry: Dictionary entry as a dict (use to_dict())
        """
        response = client.table('dictionaries').insert(entry).execute()
        if response.error:
            raise RuntimeError(f"Failed to insert dictionary entry {entry.get('id')}: {response.error.message}")
        logger.info(f"✅ Dictionary entry {entry.get('id')} inserted successfully.")

    @classmethod
    def exists(cls, client: Client, entry_id: str) -> bool:
        """
        Check if a dictionary entry with the given id exists in the database.
        Args:
            client: Supabase client instance
            entry_id: Dictionary entry ID to check
        Returns:
            bool: True if the entry exists, False otherwise
        """
        response = client.table('dictionaries').select('id').eq('id', entry_id).execute()
        return len(response.data) > 0

    @classmethod
    def delete(cls, client: Client, entry_id: str) -> None:
        """
        Delete a dictionary entry by ID.
        """
        response = client.table('dictionaries').delete().eq('id', entry_id).execute()
        if response.error:
            raise RuntimeError(f"Failed to delete dictionary entry {entry_id}: {response.error.message}")
        logger.info(f"🗑️ Dictionary entry {entry_id} deleted.")

    @classmethod
    def fetch_all(cls, client: Client) -> List['Dictionary']:
        """
        Fetch all dictionary records.
        """
        import json
        response = client.table('dictionaries').select('*').execute()
        if response.error:
            raise RuntimeError(f"Failed to fetch dictionary records: {response.error.message}")
        records: List[Dictionary] = []
        for row in response.data:
            meanings = json.loads(row['meanings']) if row.get('meanings') else None
            record = cls(
                id=row['id'],
                lang=row['lang'],
                word=row.get('word'),
                kana=row.get('kana'),
                romaji=row.get('romaji'),
                lemma=row.get('lemma'),
                pos=row.get('pos'),
                pos_remarks=row.get('pos_remarks', ''),
                gender=row.get('gender'),
                meanings=meanings,
                furigana=row.get('furigana'),
                level=row.get('level')
            )
            records.append(record)
        return records

    @classmethod
    def fetch_by_id(cls, client: Client, entry_id: str) -> Optional['Dictionary']:
        """
        Fetch a dictionary record by its ID.
        """
        import json
        response = client.table('dictionaries').select('*').eq('id', entry_id).single().execute()
        if response.error and 'no rows found' in response.error.message.lower():
            return None
        if response.error:
            raise RuntimeError(f"Failed to fetch dictionary entry {entry_id}: {response.error.message}")
        row = response.data
        meanings = json.loads(row['meanings']) if row.get('meanings') else None
        return cls(
            id=row['id'],
            lang=row['lang'],
            word=row.get('word'),
            kana=row.get('kana'),
            romaji=row.get('romaji'),
            lemma=row.get('lemma'),
            pos=row.get('pos'),
            pos_remarks=row.get('pos_remarks', ''),
            gender=row.get('gender'),
            meanings=meanings,
            furigana=row.get('furigana'),
            level=row.get('level')
        )
