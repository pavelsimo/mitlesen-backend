# Repository Guidelines

## Project Structure & Module Organization
`mitlesen/` hosts the runtime package: AI clients (`ai.py`), Supabase access (`db.py`), dictionary helpers, and the ingestion pipeline in `pipeline/runner.py` and `pipeline/steps/`. Locale-specific NLP resources live under `mitlesen/nlp/<lang>/`. Automation scripts (`import_videos.py`, `update_videos_fields.py`, `create_dictionary.py`) consume CSV manifests in `data/`, while generated assets stay inside `data/videos/`, `data/covers/`, and related folders. Tests mirror the package in `tests/` with fixtures in `tests/conftest.py` and pipeline coverage under `tests/pipeline/`.

## Build, Test, and Development Commands
- `python -m venv .venv && source .venv/bin/activate` — prepare the virtualenv used by scripts.
- `pip install -r requirements.txt` — install runtime dependencies including WhisperX, Supabase, and spaCy.
- `python run_tests.py` — canonical entry point that runs pytest with verbose, short traces.
- `pytest tests/pipeline/steps/test_augment.py` — scope testing while iterating on augment logic.
- `python import_videos.py` — execute the full ingest pipeline using `videos_*.csv` manifests.

## Coding Style & Naming Conventions
Use PEP 8 defaults with four-space indentation, trailing commas where helpful, and type hints throughout. Keep functions and modules `snake_case`, classes `PascalCase`, and constants upper-case inside their module (`mitlesen/__init__.py`). Structure imports as standard library → third party → local and prefer f-strings for formatting. Reuse `mitlesen.logger.logger` for structured logs instead of printing directly.

## Testing Guidelines
Pytest is configured via `pytest.ini` to discover `test_*.py` files and `Test*` classes inside `tests/`. Add new cases adjacent to the feature, mocking external AI or Supabase calls to keep the suite deterministic. Async scenarios should use `pytest.mark.asyncio`; the project already sets `asyncio_mode=auto`. Run `python run_tests.py` before pushing and extend the targeted suites when modifying pipeline steps or locale NLP logic.

## Commit & Pull Request Guidelines
Follow the existing emoji-prefixed subject style (`🚧 add videos`, `✨ add spanish`): pick one emoji plus a short imperative summary under ~60 characters. Expand on rationale or breaking changes in the body when necessary. Pull requests should list the change summary, linked issues, environment or data prerequisites, and proof of `python run_tests.py`. Call out schema or CSV updates so downstream consumers can refresh data safely.

## Security & Configuration Tips
Secrets live in `.env` loaded by `python-dotenv`; supply `OPENAI_API_KEY`, `GEMINI_KEY`, `SUPABASE_URL`, and `SUPABASE_KEY`. Keep `.env` and generated media under `data/` out of version control. When sharing logs or bug reports, redact Supabase URLs and AI responses containing user content, and rotate keys immediately if they leak.
