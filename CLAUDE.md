# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

Mitlesen is a backend service for processing YouTube videos for language learning. It extracts audio, generates transcripts using Whisper, augments them with linguistic analysis (morphological analysis, pronunciation guides), and stores them in a Supabase database.

## Core Architecture

### Pipeline System
The main processing workflow is built around a modular pipeline pattern:

- **PipelineContext** (`mitlesen/pipeline/base.py`): Shared context object containing video metadata and file paths
- **PipelineStep** (`mitlesen/pipeline/base.py`): Abstract base class for pipeline operations
- **PipelineRunner** (`mitlesen/pipeline/runner.py`): Orchestrates the pipeline execution with graceful interruption handling

### Pipeline Steps (in order)
1. **DownloadStep**: Downloads YouTube audio using yt-dlp
2. **TranscribeStep**: Generates transcripts using WhisperX
3. **AugmentStep**: Adds linguistic analysis (vocabulary, morphology, pronunciation)
4. **UploadStep**: Stores results in Supabase database

### Language Processing
The NLP module (`mitlesen/nlp/`) provides language-specific text processing:

- **BaseTokenizer/BaseSegmenter/BaseWordSplitter** (`mitlesen/nlp/base.py`): Abstract interfaces
- **German**: Segmentation and normalization
- **Japanese**: Tokenization (Janome), romanization (Kakasi), phonetics, and segmentation

### Data Models
- **Video**: Main content entity with transcript and vocabulary
- **Dictionary**: Multilingual dictionary entries (German/Japanese)
- **Series/Genre**: Content categorization system

## Common Development Commands

### Main Pipeline
```bash
# Process videos from CSV file
python import_videos.py

# Create/update dictionary from source files
python create_dictionary.py

# Import series and genre data
python import_series_genres.py
```

### Dependencies
```bash
# IMPORTANT: Always use the virtual environment (Python 3.11)
.venv/bin/pip install -r requirements.txt

# Run Python scripts using the virtual environment
.venv/bin/python import_videos.py

# Key dependencies: openai, supabase, google-genai, whisperx, yt-dlp, janome, pykakasi, spacy
```

### Environment Setup
Required environment variables:
- `SUPABASE_URL` and `SUPABASE_KEY`: Database connection
- `OPENAI_API_KEY`: For AI completion (optional)
- `GEMINI_KEY`: For Gemini AI completion (default backend)

## Key File Locations

- `videos.csv`: Input file containing YouTube video metadata
- `data/videos/`: Working directory for audio files and transcripts
- `data/dictionaries/`: Dictionary source files and SQLite output
- `mitlesen/`: Main Python package
- `import_videos.py`: Main entry point for video processing

## Development Notes

### AI Backend Configuration
The system supports both OpenAI and Gemini backends (default: Gemini) configured in `mitlesen/ai.py`. The AI client is used for transcript augmentation with linguistic analysis.

### Database Operations
All database operations use Supabase with models in `mitlesen/db.py`. The system handles graceful failures and duplicate detection.

### Pipeline Interruption
The pipeline supports graceful interruption (Ctrl+C) and will finish the current video before stopping.

### File Naming Conventions
- Audio files: `{youtube_id}.mp3` or `{youtube_id}.wav`
- Transcripts: `{youtube_id}.json`
- Augmented transcripts: `{youtube_id}.json.2`