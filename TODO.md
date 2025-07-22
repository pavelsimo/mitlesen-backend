# Spanish Language Support Implementation Plan

This document outlines the comprehensive plan to add Spanish language support to the Mitlesen backend system.

## Overview

The goal is to add Spanish ('es') as a supported language alongside the existing German ('de') and Japanese ('ja'/'jp') support. This will enable the system to:

- Process Spanish YouTube videos
- Generate Spanish transcripts using WhisperX
- Provide Spanish linguistic analysis and vocabulary extraction
- Support Spanish dictionary lookups
- Generate Spanish audio using ElevenLabs

## Current Architecture Analysis

### Language Support Framework
The Mitlesen backend uses a well-architected factory pattern for language-specific processing:

- **Base Classes**: Abstract interfaces (`BaseSegmenter`, `BaseTranscriptProcessor`, etc.)
- **Factory Functions**: Language resolution via `get_segmenter(language)`, `get_transcript_processor(language)`
- **Pipeline Integration**: Language-aware steps in the processing pipeline
- **AI Integration**: Language-specific prompts and processing instructions

### Existing Language Implementations

**German ('de')**:
- `GermanSentenceSegmenter` - spaCy-based sentence segmentation
- `GermanTranscriptProcessor` - dictionary lookups and text analysis
- Text normalization and linguistic preprocessing

**Japanese ('ja'/'jp')**:
- `JapaneseSentenceSegmenter` - Janome tokenization
- `JapaneseWordSplitter` - morphological analysis with phonetics
- `JapaneseTranscriptProcessor` - comprehensive Japanese text processing
- Romanization and phonetic analysis modules

## Implementation Plan

### Phase 1: Core NLP Infrastructure (High Priority)

#### 1.1 Create Spanish NLP Module Structure
**Target**: `mitlesen/nlp/spanish/`
```
spanish/
├── __init__.py
├── segmenter.py      # SpanishSentenceSegmenter
├── transcript_processor.py  # SpanishTranscriptProcessor
└── normalizer.py     # Spanish text normalization utilities
```

#### 1.2 Implement SpanishSentenceSegmenter
**File**: `mitlesen/nlp/spanish/segmenter.py`
- Inherit from `BaseSegmenter` 
- Handle Spanish sentence boundaries and punctuation rules
- Support Spanish question marks (¿?) and exclamation marks (¡!)
- Handle abbreviations and Spanish-specific sentence structures

#### 1.3 Implement SpanishTranscriptProcessor  
**File**: `mitlesen/nlp/spanish/transcript_processor.py`
- Inherit from `BaseTranscriptProcessor`
- Spanish text preprocessing and cleaning
- Integration with Spanish dictionary lookups
- Handle Spanish-specific text normalization

#### 1.4 Update Factory Functions
**File**: `mitlesen/nlp/__init__.py`
- Add 'es' support to `get_segmenter()` function
- Add 'es' support to `get_transcript_processor()` function
- Spanish doesn't need complex word splitting like Japanese

#### 1.5 Add Spanish AI Prompts
**File**: `mitlesen/prompts.py`
- Add Spanish entry to `LANGUAGE_SYSTEM_PROMPTS` dictionary
- Add Spanish function to `TRANSCRIPT_PROMPT_FACTORIES`
- Include Spanish grammatical features (gender, verb conjugation)
- Provide proper Spanish linguistic context for AI processing

### Phase 2: Pipeline Integration (Medium Priority)

#### 2.1 Configure Spanish WhisperX Settings
**File**: `mitlesen/pipeline/steps/transcribe.py`
- Add Spanish configuration to `WHISPER_CONFIGS` dictionary
- Set appropriate model and language parameters for Spanish
- Configure Spanish-specific transcription settings

#### 2.2 Update ElevenLabs Integration
**File**: `mitlesen/pipeline/steps/elevenlabs_transcribe.py`
- Add Spanish character count thresholds
- Configure Spanish-specific text segmentation for speech synthesis
- Ensure proper handling of Spanish accents and special characters

#### 2.3 Spanish Text Normalizer
**File**: `mitlesen/nlp/spanish/normalizer.py`
- Handle Spanish accents and diacritics (á, é, í, ó, ú, ñ)
- Process Spanish contractions and elisions
- Normalize punctuation and whitespace
- Handle Spanish-specific text cleaning requirements

### Phase 3: Dictionary & Advanced Features (Medium/Low Priority)

#### 3.1 Source Spanish Dictionary Data
**Research and Integration**:
- Identify reliable Spanish linguistic resources:
  - Spanish Wiktionary dumps
  - OpenCorpora Spanish corpus
  - FreeLing Spanish dictionary
  - Other open-source Spanish lexical resources
- Analyze data format and structure for integration

#### 3.2 Update Dictionary Processing
**File**: `create_dictionary.py`
- Add Spanish dictionary parser class
- Integrate Spanish dictionary data processing
- Handle Spanish-specific dictionary entry formats
- Support Spanish morphological information

#### 3.3 Spanish Morphological Analysis
**Enhancement Goals**:
- **Gender Agreement**: Noun and adjective gender marking (masculino/femenino)
- **Verb Conjugation**: Tense, mood, person analysis
- **Number Agreement**: Singular/plural forms
- **Lemmatization**: Reduce words to their base forms
- **Part-of-Speech**: Spanish-specific POS tagging

#### 3.4 Schema Considerations
**Database/Model Updates**:
- Current schema supports Spanish well (no special fields like Japanese romanji)
- Consider adding Spanish-specific grammatical fields:
  - Gender information for nouns/adjectives
  - Verb tense and mood information
  - Formality level (tú/usted distinctions)

### Phase 4: Testing & Validation (High Priority)

#### 4.1 End-to-End Pipeline Testing
- Test complete Spanish video processing pipeline
- Validate transcript quality and accuracy
- Verify linguistic analysis correctness
- Test dictionary integration and lookups

#### 4.2 Integration Testing
- Test Spanish language detection and routing
- Verify AI prompt effectiveness for Spanish content
- Test ElevenLabs Spanish speech synthesis
- Validate database storage and retrieval

## Technical Implementation Details

### Language Code Support
- Primary code: `'es'` (Spanish)
- Ensure compatibility with existing language detection logic
- Update all language enumeration and validation code

### Dependencies
- **spaCy Spanish Model**: For advanced NLP processing (`es_core_news_sm`)
- **Spanish Tokenization**: Consider NLTK Spanish punkt or spaCy
- **Dictionary Resources**: Integration with chosen Spanish lexical database

### Configuration Updates
- Environment variables for Spanish-specific settings
- Configuration files for Spanish processing parameters
- Language-specific logging and error handling

## Files to Create/Modify

### New Files
- `mitlesen/nlp/spanish/__init__.py`
- `mitlesen/nlp/spanish/segmenter.py`
- `mitlesen/nlp/spanish/transcript_processor.py`
- `mitlesen/nlp/spanish/normalizer.py`

### Modified Files
- `mitlesen/nlp/__init__.py` (factory functions)
- `mitlesen/prompts.py` (Spanish AI prompts)
- `mitlesen/pipeline/steps/transcribe.py` (WhisperX config)
- `mitlesen/pipeline/steps/elevenlabs_transcribe.py` (ElevenLabs config)
- `create_dictionary.py` (Spanish dictionary processing)

### Testing Files
- Unit tests for all Spanish NLP components
- Integration tests for Spanish pipeline
- Sample Spanish video processing tests

## Success Criteria

1. **Functional**: Complete Spanish video processing from YouTube URL to database storage
2. **Quality**: Accurate Spanish transcription and linguistic analysis
3. **Performance**: Spanish processing performance comparable to German/Japanese
4. **Maintainability**: Clean, well-documented code following existing patterns
5. **Extensibility**: Easy to add additional Spanish-specific features in the future

## Implementation Priority

**Phase 1** (Immediate): Core NLP infrastructure for basic Spanish support
**Phase 2** (Next): Pipeline integration for complete processing workflow  
**Phase 3** (Future): Advanced dictionary and morphological features
**Phase 4** (Ongoing): Comprehensive testing and validation

This plan provides a systematic approach to adding robust Spanish language support while maintaining the existing architecture's integrity and extensibility.