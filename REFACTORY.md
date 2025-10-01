# NLP Refactoring & Test Audit Plan

## Goals
- Establish a coherent, extensible NLP architecture with consistent interfaces across languages.
- Eliminate duplicated logic between language packages, especially among the spaCy-based segmenters and transcript processors.
- Clarify dependency boundaries (spaCy, Janome, Jamdict, SqliteDictionary) and make heavy resources lazy or replaceable for tests.
- Replace brittle, outdated tests with coverage that exercises real behaviour using lightweight fixtures and dependency seams.

## Key Findings
- `mitlesen/nlp/base.py` defines abstract hooks, but concrete classes (e.g. `mitlesen/nlp/spanish/segmenter.py:1`, `mitlesen/nlp/german/segmenter.py:1`) reimplement nearly identical spaCy setup and chunking logic.
- Transcript processors in `mitlesen/nlp/german/transcript_processor.py:1` and `mitlesen/nlp/spanish/transcript_processor.py:1` duplicate dictionary access, POS matching, and string cleaning; Japanese diverges with a bespoke splitter that emits temporary `_` fields.
- `mitlesen/nlp/__init__.py:1` exposes ad-hoc factory functions instead of a registry; adding a language requires editing multiple `if/elif` ladders.
- Tests under `tests/nlp/` include outdated assumptions (e.g. `tests/nlp/test_base.py:7`, `tests/nlp/german/test_segmenter.py:1`) that still expect pre-refactor APIs or inspect source strings rather than behaviour; many mocks patch implementation details instead of using public seams.
- Heavy imports occur at instantiation time, causing tests to patch third-party modules extensively; there's no shared mechanism to substitute minimal models.

## Refactoring Roadmap
### Phase 0 – Baseline & Contracts
- Document desired public interfaces for segmenters, word splitters, and transcript processors (input/output schemas, error handling, logging expectations).
- Add lightweight dataclasses (e.g. `WordToken`, `Segment`) in `mitlesen/nlp/models.py` to standardise data passed between components.

### Phase 1 – Shared Infrastructure
- Introduce a `SpaCySegmenter` base class that encapsulates model loading, sentencizer setup, and `split_long_sentence` heuristics configurable via punctuation settings; make German and Spanish thin subclasses providing model name and punctuation preferences.
- Create a `DictionaryClient` helper wrapping `SqliteDictionary` usage (context-managed, language-aware search) to remove duplicated try/except patterns.

### Phase 2 – Language Package Simplification
- German/Spanish: reduce modules to `segmenter.py`, `normalizer.py`, `transcript_processor.py` plus optional utilities; ensure they import only through shared bases.
- Japanese: separate concerns by extracting timestamp merging and romanisation helpers to dedicated files, expose a higher-level `JapaneseProcessor` that orchestrates `JapaneseWordSplitter` + dictionary enrichment without temporary underscores.
- Move normalisers into a shared namespace (e.g. `mitlesen/nlp/normalizers.py`) with language-specific variants to reuse tests and documentation.

### Phase 3 – Factories & Configuration
- Replace the `if/elif` factories in `mitlesen/nlp/__init__.py` with a registry pattern (`LanguageRegistry.register(language="es", segmenter=..., transcript_processor=...)`).
- Allow dependency injection for external resources (spaCy model aliases, Jamdict, dictionaries) via configuration dataclasses or environment overrides, making it easier to stub in tests.

### Phase 4 – Error Handling & Logging
- Centralise `SentenceMatchError` usage and provide structured context (segment id, indices) to aid debugging.
- Normalise logging through `mitlesen.logger.logger` with consistent prefixes and levels; add debug-level hooks for alignment failures with optional tracing.

### Phase 5 – Documentation & Developer Ergonomics
- Update inline docstrings and README-style docs describing how to add a new language.
- Provide usage examples for segmenters and processors in `AGENTS.md`/developer docs once refactor stabilises.

## Testing Overhaul
- Scrap legacy tests that assert on implementation details; design new suites around the standardised dataclasses and registries.
- Create fixtures for minimal spaCy/Janome stand-ins (e.g. tokeniser stubs) instead of patching global imports; verify behaviour on synthetic transcripts covering alignment success/failure.
- Add regression tests for normalisers and dictionary lookup strategies per language, including accent/umlaut handling and kana/kanji conversions.
- Introduce integration tests that round-trip a sample transcript through `segmenter.segment_text`, `segmenter.segment_transcripts`, and `transcript_processor.preprocess_transcript`, asserting on structured outputs and IDs.
- Ensure coverage for factory/registry resolution errors and dependency injection fallbacks (missing models, lazy downloads skipped in tests).

## Dependencies & Tooling
- Evaluate whether small spaCy pipelines (e.g. `xx_sent_ud_sm`) suffice for tests to avoid downloads; mock download path only once in shared fixtures.
- Cache Jamdict and Janome resources across tests to reduce startup time, or gate heavy integrations behind optional markers.
- Leverage `pytest` markers (`@pytest.mark.slow`, `@pytest.mark.requires_spacy`) to separate fast unit tests from dependency-heavy integration runs.

## Deliverables
- Updated NLP package with shared infrastructure, per-language modules trimmed to essential specialisations, and documentation of public contracts.
- Revised `tests/` tree aligned with new interfaces, featuring realistic behaviour-driven cases and clear separation between fast unit coverage and heavier integration tests.
- Migration notes covering API changes for callers (e.g. pipeline code expecting existing segmenter outputs) and guidance for future language additions.
