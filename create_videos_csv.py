#!/usr/bin/env python3
"""
Create Videos CSV - YouTube Metadata Fetcher and Serie Matcher

Script to fetch YouTube video metadata without using YouTube API.
Extracts youtube_id, title, channel_name, and channel_handle for YouTube URLs.
Generates CSV output with proper quoting and uses AI to match videos to series.

Features:
- Fetches metadata using yt-dlp (no API required)
- Language detection based on channel handles
- AI-powered serie matching using Gemini
- Smart duplicate detection and incremental processing
- Supports input from command line, files, or defaults
"""

import argparse
import csv
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional
from yt_dlp import YoutubeDL
from yt_dlp.utils import DownloadError, ExtractorError

# Import AI client for serie matching
sys.path.append(str(Path(__file__).parent))
from mitlesen.ai import get_ai_client

# Channel handle to language mapping
CHANNEL_LANGUAGE_MAP = {
    "@netflixanime": "ja",
    "@CrunchyrollenEspañol": "es", 
    "@crunchyrolldeutschland": "de",
    "@CrunchyrollExtrasDeutschland": "de",
    "@crunchyroll": "ja",
    "@NetflixJP": "ja",
}

# Default YouTube URLs to process (can be overridden by command line)
DEFAULT_YOUTUBE_URLS = [
    "https://www.youtube.com/watch?v=Oz04oXzyN2Q",
    "https://www.youtube.com/watch?v=lYVFOSWbhmI"
]

def extract_video_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL."""
    patterns = [
        r'(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([a-zA-Z0-9_-]{11})',
        r'youtube\.com.*[?&]v=([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def detect_language(channel_handle: str) -> str:
    """Detect language based on channel handle."""
    # Normalize the handle to lowercase for matching
    handle_lower = channel_handle.lower()
    
    # Direct mapping
    if handle_lower in CHANNEL_LANGUAGE_MAP:
        return CHANNEL_LANGUAGE_MAP[handle_lower]
    
    # Fallback mappings for similar handles
    for mapped_handle, lang in CHANNEL_LANGUAGE_MAP.items():
        if mapped_handle.lower().replace("@", "") in handle_lower.replace("@", ""):
            return lang
    
    # Default fallback
    return "ja"  # Default to Japanese for unknown channels

def fetch_video_metadata(url: str) -> Optional[Dict[str, str]]:
    """Fetch metadata for a YouTube video using yt-dlp."""
    youtube_id = extract_video_id(url)
    if not youtube_id:
        print(f"Error: Could not extract video ID from URL: {url}", file=sys.stderr)
        return None
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'extract_flat': False,
        'writesubtitles': False,
        'writeautomaticsub': False,
        'writedescription': False,
        'writeinfojson': False,
        'writethumbnail': False,
        'skip_download': True,
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }
    
    try:
        with YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)
            
            # Extract required fields
            title = info.get('title', 'Unknown Title')
            channel_name = info.get('uploader', info.get('channel', 'Unknown Channel'))
            
            # Extract channel handle from various possible fields
            channel_handle = None
            if info.get('uploader_url'):
                # Extract handle from uploader URL like https://www.youtube.com/@crunchyroll
                handle_match = re.search(r'@([^/\s]+)', info['uploader_url'])
                if handle_match:
                    channel_handle = f"@{handle_match.group(1)}"
            
            if not channel_handle and info.get('channel_url'):
                # Extract handle from channel URL
                handle_match = re.search(r'@([^/\s]+)', info['channel_url'])
                if handle_match:
                    channel_handle = f"@{handle_match.group(1)}"
                    
            if not channel_handle:
                channel_handle = "Unknown Handle"
            
            # Detect language based on channel handle
            language = detect_language(channel_handle)
            
            return {
                'youtube_id': youtube_id,
                'title': title,
                'is_premium': 'false',  # Default to false as requested
                'serie_id': '-1',       # Default to -1, will be filled by AI
                'channel_name': channel_name,
                'channel_handle': channel_handle,
                'language': language
            }
            
    except (DownloadError, ExtractorError) as e:
        print(f"Error fetching metadata for {url}: {str(e)}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Unexpected error for {url}: {str(e)}", file=sys.stderr)
        return None

def load_series_data(series_file: str = "series_genres.csv") -> List[Dict[str, str]]:
    """Load series data from CSV file."""
    series_data = []
    try:
        with open(series_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                series_data.append({
                    'id': row['Id'],
                    'serie': row['Serie'],
                    'genres': row['Genres']
                })
    except FileNotFoundError:
        print(f"Warning: Series file {series_file} not found. AI matching will be disabled.", file=sys.stderr)
    return series_data

def save_to_csv(videos: List[Dict[str, str]], output_file: str = "videos.csv") -> None:
    """Save video metadata to CSV file with quotes around title and channel_name."""
    if not videos:
        print("No videos to save.", file=sys.stderr)
        return
    
    fieldnames = ['youtube_id', 'title', 'is_premium', 'serie_id', 'channel_name', 'channel_handle', 'language']
    
    with open(output_file, 'w', newline='', encoding='utf-8') as f:
        # Write header manually
        f.write(','.join(fieldnames) + '\n')
        
        # Write rows with manual quoting for specific fields
        for video in videos:
            row_values = []
            for field in fieldnames:
                value = video[field]
                # Add quotes to title and channel_name fields, escape any existing quotes
                if field in ['title', 'channel_name']:
                    # Escape any existing quotes in the value
                    escaped_value = value.replace('"', '""')
                    value = f'"{escaped_value}"'
                row_values.append(value)
            f.write(','.join(row_values) + '\n')
    
    print(f"✅ Saved {len(videos)} videos to {output_file}")

def load_from_csv(input_file: str) -> List[Dict[str, str]]:
    """Load video metadata from CSV file."""
    videos = []
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                videos.append(dict(row))
    except FileNotFoundError:
        print(f"CSV file {input_file} not found. Will create new file.", file=sys.stderr)
    return videos

def has_pending_serie_ids(videos: List[Dict[str, str]]) -> bool:
    """Check if any videos have serie_id = -1."""
    return any(video.get('serie_id') == '-1' for video in videos)

def create_serie_matching_prompt(videos: List[Dict[str, str]], series_data: List[Dict[str, str]]) -> str:
    """Create prompt for AI to match videos to series."""
    # Prepare videos list for AI
    videos_for_ai = []
    for video in videos:
        if video.get('serie_id') == '-1':
            videos_for_ai.append({
                'youtube_id': video['youtube_id'],
                'title': video['title'],
                'channel_name': video['channel_name']
            })
    
    # Prepare series list for AI
    series_for_ai = []
    for serie in series_data:
        series_for_ai.append({
            'id': serie['id'],
            'serie': serie['serie'],
            'genres': serie['genres']
        })
    
    prompt = f"""You are a video categorization expert. Your task is to match YouTube videos to anime series based on their titles.

AVAILABLE SERIES:
{json.dumps(series_for_ai, indent=2, ensure_ascii=False)}

VIDEOS TO MATCH:
{json.dumps(videos_for_ai, indent=2, ensure_ascii=False)}

For each video, analyze the title and determine which series it belongs to. Return a single JSON object with the youtube_id as key and the serie_id as value. If you cannot confidently match a video to any series, use -1 as the serie_id.

Rules:
1. Match videos to series based on anime title/character names in the video title
2. Be strict - only match if you're confident the video is about that specific anime
3. Consider character names, series titles, and context clues
4. Return ONLY a single JSON object (not an array) in this exact format: {{"youtube_id": "serie_id", "youtube_id2": "serie_id2"}}

CRITICAL: Your response must be a valid JSON object, not an array. Do not include any other text or explanation.

Example output for multiple videos:
{{"Oz04oXzyN2Q": "106", "lYVFOSWbhmI": "105"}}

Example output for single video:
{{"abc123": "42"}}"""

    return prompt

def match_series_with_ai(videos: List[Dict[str, str]], series_data: List[Dict[str, str]]) -> Dict[str, str]:
    """Use AI to match videos to series and return mapping."""
    try:
        # Get AI client
        client = get_ai_client('gemini')
        
        # Create prompt
        prompt = create_serie_matching_prompt(videos, series_data)
        
        print("🤖 Sending request to Gemini AI for serie matching...")
        
        # Make AI request
        response = client.complete(prompt)
        
        # Parse response
        try:
            parsed_response = json.loads(response)
            
            # Handle different response formats
            if isinstance(parsed_response, dict):
                # Expected format: {"youtube_id": "serie_id", ...}
                matching = parsed_response
                print(f"✅ AI returned {len(matching)} serie matches (dict format)")
            elif isinstance(parsed_response, list):
                # Handle array format: [{"youtube_id": "serie_id"}, ...]
                matching = {}
                for item in parsed_response:
                    if isinstance(item, dict):
                        matching.update(item)
                print(f"✅ AI returned {len(matching)} serie matches (converted from array format)")
            else:
                print(f"❌ Unexpected AI response format: {type(parsed_response)}", file=sys.stderr)
                print(f"Raw response: {response}", file=sys.stderr)
                return {}
            
            # Validate that we have youtube_id -> serie_id mappings
            valid_matches = {}
            for youtube_id, serie_id in matching.items():
                if isinstance(youtube_id, str) and isinstance(serie_id, str):
                    valid_matches[youtube_id] = serie_id
                else:
                    print(f"⚠️ Skipping invalid match: {youtube_id} -> {serie_id}", file=sys.stderr)
            
            return valid_matches
            
        except json.JSONDecodeError as e:
            print(f"❌ Failed to parse AI response: {e}", file=sys.stderr)
            print(f"Raw response: {response}", file=sys.stderr)
            return {}
            
    except Exception as e:
        print(f"❌ AI matching failed: {str(e)}", file=sys.stderr)
        return {}

def update_serie_ids(videos: List[Dict[str, str]], matching: Dict[str, str]) -> None:
    """Update serie_ids in videos list based on AI matching."""
    updated_count = 0
    print(f"🔍 Processing {len(matching)} AI matches: {matching}")
    
    for video in videos:
        youtube_id = video['youtube_id']
        if youtube_id in matching and matching[youtube_id] != '-1':
            old_serie_id = video['serie_id']
            new_serie_id = matching[youtube_id]
            video['serie_id'] = new_serie_id
            updated_count += 1
            print(f"  ✅ Updated {youtube_id}: {old_serie_id} -> {new_serie_id}")
        elif youtube_id in matching and matching[youtube_id] == '-1':
            print(f"  ⏭️ Skipped {youtube_id}: AI couldn't match")
        else:
            print(f"  ⏭️ No match found for {youtube_id}")
    
    print(f"✅ Updated {updated_count} videos with AI-matched serie IDs")

def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Create Videos CSV - Fetch YouTube metadata and generate CSV with AI-powered serie matching"
    )
    parser.add_argument(
        '--urls', '-u',
        nargs='+',
        help='YouTube URLs to process (space-separated)'
    )
    parser.add_argument(
        '--urls-file', '-f',
        type=str,
        help='File containing YouTube URLs (one per line)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='output.csv',
        help='Output CSV file (default: output.csv)'
    )
    parser.add_argument(
        '--series-file', '-s',
        type=str,
        default='series_genres.csv',
        help='Series data CSV file (default: series_genres.csv)'
    )
    parser.add_argument(
        '--skip-ai',
        action='store_true',
        help='Skip AI matching for serie IDs'
    )
    
    return parser.parse_args()

def get_urls_from_args(args) -> List[str]:
    """Get YouTube URLs from command line arguments."""
    urls = []
    
    if args.urls:
        urls.extend(args.urls)
    
    if args.urls_file:
        try:
            with open(args.urls_file, 'r') as f:
                file_urls = [line.strip() for line in f if line.strip()]
                urls.extend(file_urls)
        except FileNotFoundError:
            print(f"❌ URLs file not found: {args.urls_file}", file=sys.stderr)
    
    if not urls:
        print("ℹ️ No URLs provided, using default URLs")
        urls = DEFAULT_YOUTUBE_URLS
    
    return urls

def main():
    """Main function with enhanced CSV processing and AI matching."""
    args = parse_arguments()
    
    print("🎬 Create Videos CSV - YouTube Metadata Fetcher with AI Serie Matching")
    print("=" * 60)
    
    # Get URLs to process
    urls = get_urls_from_args(args)
    print(f"📝 Processing {len(urls)} URLs")
    
    # Check if output file exists and load existing data
    existing_videos = load_from_csv(args.output)
    existing_ids = {video['youtube_id'] for video in existing_videos}
    
    # Fetch metadata for new videos only
    new_videos = []
    for i, url in enumerate(urls, 1):
        youtube_id = extract_video_id(url)
        if youtube_id and youtube_id in existing_ids:
            print(f"[{i}/{len(urls)}] ⏭️ Skipping {youtube_id} (already processed)")
            continue
            
        print(f"[{i}/{len(urls)}] 🔍 Processing: {url}")
        metadata = fetch_video_metadata(url)
        
        if metadata:
            new_videos.append(metadata)
            print(f"✅ Extracted: {metadata['title']} ({metadata['language']})")
        else:
            print("❌ Failed to extract metadata")
    
    # Combine existing and new videos
    all_videos = existing_videos + new_videos
    
    if new_videos:
        print(f"\n💾 Saving {len(new_videos)} new videos to {args.output}")
        save_to_csv(all_videos, args.output)
    else:
        print("\n💾 No new videos to save")
    
    # AI matching for serie IDs
    if not args.skip_ai and has_pending_serie_ids(all_videos):
        print(f"\n🤖 AI Serie Matching")
        print("-" * 30)
        
        # Load series data
        series_data = load_series_data(args.series_file)
        
        if series_data:
            # Run AI matching
            matching = match_series_with_ai(all_videos, series_data)
            
            if matching:
                # Update videos with AI results
                update_serie_ids(all_videos, matching)
                
                # Save updated CSV
                print(f"💾 Saving updated CSV with AI-matched serie IDs")
                save_to_csv(all_videos, args.output)
            else:
                print("❌ AI matching returned no results")
        else:
            print(f"❌ Cannot perform AI matching: series file not available")
    elif args.skip_ai:
        print("\n⏭️ Skipping AI matching (--skip-ai flag)")
    else:
        print("\n✅ All videos already have serie IDs assigned")
    
    # Summary
    print(f"\n{'=' * 60}")
    print("📊 SUMMARY")
    print(f"Total videos processed: {len(all_videos)}")
    print(f"New videos added: {len(new_videos)}")
    
    pending_count = len([v for v in all_videos if v.get('serie_id') == '-1'])
    print(f"Videos with serie IDs: {len(all_videos) - pending_count}")
    print(f"Videos pending serie IDs: {pending_count}")
    print(f"Output file: {args.output}")
    print("🎉 Processing complete!")

if __name__ == "__main__":
    main()