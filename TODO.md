# Code Simplification TODO

This document outlines areas where the Mitlesen backend codebase can be simplified and refactored for better maintainability.

## 1. Duplicate Exception Classes [DONE]

**Issue**: Both `mitlesen/nlp/german/segmenter.py:13-22` and `mitlesen/nlp/japanese/segmenter.py:12-21` define identical `SentenceMatchError` classes.

**Solution**: 
- [DONE] Move `SentenceMatchError` to `mitlesen/nlp/base.py` as a shared exception
- [DONE] Update imports in both segmenter files

**Files affected**:
- [DONE] `mitlesen/nlp/base.py` (add exception)
- [DONE] `mitlesen/nlp/german/segmenter.py` (remove duplicate, import from base)
- [DONE] `mitlesen/nlp/japanese/segmenter.py` (remove duplicate, import from base)

## 2. Redundant Dictionary Classes [DONE]

**Issue**: Two separate dictionary implementations serve similar purposes:
- `mitlesen/db.py:297-437` - Supabase-based Dictionary class
- `mitlesen/dictionary.py:67-222` - SQLite-based BaseDictionary/SqliteDictionary

**Solution**:
- [DONE] Create a common interface/abstract base class for dictionary operations (`BaseDictionaryInterface`)
- [DONE] Unify the API between both implementations with consistent method signatures
- [DONE] Add `SupabaseDictionary` wrapper class that implements the unified interface
- [DONE] Update type annotations to use consistent types (`List[Dict[str, Any]]`)
- [DONE] Preserve backward compatibility with existing `Dictionary` class

**Files affected**:
- [DONE] `mitlesen/db.py` (added `SupabaseDictionary` class)
- [DONE] `mitlesen/dictionary.py` (added `BaseDictionaryInterface`, updated type annotations)
- [DONE] Any files importing these classes (can now use either implementation interchangeably)

## 3. Complex Batch Processing Logic [DONE]

**Issue**: The `AugmentStep.execute()` method in `mitlesen/pipeline/steps/augment.py:37-118` has overly complex nested loops and retry logic.

**Solution**:
- [DONE] Extract batch creation logic into `_create_batches()` method
- [DONE] Extract retry mechanism into `_process_batch_with_retry()` method
- [DONE] Simplify the main processing loop
- [DONE] Consider using a state machine pattern for retry logic

**Files affected**:
- [DONE] `mitlesen/pipeline/steps/augment.py`

## 4. Repeated Database Connection Patterns [DONE]

**Issue**: Multiple classes in `mitlesen/db.py` repeat the same pattern for database operations (insert with duplicate handling, fetch operations).

**Solution**:
- [DONE] Create a `BaseSupabaseModel` class with common CRUD operations
- [DONE] Implement methods like `_insert_with_duplicate_handling()`, `_fetch_by_field()`, etc.
- [DONE] Refactor Video, Genre, Series, SeriesGenre, Dictionary classes to inherit from base

**Files affected**:
- [DONE] `mitlesen/db.py`

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

## 6. Dictionary Parser Complexity [DONE]

**Issue**: The `mitlesen/dictionary.py` file contains three large parser classes (424+ lines total) with complex methods.

**Solution**:
- [DONE] Extract common parsing patterns into `BaseDictionaryParser` abstract base class
- [DONE] Create `XMLParserMixin` and `JSONLParserMixin` for shared XML/JSON processing utilities
- [DONE] Break down large methods in `JapaneseJMDictParser` and `JapaneseWiktionaryParser`:
  - [DONE] Refactor `JapaneseWiktionaryParser.parse()` into smaller helper methods
  - [DONE] Extract `_build_entry_lookup()`, `_process_redirect_entry()`, `_process_direct_entry()`, `_create_dict_row()`
  - [DONE] Use base class utilities for common operations (ID generation, POS canonicalization, text cleaning)
- [DONE] Simplify XML and JSONL processing using mixin utilities
- [DONE] Eliminate code duplication across all three parser classes

**Files affected**:
- [DONE] `mitlesen/dictionary.py` (added base classes and mixins, refactored all parser classes)

## 7. AI Client Redundancy [DONE]

**Issue**: The `CompletionClient` and `CompletionStreamClient` in `mitlesen/ai.py:15-143` have overlapping initialization logic.

**Solution**:
- [DONE] Create a `BaseAIClient` class with shared initialization
- [DONE] Extract common backend setup logic
- [DONE] Consider using composition over inheritance for backend-specific behavior
- [DONE] Unify configuration management

**Files affected**:
- [DONE] `mitlesen/ai.py`

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

- [DONE] All changes should include proper unit tests
- Consider backward compatibility when refactoring public APIs
- Update documentation after implementing changes
- Run full test suite after each refactoring to ensure no regression