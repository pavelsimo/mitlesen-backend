import re
import json
import sys
from typing import List, Dict, Tuple, Optional

# Regular expression to match SRT timestamp lines
SRT_TIME_REGEX = re.compile(r"(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})")

def srt_time_to_seconds(time_str: str) -> float:
    """Converts an SRT timestamp string (HH:MM:SS,ms) to seconds (float)."""
    hours, minutes, seconds_ms = time_str.split(':')
    seconds, milliseconds = seconds_ms.split(',')
    total_seconds = (
        int(hours) * 3600 +
        int(minutes) * 60 +
        int(seconds) +
        int(milliseconds) / 1000.0
    )
    return total_seconds

def parse_srt(filepath: str) -> List[Dict]:
    """
    Parses an SRT file into a list of subtitle entries.

    Each entry is a dictionary containing 'text', 'start', and 'end' times in seconds.
    Sorts entries by start time.
    """
    subtitles = []
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read().strip()
            blocks = re.split(r'\n\s*\n', content)

            for block in blocks:
                lines = block.strip().split('\n')
                if len(lines) >= 3:
                    index_str = lines[0]
                    time_line = lines[1]
                    text_lines = lines[2:]

                    if not index_str.isdigit():
                        if len(lines) > 3 and lines[1].isdigit() and SRT_TIME_REGEX.match(lines[2]):
                           time_line = lines[2]
                           text_lines = lines[3:]
                        else:
                           continue

                    time_match = SRT_TIME_REGEX.match(time_line)
                    if time_match:
                        start_str, end_str = time_match.groups()
                        start_time = srt_time_to_seconds(start_str)
                        end_time = srt_time_to_seconds(end_str)
                        # Handle cases where end time might be before start time in source
                        if end_time < start_time:
                            end_time = start_time # Set end = start for zero/negative duration
                        text = " ".join(line.strip() for line in text_lines).strip()

                        subtitles.append({
                            "text": text,
                            "start": start_time,
                            "end": end_time
                        })

    except FileNotFoundError:
        print(f"Error: File not found at {filepath}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Error parsing SRT file {filepath}: {e}", file=sys.stderr)
        sys.exit(1)

    # Ensure subtitles are sorted by start time
    subtitles.sort(key=lambda x: x['start'])
    return subtitles

def keep_letters_spaces_de(text: str) -> str:
    """
    Remove every character that is not a space, an ASCII letter, or a German-specific
    letter (ÄÖÜäöüß).

    Parameters
    ----------
    text : str
        The input string.

    Returns
    -------
    str
        The cleaned string containing only spaces plus A-Z, a-z, ÄÖÜäöüß.
    """
    # space added to the allowed set right after ß␠
    return re.sub(r'[^A-Za-zÄÖÜäöüß ]', '', text)

# ***** MODIFIED FUNCTION *****
def merge_subtitles(sentences: List[Dict], words: List[Dict]) -> List[Dict]:
    """
    Merges word subtitles into sentence subtitles based on time ranges,
    assigning words based on their midpoint falling within the effective
    sentence time range [sentence_start_time, match_end_time).

    Args:
        sentences: List of sentence subtitle dictionaries, pre-processed with
                   'match_end_time'.
        words: List of word subtitle dictionaries.

    Returns:
        A list of sentence dictionaries, each containing a 'words' list,
        using the *original* sentence start/end times in the output.
    """
    merged_data = []
    word_index = 0 # Optimization: track the last matched word index
    sentence_index = 0

    while sentence_index < len(sentences):
        sentence = sentences[sentence_index]

        sentence_start = sentence['start']
        sentence_end = sentence['end']
        if sentence_index + 1 < len(sentences):
            next_sentence = sentences[sentence_index + 1]
            sentence_end = next_sentence['start']
        sentence_text = keep_letters_spaces_de(sentence['text']).lower()
        sentence_words = []
        sentence_pos = 0
        print('>> ', sentence_text, sentence_start, sentence_end)

        while word_index < len(words):
            word = words[word_index]
            word_text = keep_letters_spaces_de(word['text']).lower()
            word_start = word['start']
            word_end = word['end']
            print(word_text, word_start, word_end)

            idx = sentence_text.find(word_text, sentence_pos)
            if idx == -1:
                break
            sentence_words.append({"word": word_text, "start": word_start, "end": word_end})
            sentence_pos = idx + len(word_text)
            word_index += 1



        merged_data.append({
            "sentence": sentence_text,
            "start": sentence['start'], # Original start time
            "end": sentence['end'],     # Original end time
            "words": sentence_words
        })
        sentence_index += 1

    #
    # for sentence in sentences:
    #     sentence_start_time = sentence['start']
    #     match_end_time = sentence['match_end_time'] # Effective end for matching
    #     sentence_text = sentence['text']
    #     sentence_words = []
    #
    #     # Iterate through words starting from the last relevant index
    #     temp_word_index = word_index
    #     while temp_word_index < len(words):
    #         word_data = words[temp_word_index]
    #         word_start = word_data['start']
    #         word_end = word_data['end']
    #         word_text = word_data['text']
    #
    #         # Ensure end is not before start (can happen in source data)
    #         if word_end < word_start:
    #             word_end = word_start
    #
    #         # ***** MIDPOINT LOGIC *****
    #         # Calculate the midpoint of the word's duration.
    #         word_midpoint = (word_start + word_end) / 2.0
    #
    #         # Check if the word's midpoint falls within the effective sentence interval:
    #         # [sentence_start_time, match_end_time)
    #         # The interval is inclusive of the start and exclusive of the end (match_end_time).
    #         if word_midpoint >= sentence_start_time and word_midpoint < match_end_time:
    #              # Check if this word is the *first* match for this sentence
    #              if not sentence_words:
    #                  # Update the main word_index
    #                  word_index = temp_word_index
    #
    #              sentence_words.append({
    #                 "word": word_text,
    #                 "start": word_start,
    #                 "end": word_end
    #              })
    #         # Optimization: If the word starts *at or after* the effective end time,
    #         # its midpoint will also be >= match_end_time (unless it has zero/neg duration,
    #         # which is handled), so we can stop searching for *this* sentence.
    #         elif word_start >= match_end_time:
    #              break
    #
    #         temp_word_index += 1
    #
    #     # Append the final structure using the ORIGINAL sentence start/end times
    #     merged_data.append({
    #         "sentence": sentence_text,
    #         "start": sentence['start'], # Original start time
    #         "end": sentence['end'],     # Original end time
    #         "words": sentence_words
    #     })

    return merged_data

def main():
    """
    Main function to parse arguments, process SRT files, and print JSON output.
    """
    if len(sys.argv) != 3:
        print("Usage: python merge_srt.py <sentences_srt_filepath> <words_srt_filepath>", file=sys.stderr)
        sys.exit(1)

    sentences_filepath = sys.argv[1]
    words_filepath = sys.argv[2]

    # Parse both SRT files
    print(f"Parsing sentences from: {sentences_filepath}", file=sys.stderr)
    sentences_data = parse_srt(sentences_filepath)
    print(f"Parsed {len(sentences_data)} sentences.", file=sys.stderr)

    print(f"Parsing words from: {words_filepath}", file=sys.stderr)
    words_data = parse_srt(words_filepath) # Also sort words by start time
    print(f"Parsed {len(words_data)} words.", file=sys.stderr)

    if not sentences_data:
        print("Warning: No sentences found in the sentences SRT file.", file=sys.stderr)
        print("[]")
        sys.exit(0)
    if not words_data:
        print("Warning: No words found in the words SRT file.", file=sys.stderr)

    # Pre-processing Step: Calculate effective end times for matching
    print("Pre-processing sentence time boundaries for matching...", file=sys.stderr)
    if sentences_data: # Check list is not empty
        for i in range(len(sentences_data) - 1):
            # Effective end for sentence 'i' is start of sentence 'i+1'
            sentences_data[i]['match_end_time'] = sentences_data[i+1]['start']
            # Basic sanity check for ordering after sort
            if sentences_data[i+1]['start'] < sentences_data[i]['start']:
                 print(f"Warning: Sentences may not be strictly time-ordered between index {i} and {i+1} despite sorting. Results might be affected.", file=sys.stderr)

        # Last sentence uses its own end time
        sentences_data[-1]['match_end_time'] = sentences_data[-1]['end']

        # Add a small epsilon to the very last sentence's match_end_time
        # to include words ending exactly at the boundary, consistent with
        # the '< match_end_time' logic used elsewhere.
        # Check if it's different from start time to avoid issues with zero-duration subs
        if sentences_data[-1]['end'] > sentences_data[-1]['start']:
             sentences_data[-1]['match_end_time'] += 0.0001 # Add tiny fraction of a millisecond


    # Merge the data using the midpoint matching logic
    print("Merging words into sentences using midpoint logic...", file=sys.stderr)
    merged_output = merge_subtitles(sentences_data, words_data)
    print("Merging complete.", file=sys.stderr)

    # Output the result as JSON
    print(json.dumps(merged_output, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()

# #!/usr/bin/env python3
# import argparse
# import json
# import re
# from datetime import datetime
#
# def srt_time_to_seconds(srt_time: str) -> float:
#     """
#     Convert an SRT timestamp (e.g. "00:00:28,020") into seconds.
#     """
#     dt = datetime.strptime(srt_time, "%H:%M:%S,%f")
#     return dt.hour * 3600 + dt.minute * 60 + dt.second + dt.microsecond / 1_000_000
#
# def parse_srt(srt_path: str) -> list[dict]:
#     """
#     Parse a word-by-word SRT file into a list of dicts:
#       { "word": "...", "start": 0.123, "end": 0.456 }
#     """
#     with open(srt_path, encoding='utf-8') as f:
#         content = f.read()
#     # Split into blocks by blank line
#     blocks = re.split(r'\n\s*\n', content.strip())
#     word_entries = []
#     for block in blocks:
#         lines = block.strip().splitlines()
#         if len(lines) < 2:
#             continue
#         # The second line is the timestamp
#         timestamp = lines[1]
#         match = re.match(r'(\d{2}:\d{2}:\d{2},\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2},\d{3})', timestamp)
#         if not match:
#             continue
#         start_s, end_s = match.groups()
#         start = srt_time_to_seconds(start_s)
#         end   = srt_time_to_seconds(end_s)
#         # The rest of the lines form the subtitle text
#         text = " ".join(line.strip() for line in lines[2:])
#         # Split into words and strip punctuation
#         for w in text.split():
#             clean = w.strip('.,!?:;"“”()[]')
#             if clean:
#                 word_entries.append({
#                     "word": clean,
#                     "start": round(start, 3),
#                     "end":   round(end,   3)
#                 })
#     return word_entries
#
# def main():
#     parser = argparse.ArgumentParser(
#         description="Turn a .txt transcript + word-by-word .srt into a JSON with per-word timing."
#     )
#     parser.add_argument("transcript_txt", help="Path to the transcript .txt file")
#     parser.add_argument("words_srt",       help="Path to the word-by-word .srt file")
#     parser.add_argument("output_json",     help="Path where the output .json should be written")
#     args = parser.parse_args()
#
#     # Read full transcript
#     with open(args.transcript_txt, encoding='utf-8') as f:
#         transcript = f.read().strip()
#
#     # Parse the SRT into word entries
#     words = parse_srt(args.words_srt)
#
#     # Build the final structure
#     out = {
#         "transcript": transcript,
#         "words": words
#     }
#
#     # Write JSON
#     with open(args.output_json, 'w', encoding='utf-8') as f:
#         json.dump(out, f, ensure_ascii=False, indent=2)
#
#     print(f"Wrote {len(words)} words into {args.output_json}")
#
# if __name__ == "__main__":
#     main()
