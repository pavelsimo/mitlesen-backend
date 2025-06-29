# Code Simplification TODO

This document outlines areas where the Mitlesen backend codebase can be simplified and refactored for better maintainability.

## 1. Duplicate Exception Classes

**Issue**: Both `mitlesen/nlp/german/segmenter.py:13-22` and `mitlesen/nlp/japanese/segmenter.py:12-21` define identical `SentenceMatchError` classes.

**Solution**: 
- Move `SentenceMatchError` to `mitlesen/nlp/base.py` as a shared exception
- Update imports in both segmenter files

**Files affected**:
- `mitlesen/nlp/base.py` (add exception)
- `mitlesen/nlp/german/segmenter.py` (remove duplicate, import from base)
- `mitlesen/nlp/japanese/segmenter.py` (remove duplicate, import from base)

## 2. Redundant Dictionary Classes

**Issue**: Two separate dictionary implementations serve similar purposes:
- `mitlesen/db.py:297-437` - Supabase-based Dictionary class
- `mitlesen/dictionary.py:67-222` - SQLite-based BaseDictionary/SqliteDictionary

**Solution**:
- Create a common interface/abstract base class for dictionary operations
- Unify the API between both implementations
- Consider deprecating one implementation if they're truly redundant

**Files affected**:
- `mitlesen/db.py`
- `mitlesen/dictionary.py`
- Any files importing these classes

## 3. Complex Batch Processing Logic

**Issue**: The `AugmentStep.execute()` method in `mitlesen/pipeline/steps/augment.py:37-118` has overly complex nested loops and retry logic.

**Solution**:
- Extract batch creation logic into `_create_batches()` method
- Extract retry mechanism into `_process_batch_with_retry()` method
- Simplify the main processing loop
- Consider using a state machine pattern for retry logic

**Files affected**:
- `mitlesen/pipeline/steps/augment.py`

## 4. Repeated Database Connection Patterns

**Issue**: Multiple classes in `mitlesen/db.py` repeat the same pattern for database operations (insert with duplicate handling, fetch operations).

**Solution**:
- Create a `BaseSupabaseModel` class with common CRUD operations
- Implement methods like `_insert_with_duplicate_handling()`, `_fetch_by_field()`, etc.
- Refactor Video, Genre, Series, SeriesGenre, Dictionary classes to inherit from base

**Files affected**:
- `mitlesen/db.py`

## 5. Large Segmenter Classes

**Issue**: Both `GermanSentenceSegmenter` and `JapaneseSentenceSegmenter` have very similar `split_long_sentence` and `segment_transcripts` methods with only language-specific differences.

**Solution**:
- Move common logic to `BaseSegmenter` class
- Create abstract methods for language-specific operations:
  - `_get_sentence_endings()`
  - `_get_safe_split_chars()`
  - `_normalize_for_matching()`
- Implement template method pattern for `segment_transcripts()`

**Files affected**:
- `mitlesen/nlp/base.py`
- `mitlesen/nlp/german/segmenter.py`
- `mitlesen/nlp/japanese/segmenter.py`

## 6. Dictionary Parser Complexity

**Issue**: The `mitlesen/dictionary.py` file contains three large parser classes (424+ lines total) with complex methods.

**Solution**:
- Extract common parsing patterns into utility functions
- Break down large methods in `JapaneseJMDictParser` and `JapaneseWiktionaryParser`:
  - `_parse_pos_info()`
  - `_extract_text_content()`
  - `_build_meanings_list()`
- Create shared XML/JSON processing utilities
- Consider splitting parsers into separate files

**Files affected**:
- `mitlesen/dictionary.py`
- Possibly create new files: `mitlesen/parsers/` directory

## 7. AI Client Redundancy

**Issue**: The `CompletionClient` and `CompletionStreamClient` in `mitlesen/ai.py:15-143` have overlapping initialization logic.

**Solution**:
- Create a `BaseAIClient` class with shared initialization
- Extract common backend setup logic
- Consider using composition over inheritance for backend-specific behavior
- Unify configuration management

**Files affected**:
- `mitlesen/ai.py`

## Implementation Priority

1. **High Priority** (Quick wins):
   - Duplicate Exception Classes (#1)
   - AI Client Redundancy (#7)

2. **Medium Priority** (Moderate effort):
   - Complex Batch Processing Logic (#3)
   - Repeated Database Connection Patterns (#4)

3. **Low Priority** (Larger refactoring):
   - Redundant Dictionary Classes (#2)
   - Large Segmenter Classes (#5)
   - Dictionary Parser Complexity (#6)

## Notes

- All changes should include proper unit tests
- Consider backward compatibility when refactoring public APIs
- Update documentation after implementing changes
- Run full test suite after each refactoring to ensure no regression