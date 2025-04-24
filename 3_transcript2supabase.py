import json
from dotenv import load_dotenv
from ai import fetch_transcript, improve_transcript, process_vocabulary
from db import MitLesenDatabase
from transcript import YouTubeTranscriptFetcher

load_dotenv()

TRANSCRIPT_CHUNK_SIZE = 20
VOCABULARY_CHUNK_SIZE = 2

def chunk_lines(lines, size):
    return [lines[i:i + size] for i in range(0, len(lines), size)]

def chunk_sentences(sentences, size):
    return [sentences[i:i + size] for i in range(0, len(sentences), size)]

def generate_sentence_id(video_index, sentence_index):
    return f"{video_index + 1}-{sentence_index + 1}"

def generate_word_id(sentence_id, word_index):
    return f"{sentence_id}-{word_index + 1}"

if __name__ == "__main__":
    db = MitLesenDatabase()

    # https://github.com/hyperaudio/hyperaudio-lite

    videos = [
        #{"youtube_id": "O2w9acaudd8", "title": "Shangri-La Frontier - Folge 1", "is_premium": False},
        #{"youtube_id": "t0SQPbD2F08", "title": "BLUE LOCK - Folge 1", "is_premium": False},
        {"youtube_id": "CvlVuSN_twQ", "title": "JUJUTSU KAISEN - Folge 1", "is_premium": False},
        # https://www.youtube.com/watch?v=O2w9acaudd8&t=514s
    ]

    yt = YouTubeTranscriptFetcher(language_code='de', preserve_formatting=True)

    for vid_index, video in enumerate(videos):
        youtube_id = video["youtube_id"]
        title = video["title"]
        is_premium = video["is_premium"]

        try:
            raw_transcript = yt.fetch(youtube_id)
            
            # Improve the transcript before processing
            improved_transcript = improve_transcript(youtube_id, raw_transcript)
            print(f"Improved transcript for {title}")
            
            # Split the improved transcript into chunks for processing
            transcript_lines = [line.strip() for line in improved_transcript.split('\n') if line.strip()]
            transcript_chunks = chunk_lines(transcript_lines, TRANSCRIPT_CHUNK_SIZE)
            
            # Process transcript for sentences in chunks
            all_sentences = []
            sent_count = 0
            
            for chunk_index, chunk_text_lines in enumerate(transcript_chunks):
                chunk_str = "\n".join(chunk_text_lines)
                print(f"Processing transcript chunk {chunk_index+1}/{len(transcript_chunks)}")
                
                parsed_chunk_str = fetch_transcript(youtube_id, chunk_str)
                if parsed_chunk_str:
                    parsed_chunk = json.loads(parsed_chunk_str)
                    
                    # Assign proper sentence IDs
                    for s_idx, sentence in enumerate(parsed_chunk["sentences"]):
                        sentence_id = generate_sentence_id(vid_index, sent_count + s_idx)
                        sentence["id"] = sentence_id
                    
                    all_sentences.extend(parsed_chunk["sentences"])
                    sent_count += len(parsed_chunk["sentences"])
            
            # Create final transcript JSON
            parsed_transcript = {
                "videoId": youtube_id,
                "sentences": all_sentences
            }
            
            print(f"Processed full transcript with {len(all_sentences)} sentences")
            
            # Process vocabulary in chunks
            all_words = []
            sentence_chunks = chunk_sentences(parsed_transcript["sentences"], VOCABULARY_CHUNK_SIZE)
            
            for chunk_index, sentence_chunk in enumerate(sentence_chunks):
                print(f"Processing vocabulary chunk {chunk_index+1}/{len(sentence_chunks)}")
                parsed_vocab_str = process_vocabulary(youtube_id, sentence_chunk)
                if parsed_vocab_str:
                    parsed_vocab = json.loads(parsed_vocab_str)
                    # Fix word IDs
                    for w_idx, word in enumerate(parsed_vocab["words"]):
                        sentence_id = word["sentenceId"]
                        word["id"] = generate_word_id(sentence_id, w_idx)
                    all_words.extend(parsed_vocab["words"])
            
            # Create final vocabulary JSON
            vocabulary = {
                "videoId": youtube_id,
                "words": all_words
            }
            
            # Insert both transcript and vocabulary
            db.insert(
                title=title,
                youtube_id=youtube_id,
                is_premium=is_premium,
                transcript=json.dumps(parsed_transcript),
                vocabulary=json.dumps(vocabulary)
            )

            print(f"✅ Inserted {title} with {len(parsed_transcript['sentences'])} sentences and {len(all_words)} words")
        except ValueError as err:
            print(f"❌ Error for {youtube_id}: {err}")
            continue

    db.close()
