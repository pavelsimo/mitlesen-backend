#!/usr/bin/env python3
import os
import argparse
from yt_dlp import YoutubeDL



def download_audio(youtube_id: str, output_dir: str):
    """
    Download the audio of a YouTube video as an MP3 file.

    :param youtube_id: The YouTube video ID (e.g. "dQw4w9WgXcQ").
    :param output_dir: Directory where the MP3 will be saved.
    """

    os.makedirs(output_dir, exist_ok=True)
    url = f"https://www.youtube.com/watch?v={youtube_id}"

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': os.path.join(output_dir, f'{youtube_id}.%(ext)s'),
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',  # kbps
        }],
        'quiet': False,    # set to True to suppress output
        'no_warnings': True,
    }

    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def main():
    parser = argparse.ArgumentParser(
        description="Download YouTube video audio as MP3 using yt-dlp"
    )
    parser.add_argument(
        "youtube_id",
        help="YouTube video ID (e.g. 'dQw4w9WgXcQ')"
    )
    parser.add_argument(
        "output_dir",
        help="Directory to save the downloaded MP3 file"
    )
    args = parser.parse_args()

    download_audio(args.youtube_id, args.output_dir)


if __name__ == "__main__":
    main()
