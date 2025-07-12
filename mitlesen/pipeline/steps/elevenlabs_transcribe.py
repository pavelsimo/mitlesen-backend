import json
import os
from typing import Dict, List, Any
from io import BytesIO
from elevenlabs.client import ElevenLabs

from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger


def _should_split_segment(current_words, word_text, language, total_segment_length=None):
    """Check if we should split the current segment after adding this word."""
    import re
    
    # Always split on sentence endings (but not ellipsis)
    if word_text.endswith(('!', '?', '。', '！', '？')) or (word_text.endswith('.') and word_text != '...'):
        return True
    
    # Split on commas if the total segment would be long enough to warrant splitting
    comma_ending = re.compile(r'[,、]$')
    if comma_ending.search(word_text):
        char_threshold = 15 if language == 'ja' else 80
        
        # If we have total segment length info, use that for decision
        if total_segment_length is not None:
            return total_segment_length >= char_threshold
        
        # Fallback: check current accumulated segment length
        segment_text = ''.join(w.get('text', '') for w in current_words)
        return len(segment_text) >= char_threshold
    
    return False


def _create_segment(words, segment_id):
    """Create a segment from a list of words."""
    if not words:
        return None
    
    # Filter out spacing words for the words array, but keep them for text
    content_words = [w for w in words if w.get('type') != 'spacing']
    
    return {
        'id': segment_id,
        'text': ''.join(w.get('text', '') for w in words).strip(),
        'start': words[0].get('start', 0.0),
        'end': words[-1].get('end', 0.0),
        'words': [{'text': w.get('text', ''), 'start': w.get('start', 0.0), 'end': w.get('end', 0.0)} 
                 for w in content_words],
    }


def transform_elevenlabs_to_transcript(elevenlabs_response, language: str = 'de') -> List[Dict[str, Any]]:
    """Transform ElevenLabs API response to match TranscribeStep output format.
    
    Args:
        elevenlabs_response: Raw response from ElevenLabs API
        language: Language code ('de' for German, 'ja' for Japanese) for character thresholds
        
    Returns:
        List of segments split by sentences (punctuation) and speaker changes
    """
    # Convert response object to dictionary if needed
    if hasattr(elevenlabs_response, 'dict'):
        response_dict = elevenlabs_response.dict()
    elif hasattr(elevenlabs_response, 'model_dump'):
        response_dict = elevenlabs_response.model_dump()
    else:
        response_dict = dict(elevenlabs_response)
    
    words = response_dict.get('words', [])
    if not words:
        return []
    
    # Step 1: Group words into sentence-level segments first
    sentence_segments = _group_into_sentences(words)
    
    # Step 2: Split long sentences at commas if needed
    final_segments = []
    for sentence_words in sentence_segments:
        sub_segments = _split_long_sentence_at_commas(sentence_words, language)
        for sub_segment in sub_segments:
            segment = _create_segment(sub_segment, len(final_segments))
            if segment:
                final_segments.append(segment)
    
    return final_segments


def _group_into_sentences(words):
    """Group words into sentence-level segments based on punctuation and speaker changes."""
    sentences = []
    current_sentence = []
    current_speaker = None
    
    for word in words:
        word_text = word.get('text', '').strip()
        speaker_id = word.get('speaker_id', 'speaker_0')
        
        # Handle speaker changes (only for content words)
        if word.get('type') != 'spacing':
            if current_speaker is None:
                current_speaker = speaker_id
            elif current_speaker != speaker_id:
                # Speaker change - finish current sentence
                if current_sentence:
                    sentences.append(current_sentence)
                    current_sentence = []
                current_speaker = speaker_id
        
        # Add word to current sentence
        current_sentence.append(word)
        
        # Check for sentence endings
        if word.get('type') != 'spacing' and _is_sentence_ending(word_text):
            sentences.append(current_sentence)
            current_sentence = []
            current_speaker = None
    
    # Add final sentence if remaining
    if current_sentence:
        sentences.append(current_sentence)
    
    return sentences


def _is_sentence_ending(word_text):
    """Check if word ends a sentence."""
    return (word_text.endswith(('!', '?', '。', '！', '？')) or 
            (word_text.endswith('.') and word_text != '...'))


def _split_long_sentence_at_commas(sentence_words, language):
    """Split a sentence at commas if it's long enough."""
    if not sentence_words:
        return []
    
    # Calculate total sentence length
    total_text = ''.join(w.get('text', '') for w in sentence_words)
    char_threshold = 15 if language == 'ja' else 80
    
    # If sentence is short enough, don't split
    if len(total_text) < char_threshold:
        return [sentence_words]
    
    # Split at commas
    segments = []
    current_segment = []
    
    for word in sentence_words:
        word_text = word.get('text', '').strip()
        current_segment.append(word)
        
        # Split at comma (now we know the total sentence is long enough)
        if word_text.endswith((',', '、')):
            segments.append(current_segment)
            current_segment = []
    
    # Add remaining words as final segment
    if current_segment:
        segments.append(current_segment)
    
    return segments if segments else [sentence_words]


class ElevenLabsTranscribeStep(PipelineStep):
    """Transcription step using ElevenLabs API instead of WhisperX."""
    
    def __init__(self, name: str, model_id: str = "scribe_v1"):
        super().__init__(name)
        self.model_id = model_id
        self.client = ElevenLabs(api_key=os.getenv("ELEVENLABS_API_KEY"))
    
    def execute(self, context: PipelineContext) -> bool:
        logger.info(f"🔊 Starting ElevenLabs transcription for {context.youtube_id}")
        
        if context.transcript_path.exists():
            logger.warning(f"⚠️ Transcript already exists: {context.transcript_path}")
            return self.run_next(context)
        
        # check if raw elevenlabs response already exists to avoid expensive API calls
        raw_response_path = context.transcript_path.with_suffix('.elevenlabs.json')
        transcription_dict = None
        if raw_response_path.exists():
            logger.info(f"📄 Raw ElevenLabs response already exists: {raw_response_path}")
            try:
                with open(raw_response_path, 'r', encoding='utf-8') as f:
                    transcription_dict = json.load(f)
            except Exception as e:
                logger.warning(f"⚠️ Failed to load cached response: {str(e)}, calling API")
                transcription_dict = None

        # call API if we don't have cached response
        if transcription_dict is None:
            try:
                # Read audio file
                with open(context.audio_path, 'rb') as audio_file:
                    audio_data = BytesIO(audio_file.read())
                
                # Transcribe using ElevenLabs (supports 2-letter language codes directly)
                logger.info(f"Transcribing with ElevenLabs (language: {context.language})")
                transcription = self.client.speech_to_text.convert(
                    file=audio_data,
                    model_id=self.model_id,
                    tag_audio_events=False,
                    language_code=context.language,
                    diarize=True
                )
                
                # Convert response object to dictionary for JSON serialization
                if hasattr(transcription, 'dict'):
                    transcription_dict = transcription.dict()
                elif hasattr(transcription, 'model_dump'):
                    transcription_dict = transcription.model_dump()
                else:
                    # fallback: convert to dict manually
                    transcription_dict = dict(transcription)
                
                # save raw ElevenLabs response for caching
                with open(raw_response_path, 'w', encoding='utf-8') as f:
                    json.dump(transcription_dict, f, indent=2, ensure_ascii=False)
            except Exception as e:
                logger.error(f"❌ ElevenLabs API call failed: {str(e)}")
                return False
        
        try:
            # Transform to expected format with built-in sentence segmentation
            segments = transform_elevenlabs_to_transcript(transcription_dict, context.language)
            logger.info(f"ElevenLabs transcript transformed into {len(segments)} sentence segments")
            
            # Save in expected format
            context.transcript_path.write_text(
                json.dumps(segments, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            logger.info(f"✅ ElevenLabs transcription completed for {context.youtube_id}")
            return self.run_next(context)
            
        except Exception as e:
            logger.error(f"❌ ElevenLabs transcription processing failed: {str(e)}")
            return False