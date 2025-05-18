import csv
import os
import urllib.parse
import base64
from typing import List, Set, Optional
from mitlesen.db import Database, Series, Genre, SeriesGenre
from mitlesen.logger import logger

def get_image_base64(image_path: str) -> Optional[str]:
    """
    Convert an image file to base64 string.
    Returns None if the file doesn't exist or can't be read.
    """
    if not os.path.exists(image_path):
        logger.error(f"❌ Image file not found: {image_path}")
        return None
        
    try:
        # Determine the image type from extension
        ext = os.path.splitext(image_path)[1].lower()
        if ext not in ['.jpg', '.jpeg', '.png']:
            logger.error(f"❌ Unsupported image format: {ext}")
            return None
            
        mime_type = 'image/jpeg' if ext in ['.jpg', '.jpeg'] else 'image/png'
        
        with open(image_path, 'rb') as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
            return f"data:{mime_type};base64,{encoded_string}"
    except Exception as e:
        logger.error(f"❌ Error converting image to base64: {str(e)}")
        return None

def get_series_by_title(db: Database, title: str) -> Optional[Series]:
    """
    Get a series by title from the database.
    Returns None if the series doesn't exist.
    """
    try:
        # URL encode the title to handle special characters
        encoded_title = urllib.parse.quote(title)
        response = db.client.table('series').select('*').eq('title', title).execute()
        if not response.data or len(response.data) == 0:  # No data means series doesn't exist
            return None
        # Use the first match if multiple exist
        row = response.data[0]
        return Series(
            id=row['id'],
            title=row['title'],
            created_at=row['created_at']
        )
    except Exception as e:
        if 'no rows found' in str(e).lower():
            return None
        logger.error(f"Error fetching series {title}: {str(e)}")
        return None

def create_series(db: Database, title: str, series_id: int, cover_image: Optional[str] = None) -> Optional[Series]:
    """
    Create a new series in the database with the specified ID and optional cover image.
    Returns None if creation fails.
    """
    try:
        data = {
            'id': series_id,
            'title': title
        }
        if cover_image:
            data['cover_image'] = cover_image
            
        response = db.client.table('series').insert(data).execute()
        if not response.data or len(response.data) == 0:
            logger.error(f"Failed to create series: {title}")
            return None
        
        row = response.data[0]
        return Series(
            id=row['id'],
            title=row['title'],
            created_at=row['created_at']
        )
    except Exception as e:
        if 'duplicate key value' in str(e).lower():
            # If we got a duplicate key error, try fetching again
            return get_series_by_title(db, title)
        logger.error(f"Error creating series {title}: {str(e)}")
        return None

def get_genre_by_name(db: Database, name: str) -> Optional[Genre]:
    """
    Get a genre by name from the database.
    Returns None if the genre doesn't exist.
    """
    try:
        response = db.client.table('genres').select('*').eq('name', name).execute()
        if not response.data or len(response.data) == 0:  # No data means genre doesn't exist
            return None
        # Use the first match if multiple exist
        row = response.data[0]
        return Genre(
            id=row['id'],
            name=row['name'],
            created_at=row['created_at']
        )
    except Exception as e:
        if 'no rows found' in str(e).lower():
            return None
        logger.error(f"Error fetching genre {name}: {str(e)}")
        return None

def get_or_create_genre(db: Database, name: str) -> Optional[Genre]:
    """
    Get a genre by name or create it if it doesn't exist.
    Returns None if both operations fail.
    """
    # Try to get existing genre first
    genre = get_genre_by_name(db, name)
    if genre is not None:
        logger.info(f"📚 Using existing genre: {name}")
        return genre
    
    # Genre doesn't exist, try to create it
    try:
        response = db.client.table('genres').insert({'name': name}).execute()
        if not response.data or len(response.data) == 0:
            logger.error(f"❌ Failed to create genre: {name}")
            return None
        
        row = response.data[0]
        genre = Genre(
            id=row['id'],
            name=row['name'],
            created_at=row['created_at']
        )
        logger.info(f"✨ Created new genre: {name}")
        return genre
    except Exception as e:
        if 'duplicate key value' in str(e).lower():
            # If we got a duplicate key error, try fetching again
            return get_genre_by_name(db, name)
        logger.error(f"❌ Error creating genre {name}: {str(e)}")
        return None

def import_series_genres(csv_path: str, covers_dir: str = "covers") -> None:
    """
    Import series and genres from a CSV file into the database.
    The CSV should have three columns: Id, Serie, and Genres (comma-separated).
    Also imports cover images from the covers directory.
    """
    if not os.path.exists(csv_path):
        logger.error(f"❌ CSV file not found: {csv_path}")
        return

    if not os.path.exists(covers_dir):
        logger.error(f"❌ Covers directory not found: {covers_dir}")
        return

    db = Database()
    
    try:
        with open(csv_path, 'r', encoding='utf-8') as f:
            # Skip the header row and read directly as a list of lists
            reader = csv.reader(f)
            next(reader)  # Skip header row
            
            for row in reader:
                if len(row) != 3:
                    logger.error(f"❌ Invalid row format: {row}")
                    continue
                    
                try:
                    series_id = int(row[0].strip())
                except ValueError:
                    logger.error(f"❌ Invalid series ID: {row[0]}")
                    continue
                    
                series_title = row[1].strip()
                genres_str = row[2].strip()
                
                if not series_title or not genres_str:
                    logger.error(f"❌ Empty series title or genres: {row}")
                    continue
                
                # Try to find cover image
                cover_image = None
                for ext in ['.jpg', '.png']:
                    image_path = os.path.join(covers_dir, f"{series_id}{ext}")
                    if os.path.exists(image_path):
                        cover_image = get_image_base64(image_path)
                        if cover_image:
                            logger.info(f"🖼️ Found cover image for series {series_title}")
                        break
                
                # Try to get existing series first
                series = get_series_by_title(db, series_title)
                if series is None:  # Series doesn't exist, create it
                    series = create_series(db, series_title, series_id, cover_image)
                    if series is None:
                        logger.error(f"❌ Failed to insert series: {series_title}")
                        continue
                    logger.info(f"✨ Created new series: {series_title} (ID: {series_id})")
                else:
                    # Update existing series with cover image if found
                    if cover_image:
                        try:
                            response = db.client.table('series').update({
                                'cover_image': cover_image
                            }).eq('id', series.id).execute()
                            if response.data:
                                logger.info(f"🖼️ Updated cover image for series: {series_title}")
                        except Exception as e:
                            logger.error(f"❌ Error updating cover image for {series_title}: {str(e)}")
                    logger.info(f"📺 Using existing series: {series_title}")
                
                # Process each genre
                genres = [genre.strip() for genre in genres_str.split(',')]
                for genre_name in genres:
                    if not genre_name:  # Skip empty genre names
                        continue
                    
                    # Get or create genre
                    genre = get_or_create_genre(db, genre_name)
                    if genre is None:
                        logger.error(f"❌ Failed to get or create genre: {genre_name}")
                        continue
                    
                    # Create series-genre relationship
                    try:
                        response = db.client.table('series_genres').insert({
                            'series_id': series.id,
                            'genre_id': genre.id
                        }).execute()
                        
                        if not response.data:
                            logger.error(f"❌ Failed to create relationship between {series_title} and {genre_name}")
                            continue
                            
                        logger.info(f"🔗 Created relationship: {series_title} - {genre_name}")
                    except Exception as e:
                        if 'duplicate key value' in str(e).lower():
                            logger.info(f"ℹ️ Relationship already exists: {series_title} - {genre_name}")
                            continue
                        logger.error(f"❌ Error creating relationship between {series_title} and {genre_name}: {str(e)}")
                        continue
                
                logger.info(f"✅ Processed series: {series_title}")
        
        logger.info("🎉 Import completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Error during import: {str(e)}")
        raise  # Re-raise the exception to see the full traceback
    finally:
        db.close()

if __name__ == "__main__":
    import_series_genres("series_genres.csv") 