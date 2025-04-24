#!/usr/bin/env python3
import argparse
import json
import re
from datetime import datetime

def srt_time_to_seconds(srt_time: str) -> float:
    """
    Convert an SRT timestamp (e.g. "00:00:28,020") into seconds.
    """
    dt = datetime.strptime(srt_time, "%H:%M:%S,%f")
    return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1_000_000

def parse_srt(srt_path: str) -> list[dict]:
    """
    Parse a word-by-word SRT file into a list of dicts:
      { "word": "...", "start": 0.123, "end": 0.456 }
    """
    with open(srt_path, encoding='utf-8') as f:
        content = f.read()
    # Split into blocks by blank line
    blocks = re.split(r'\n\s*\n', content.strip())
    word_entries = []
    for block in blocks:
        lines = block.strip().splitlines()
        if len(lines) < 2:
            continue
        # The second line is the timestamp
        timestamp = lines[1]
        match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp)
        if not match:
            continue
        start_s, end_s = match.groups()
        start = srt_time_to_seconds(start_s)
        end   = srt_time_to_seconds(end_s)
        # The rest of the lines form the subtitle text
        text = " ".join(line.strip() for line in lines[2:])
        # Split into words and strip punctuation
        for w in text.split():
            clean = w.strip('.,!?:;"“”()[]')
            if clean:
                word_entries.append({
                    "word": clean,
                    "start": round(start, 3),
                    "end":   round(end,   3)
                })
    return word_entries

def main():
    parser = argparse.ArgumentParser(
        description="Turn a .txt transcript + word-by-word .srt into a JSON with per-word timing."
    )
    parser.add_argument("transcript_txt", help="Path to the transcript .txt file")
    parser.add_argument("words_srt",       help="Path to the word-by-word .srt file")
    parser.add_argument("output_json",     help="Path where the output .json should be written")
    args = parser.parse_args()

    # Read full transcript
    with open(args.transcript_txt, encoding='utf-8') as f:
        transcript = f.read().strip()

    # Parse the SRT into word entries
    words = parse_srt(args.words_srt)

    # Build the final structure
    out = {
        "transcript": transcript,
        "words": words
    }

    # Write JSON
    with open(args.output_json, 'w', encoding='utf-8') as f:
        json.dump(out, f, ensure_ascii=False, indent=2)

    print(f"Wrote {len(words)} words into {args.output_json}")

if __name__ == "__main__":
    main()
