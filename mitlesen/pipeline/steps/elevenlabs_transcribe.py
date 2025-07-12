import json
import os
from typing import Dict, List, Any
from io import BytesIO
from elevenlabs.client import ElevenLabs

from mitlesen.pipeline.base import PipelineStep, PipelineContext
from mitlesen.logger import logger
from mitlesen.nlp import get_segmenter


# Language code mapping from 2-letter to 3-letter codes for ElevenLabs
LANGUAGE_CODE_MAPPING = {
    'ja': 'jpn',
    'de': 'deu',
    'en': 'eng',
    'es': 'spa',
    'fr': 'fra',
    'it': 'ita',
    'pt': 'por',
    'ru': 'rus',
    'zh': 'zho',
    'ko': 'kor',
    'ar': 'ara',
    'hi': 'hin',
    'th': 'tha',
    'vi': 'vie',
    'pl': 'pol',
    'nl': 'nld',
    'tr': 'tur',
    'sv': 'swe',
    'da': 'dan',
    'no': 'nor',
    'fi': 'fin',
    'hu': 'hun',
    'cs': 'ces',
    'sk': 'slk',
    'uk': 'ukr',
    'bg': 'bul',
    'hr': 'hrv',
    'sr': 'srp',
    'sl': 'slv',
    'et': 'est',
    'lv': 'lav',
    'lt': 'lit',
    'ro': 'ron',
    'el': 'ell',
    'he': 'heb',
    'fa': 'fas',
    'ur': 'urd',
    'bn': 'ben',
    'ta': 'tam',
    'te': 'tel',
    'ml': 'mal',
    'kn': 'kan',
    'gu': 'guj',
    'pa': 'pan',
    'mr': 'mar',
    'ne': 'nep',
    'si': 'sin',
    'my': 'mya',
    'km': 'khm',
    'lo': 'lao',
    'ka': 'kat',
    'am': 'amh',
    'sw': 'swa',
    'zu': 'zul',
    'af': 'afr',
    'is': 'isl',
    'mt': 'mlt',
    'cy': 'cym',
    'ga': 'gle',
    'gd': 'gla',
    'br': 'bre',
    'eu': 'eus',
    'ca': 'cat',
    'gl': 'glg',
    'oc': 'oci',
    'co': 'cos',
    'rm': 'roh',
    'lb': 'ltz',
    'fo': 'fao',
    'kl': 'kal',
    'se': 'sme',
    'yo': 'yor',
    'ig': 'ibo',
    'ha': 'hau',
    'xh': 'xho',
    'st': 'sot',
    'tn': 'tsn',
    'ts': 'tso',
    'ss': 'ssw',
    'nr': 'nbl',
    've': 'ven',
    'nd': 'nde',
    'lg': 'lug',
    'rw': 'kin',
    'rn': 'run',
    'ny': 'nya',
    'sn': 'sna',
    'mg': 'mlg',
    'ti': 'tir',
    'so': 'som',
    'or': 'ori',
    'as': 'asm',
    'ks': 'kas',
    'sd': 'snd',
    'ps': 'pus',
    'dv': 'div',
    'bo': 'bod',
    'ug': 'uig',
    'mn': 'mon',
    'hy': 'hye',
    'az': 'aze',
    'kk': 'kaz',
    'ky': 'kir',
    'tg': 'tgk',
    'tk': 'tuk',
    'uz': 'uzb',
    'tt': 'tat',
    'ba': 'bak',
    'cv': 'chv',
    'sah': 'sah',
    'ce': 'che',
    'av': 'ava',
    'lez': 'lez',
    'kbd': 'kbd',
    'ady': 'ady',
    'krc': 'krc',
    'kum': 'kum',
    'nog': 'nog',
    'kv': 'kom',
    'udm': 'udm',
    'mdf': 'mdf',
    'myv': 'myv',
    'mhr': 'mhr',
    'mrj': 'mrj',
    'chm': 'chm',
    'kpv': 'kpv',
    'koi': 'koi',
    'mns': 'mns',
    'kca': 'kca',
    'nio': 'nio',
    'yrk': 'yrk',
    'eve': 'eve',
    'evn': 'evn',
    'nan': 'nan',
    'chg': 'chg',
    'cjs': 'cjs',
    'kjh': 'kjh',
    'alt': 'alt',
    'tuv': 'tuv',
    'tyv': 'tyv',
    'bua': 'bua',
    'xal': 'xal',
    'kha': 'kha',
    'lus': 'lus',
    'grt': 'grt',
    'sat': 'sat',
    'brx': 'brx',
    'kok': 'kok',
    'mai': 'mai',
    'mag': 'mag',
    'bho': 'bho',
    'awa': 'awa',
    'raj': 'raj',
    'hne': 'hne',
    'gom': 'gom',
    'sa': 'san',
    'pi': 'pli',
    'pra': 'pra',
    'new': 'new',
    'bpy': 'bpy',
    'mni': 'mni',
    'lep': 'lep',
    'dz': 'dzo',
    'ii': 'iii',
    'za': 'zha',
    'iu': 'iku',
    'kl': 'kal',
    'mi': 'mri',
    'haw': 'haw',
    'ty': 'tah',
    'sm': 'smo',
    'to': 'ton',
    'fj': 'fij',
    'bi': 'bis',
    'ho': 'hmo',
    'kg': 'kon',
    'ak': 'aka',
    'tw': 'twi',
    'bm': 'bam',
    'dyu': 'dyu',
    'ff': 'ful',
    'wo': 'wol',
    'sg': 'sag',
    'ln': 'lin',
    'lua': 'lua',
    'luo': 'luo',
    'gaa': 'gaa',
    'ee': 'ewe',
    'kr': 'kau',
    'din': 'din',
    'nus': 'nus',
    'teo': 'teo',
    'lgg': 'lgg',
    'acholi': 'ach',
    'mas': 'mas',
    'kik': 'kik',
    'kam': 'kam',
    'mer': 'mer',
    'luy': 'luy',
    'guz': 'guz',
    'kln': 'kln',
    'luo': 'luo',
}


def get_elevenlabs_language_code(language: str) -> str:
    """Convert 2-letter language code to 3-letter code for ElevenLabs API.
    
    Args:
        language: 2-letter language code (e.g., 'ja', 'de')
        
    Returns:
        3-letter language code for ElevenLabs API (e.g., 'jpn', 'deu')
    """
    return LANGUAGE_CODE_MAPPING.get(language.lower(), 'eng')  # Default to English


def transform_elevenlabs_to_transcript(elevenlabs_response) -> List[Dict[str, Any]]:
    """Transform ElevenLabs API response to match TranscribeStep output format.
    
    Args:
        elevenlabs_response: Raw response from ElevenLabs API
        
    Returns:
        List of segments in the format expected by the pipeline
    """
    # Convert response object to dictionary if needed
    if hasattr(elevenlabs_response, 'dict'):
        response_dict = elevenlabs_response.dict()
    elif hasattr(elevenlabs_response, 'model_dump'):
        response_dict = elevenlabs_response.model_dump()
    else:
        response_dict = dict(elevenlabs_response)
    
    words = response_dict.get('words', [])
    
    # Group words into segments based on speaker changes and pauses
    segments = []
    current_segment = []
    current_speaker = None
    segment_start = None
    
    for word in words:
        word_start = word.get('start', 0.0)
        word_end = word.get('end', 0.0)
        word_text = word.get('text', '')
        speaker_id = word.get('speaker_id', 'speaker_0')
        
        # Start new segment if speaker changes or if there's a long pause
        if current_speaker is None:
            current_speaker = speaker_id
            segment_start = word_start
        elif current_speaker != speaker_id or (current_segment and word_start - current_segment[-1]['end'] > 2.0):
            # Finish current segment
            if current_segment:
                segment_text = ' '.join([w['text'] for w in current_segment])
                segments.append({
                    'id': len(segments),
                    'text': segment_text,
                    'start': segment_start,
                    'end': current_segment[-1]['end'],
                    'words': current_segment,
                })
            # Start new segment
            current_segment = []
            current_speaker = speaker_id
            segment_start = word_start
        
        # Add word to current segment
        current_segment.append({
            'text': word_text,
            'start': word_start,
            'end': word_end,
        })
    
    # Add final segment
    if current_segment:
        segment_text = ' '.join([w['text'] for w in current_segment])
        segments.append({
            'id': len(segments),
            'text': segment_text,
            'start': segment_start,
            'end': current_segment[-1]['end'],
            'words': current_segment,
        })
    
    return segments


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
        
        try:
            # Read audio file
            with open(context.audio_path, 'rb') as audio_file:
                audio_data = BytesIO(audio_file.read())
            
            # Get ElevenLabs language code
            elevenlabs_language = get_elevenlabs_language_code(context.language)
            
            # Transcribe using ElevenLabs
            logger.info(f"Transcribing with ElevenLabs (language: {elevenlabs_language})")
            transcription = self.client.speech_to_text.convert(
                file=audio_data,
                model_id=self.model_id,
                tag_audio_events=False,
                language_code=elevenlabs_language,
                diarize=True
            )
            
            # Convert response object to dictionary for JSON serialization
            if hasattr(transcription, 'dict'):
                transcription_dict = transcription.dict()
            elif hasattr(transcription, 'model_dump'):
                transcription_dict = transcription.model_dump()
            else:
                # Fallback: convert to dict manually
                transcription_dict = dict(transcription)
            
            # Save raw ElevenLabs response for debugging
            raw_response_path = context.transcript_path.with_suffix('.elevenlabs.json')
            with open(raw_response_path, 'w', encoding='utf-8') as f:
                json.dump(transcription_dict, f, indent=2, ensure_ascii=False)
            
            # Transform to expected format
            segments = transform_elevenlabs_to_transcript(transcription)
            
            # Apply sentence segmentation for supported languages
            try:
                segmenter = get_segmenter(context.language)
                segments = segmenter.segment_transcripts(segments)
                logger.info(f"Applied {context.language} sentence segmentation")
            except ValueError as e:
                logger.info(f"No segmentation available for {context.language}: {e}")
                # Continue without segmentation for unsupported languages
            
            # Save in expected format
            context.transcript_path.write_text(
                json.dumps(segments, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            logger.info(f"✅ ElevenLabs transcription completed for {context.youtube_id}")
            return self.run_next(context)
            
        except Exception as e:
            logger.error(f"❌ ElevenLabs transcription failed: {str(e)}")
            return False