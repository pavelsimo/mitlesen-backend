#!/usr/bin/env python3
import os
import argparse
from yt_dlp import YoutubeDL

def download_audio(youtube_id: str, output_dir: str):
    """
    Download the audio of a YouTube video as a 16 kHz WAV file.

    :param youtube_id: The YouTube video ID (e.g. "dQw4w9WgXcQ").
    :param output_dir: Directory where the WAV will be saved.
    """

    os.makedirs(output_dir, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={youtube_id}"
    outtmpl = os.path.join(output_dir, youtube_id)
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": outtmpl,
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                # quality param is ignored for WAV, but left here for consistency
                "preferredquality": "192",
            }
        ],
        # Tell ffmpeg to resample to 16 kHz
        "postprocessor_args": [
            "-ar", "16000"
        ],
        "quiet": False,
        "no_warnings": True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])

def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube audio as 16 kHz WAV using yt-dlp"
    )
    parser.add_argument(
        "youtube_id",
        help="YouTube video ID (e.g. 'dQw4w9WgXcQ')"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save the downloaded WAV file"
    )
    args = parser.parse_args()

    download_audio(args.youtube_id, args.output_dir)

if __name__ == "__main__":
    main()
