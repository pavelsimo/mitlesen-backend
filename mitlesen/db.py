import os
from typing import Optional, List, Dict, Any, Type, TypeVar
from abc import ABC, abstractmethod
from dotenv import load_dotenv
from supabase import create_client, Client
from postgrest.exceptions import APIError

from mitlesen.logger import logger

load_dotenv()

# Type variable for BaseSupabaseModel subclasses
T = TypeVar('T', bound='BaseSupabaseModel')


def get_supabase_client() -> Client:
    """Get a Supabase client instance."""
    url: str = os.getenv('SUPABASE_URL')
    key: str = os.getenv('SUPABASE_KEY')
    if not url or not key:
        raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in environment")
    return create_client(url, key)


class BaseSupabaseModel(ABC):
    """Base class for Supabase models with common CRUD operations."""

    @classmethod
    @abstractmethod
    def get_table_name(cls) -> str:
        """Return the Supabase table name for this model."""
        pass

    @classmethod
    @abstractmethod
    def from_row(cls: Type[T], row: Dict[str, Any]) -> T:
        """Create an instance from a database row."""
        pass

    @abstractmethod
    def to_dict(self) -> Dict[str, Any]:
        """Convert instance to dictionary."""
        pass

    @classmethod
    def _get_client(cls) -> Client:
        """Get Supabase client (can be overridden for testing)."""
        return get_supabase_client()

    @classmethod
    def _insert_with_duplicate_handling(
        cls: Type[T],
        data: Dict[str, Any],
        unique_fields: List[str],
        client: Optional[Client] = None
    ) -> Optional[T]:
        """
        Insert record with duplicate handling.

        Args:
            data: Data to insert
            unique_fields: Fields to check for existing records
            client: Optional client (uses default if None)

        Returns:
            Created or existing record, None if error
        """
        if client is None:
            client = cls._get_client()

        try:
            # Try to insert
            response = client.table(cls.get_table_name()).insert(data).execute()

            # Return created record
            row = response.data[0]
            return cls.from_row(row)

        except APIError as e:
            # Check if it's a duplicate key error
            if 'duplicate key value' in str(e).lower():
                # If duplicate, fetch existing record
                return cls._fetch_by_fields(unique_fields, data, client)
            else:
                raise RuntimeError(f"Failed to insert into {cls.get_table_name()}: {str(e)}")
        except Exception as e:
            logger.error(f"Error inserting into {cls.get_table_name()}: {str(e)}")
            return None

    @classmethod
    def _fetch_by_fields(
        cls: Type[T],
        field_names: List[str],
        field_values: Dict[str, Any],
        client: Optional[Client] = None
    ) -> Optional[T]:
        """
        Fetch record by specific field values.

        Args:
            field_names: List of field names to match
            field_values: Dictionary containing field values
            client: Optional client (uses default if None)

        Returns:
            Found record or None
        """
        if client is None:
            client = cls._get_client()

        try:
            query = client.table(cls.get_table_name()).select('*')

            # Apply eq filters for each field
            for field_name in field_names:
                if field_name in field_values:
                    query = query.eq(field_name, field_values[field_name])

            response = query.single().execute()
            return cls.from_row(response.data)

        except APIError as e:
            # Check if it's a "no rows found" error
            if 'no rows found' in str(e).lower():
                return None
            logger.error(f"Error fetching from {cls.get_table_name()}: {str(e)}")
            return None
        except Exception as e:
            logger.error(f"Error fetching from {cls.get_table_name()}: {str(e)}")
            return None

    @classmethod
    def _fetch_by_field(
        cls: Type[T],
        field_name: str,
        field_value: Any,
        client: Optional[Client] = None
    ) -> Optional[T]:
        """
        Fetch record by a single field value.

        Args:
            field_name: Name of the field to match
            field_value: Value to match
            client: Optional client (uses default if None)

        Returns:
            Found record or None
        """
        return cls._fetch_by_fields([field_name], {field_name: field_value}, client)

    @classmethod
    def _fetch_all(cls: Type[T], client: Optional[Client] = None) -> List[T]:
        """
        Fetch all records from the table.

        Args:
            client: Optional client (uses default if None)

        Returns:
            List of all records
        """
        if client is None:
            client = cls._get_client()

        try:
            response = client.table(cls.get_table_name()).select('*').execute()
            return [cls.from_row(row) for row in response.data]

        except Exception as e:
            logger.error(f"Error fetching all from {cls.get_table_name()}: {str(e)}")
            return []

    @classmethod
    def _exists_by_field(
        cls,
        field_name: str,
        field_value: Any,
        client: Optional[Client] = None
    ) -> bool:
        """
        Check if a record exists by field value.

        Args:
            field_name: Name of the field to check
            field_value: Value to check for
            client: Optional client (uses default if None)

        Returns:
            True if record exists, False otherwise
        """
        if client is None:
            client = cls._get_client()

        try:
            response = client.table(cls.get_table_name()).select('id').eq(field_name, field_value).execute()
            return len(response.data) > 0
        except Exception as e:
            logger.error(f"Error checking existence in {cls.get_table_name()}: {str(e)}")
            return False

class Video(BaseSupabaseModel):
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

    @classmethod
    def get_table_name(cls) -> str:
        return 'videos'

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Video':
        return cls(
            id=row['id'],
            title=row['title'],
            youtube_id=row['youtube_id'],
            is_premium=row['is_premium'],
            transcript=row['transcript'],
            language=row.get('language', 'de'),
            vocabulary=row.get('vocabulary')
        )

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
    def insert(cls, title: str, youtube_id: str, is_premium: bool, transcript: str, language: str = 'de', vocabulary: str = None) -> Optional['Video']:
        """
        Insert a new video record.

        Args:
            title: Title of the video.
            youtube_id: YouTube video ID.
            is_premium: Whether the video is premium.
            transcript: Transcript JSON as a string.
            language: Language code of the video (e.g., 'de', 'ja').
            vocabulary: Vocabulary JSON as a string (optional).

        Returns:
            Created or existing Video record, None if error
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

        result = cls._insert_with_duplicate_handling(record, ['youtube_id'])
        if result:
            logger.info("✅ Video inserted successfully.")
        return result

    @classmethod
    def get_by_youtube_id(cls, youtube_id: str) -> Optional['Video']:
        """Get video by YouTube ID."""
        return cls._fetch_by_field('youtube_id', youtube_id)

    @classmethod
    def exists(cls, youtube_id: str) -> bool:
        """
        Check if a video with the given youtube_id exists in the database.

        Args:
            youtube_id: YouTube video ID to check

        Returns:
            bool: True if the video exists, False otherwise
        """
        return cls._exists_by_field('youtube_id', youtube_id)

    @classmethod
    def fetch_all(cls) -> List['Video']:
        """Fetch all video records."""
        return cls._fetch_all()

    @classmethod
    def fetch_by_id(cls, record_id: int) -> Optional['Video']:
        """Fetch a video record by its ID."""
        return cls._fetch_by_field('id', record_id)

class Genre(BaseSupabaseModel):
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

    @classmethod
    def get_table_name(cls) -> str:
        return 'genres'

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Genre':
        return cls(
            id=row['id'],
            name=row['name'],
            created_at=row.get('created_at')
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at
        }

    @classmethod
    def insert(cls, name: str) -> Optional['Genre']:
        """
        Insert a new genre record if it doesn't exist.
        Returns the genre record if successful.
        """
        return cls._insert_with_duplicate_handling({'name': name}, ['name'])

    @classmethod
    def get_by_name(cls, name: str) -> Optional['Genre']:
        """Get genre by name."""
        return cls._fetch_by_field('name', name)

class Series(BaseSupabaseModel):
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

    @classmethod
    def get_table_name(cls) -> str:
        return 'series'

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'Series':
        return cls(
            id=row['id'],
            title=row['title'],
            created_at=row.get('created_at')
        )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "created_at": self.created_at
        }

    @classmethod
    def insert(cls, title: str) -> Optional['Series']:
        """
        Insert a new series record if it doesn't exist.
        Returns the series record if successful.
        """
        return cls._insert_with_duplicate_handling({'title': title}, ['title'])

    @classmethod
    def get_by_name(cls, title: str) -> Optional['Series']:
        """Get series by title."""
        return cls._fetch_by_field('title', title)

class SeriesGenre(BaseSupabaseModel):
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

    @classmethod
    def get_table_name(cls) -> str:
        return 'series_genres'

    @classmethod
    def from_row(cls, row: Dict[str, Any]) -> 'SeriesGenre':
        return cls(
            series_id=row['series_id'],
            genre_id=row['genre_id'],
            created_at=row.get('created_at')
        )

    def to_dict(self) -> dict:
        return {
            "series_id": self.series_id,
            "genre_id": self.genre_id,
            "created_at": self.created_at
        }

    @classmethod
    def insert(cls, series_id: int, genre_id: int) -> Optional['SeriesGenre']:
        """
        Insert a new series-genre relationship record if it doesn't exist.
        Returns the relationship record if successful.
        """
        data = {'series_id': series_id, 'genre_id': genre_id}
        return cls._insert_with_duplicate_handling(data, ['series_id', 'genre_id'])

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
        try:
            response = client.table('dictionaries').insert(entry).execute()
            logger.info(f"✅ Dictionary entry {entry.get('id')} inserted successfully.")
        except Exception as e:
            raise RuntimeError(f"Failed to insert dictionary entry {entry.get('id')}: {str(e)}")

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
        try:
            response = client.table('dictionaries').delete().eq('id', entry_id).execute()
            logger.info(f"🗑️ Dictionary entry {entry_id} deleted.")
        except Exception as e:
            raise RuntimeError(f"Failed to delete dictionary entry {entry_id}: {str(e)}")

    @classmethod
    def fetch_all(cls, client: Client) -> List['Dictionary']:
        """
        Fetch all dictionary records.
        """
        import json
        try:
            response = client.table('dictionaries').select('*').execute()
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
        except Exception as e:
            raise RuntimeError(f"Failed to fetch dictionary records: {str(e)}")

    @classmethod
    def fetch_by_id(cls, client: Client, entry_id: str) -> Optional['Dictionary']:
        """
        Fetch a dictionary record by its ID.
        """
        import json
        try:
            response = client.table('dictionaries').select('*').eq('id', entry_id).single().execute()
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
        except APIError as e:
            if 'no rows found' in str(e).lower():
                return None
            raise RuntimeError(f"Failed to fetch dictionary entry {entry_id}: {str(e)}")
        except Exception as e:
            raise RuntimeError(f"Failed to fetch dictionary entry {entry_id}: {str(e)}")


class SupabaseDictionary:
    """
    Unified interface wrapper for Supabase-based Dictionary operations.

    This class implements the BaseDictionaryInterface to provide a consistent API
    for dictionary operations across SQLite and Supabase implementations.
    """

    def __init__(self, client: Client):
        """Initialize with a Supabase client."""
        self.client = client

    def search_by_lemma(self, lemma: str, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for dictionary entries by lemma (and optionally language)."""
        import json

        query = self.client.table('dictionaries').select('*')

        # Case-insensitive lemma search
        if lang:
            query = query.ilike('lemma', lemma.lower()).eq('lang', lang)
        else:
            query = query.ilike('lemma', lemma.lower())

        try:
            response = query.execute()

                        # Convert meanings from JSON strings to lists
            results = []
            for row in response.data:
                row_copy = row.copy()
                if row_copy.get('meanings'):
                    try:
                        row_copy['meanings'] = json.loads(row_copy['meanings'])
                    except json.JSONDecodeError:
                        row_copy['meanings'] = None
                results.append(row_copy)

            return results
        except Exception as e:
            logger.error(f"Failed to search dictionary by lemma: {str(e)}")
            return []

    def search_japanese_word(self, word: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Search for a Japanese dictionary entry by word dict using prioritized matching logic.

        This implements the same prioritized search logic as SqliteDictionary.
        """
        import json

        lemma_kana = word.get('base_form')
        lemma_kanji = word.get('base_form2')
        pos = word.get('pos')
        kana = word.get('text')

        logger.info(f"Searching for Japanese word: lemma_kana={lemma_kana}, lemma_kanji={lemma_kanji}, pos={pos}, kana={kana}")

        # 1. Try to match by (lang='ja', lemma_kana, pos)
        if lemma_kana and pos:
            logger.info(f"Attempting match by (lang='ja', lemma_kana={lemma_kana}, pos={pos})")
            response = self.client.table('dictionaries') \
                .select('*') \
                .eq('lang', 'ja') \
                .eq('lemma', lemma_kana) \
                .eq('pos', pos) \
                .limit(1) \
                .execute()

            if response.data:
                row = response.data[0]
                logger.info("Found a match by lemma_kana and pos")
                if row.get('meanings'):
                    try:
                        row['meanings'] = json.loads(row['meanings'])
                    except json.JSONDecodeError:
                        row['meanings'] = None
                return row

        # 2. Try to match by (lang='ja', lemma_kanji, pos)
        if lemma_kanji and pos:
            logger.info(f"Attempting match by (lang='ja', lemma_kanji={lemma_kanji}, pos={pos})")
            response = self.client.table('dictionaries') \
                .select('*') \
                .eq('lang', 'ja') \
                .eq('lemma', lemma_kanji) \
                .eq('pos', pos) \
                .limit(1) \
                .execute()

            if response.data:
                row = response.data[0]
                logger.info("Found a match by lemma_kanji and pos")
                if row.get('meanings'):
                    try:
                        row['meanings'] = json.loads(row['meanings'])
                    except json.JSONDecodeError:
                        row['meanings'] = None
                return row

        # 3. Try to match by (lang='ja', lemma_kana)
        if lemma_kana:
            logger.info(f"Attempting match by (lang='ja', lemma_kana={lemma_kana})")
            response = self.client.table('dictionaries') \
                .select('*') \
                .eq('lang', 'ja') \
                .eq('lemma', lemma_kana) \
                .limit(1) \
                .execute()

            if response.data:
                row = response.data[0]
                logger.info("Found a match by lemma_kana")
                if row.get('meanings'):
                    try:
                        row['meanings'] = json.loads(row['meanings'])
                    except json.JSONDecodeError:
                        row['meanings'] = None
                return row

        # 4. Try to match by (lang='ja', kana)
        if kana:
            logger.info(f"Attempting match by (lang='ja', kana={kana})")
            response = self.client.table('dictionaries') \
                .select('*') \
                .eq('lang', 'ja') \
                .eq('kana', kana) \
                .limit(1) \
                .execute()

            if response.data:
                row = response.data[0]
                logger.info("Found a match by kana")
                if row.get('meanings'):
                    try:
                        row['meanings'] = json.loads(row['meanings'])
                    except json.JSONDecodeError:
                        row['meanings'] = None
                return row

        logger.info("No match found for Japanese word")
        return None

    def close(self) -> None:
        """Close database connection - no-op for Supabase as it manages connections."""
        pass
