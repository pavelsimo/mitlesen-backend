import hashlib
import json
import sqlite3
from abc import ABC, abstractmethod
from typing import List, Optional, Iterable, Dict, Any
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pykakasi import kakasi

from mitlesen.logger import logger

POS_CANON = {
    "noun": "noun",
    "name": "noun",
    "adj": "adjective",
    "adjective": "adjective",
    "adv": "adverb",
    "adverb": "adverb",
    "pron": "pronoun",
    "pronoun": "pronoun",
    "conj": "conjunction",
    "conjunction": "conjunction",
    "intj": "interjection",
    "interjection": "interjection",
    "num": "number",
    "number": "number",
    "verb": "verb",
    "counter": "counter",
    "romanization": "romanization",
    "character": "character",
    "particle": "particle"
}

_pos_cache: dict[str, tuple[str, str]] = {}

def canonicalise_pos(raw: str) -> tuple[str, str]:
    raw = raw.lower().strip()
    if raw in _pos_cache:
        return _pos_cache[raw]
    head, *tail = raw.replace("(", "").replace(")", "").split()
    mapped = POS_CANON.get(head, "other")
    remarks = "" if mapped != "other" else raw
    _pos_cache[raw] = (mapped, " ".join(tail) if tail else remarks)
    return _pos_cache[raw]

def make_id(lang: str, lemma: str, pos: str) -> str:
    return hashlib.sha1(f"{lang}:{lemma}:{pos}".encode()).hexdigest()

KKS = kakasi()

@dataclass
class DictRow:
    id: str
    lang: str
    word: str
    kana: Optional[str] = None
    romaji: Optional[str] = None
    lemma: Optional[str] = None
    pos: Optional[str] = None
    pos_remarks: str = ""
    gender: Optional[str] = None
    meanings: Optional[list[str]] = None
    furigana: Optional[str] = None
    level: Optional[str] = None


class BaseDictionaryParser(ABC):
    """Abstract base class for dictionary parsers to reduce code duplication."""

    def __init__(self, source_path: str):
        self.source_path = source_path

    @abstractmethod
    def parse(self) -> Iterable[DictRow]:
        """Parse the dictionary source and yield DictRow objects."""
        pass

    def make_entry_id(self, lang: str, lemma: str, pos: str) -> str:
        """Generate a unique ID for a dictionary entry."""
        return make_id(lang, lemma, pos)

    def canonicalize_pos(self, pos_raw: str) -> tuple[str, str]:
        """Canonicalize part-of-speech using shared logic."""
        return canonicalise_pos(pos_raw)

    def extract_gender_from_tags(self, tags: List[str]) -> Optional[str]:
        """Extract gender information from tags (common for German entries)."""
        gender_tags = [t for t in tags if t in {"masculine", "feminine", "neuter"}]
        if gender_tags:
            return gender_tags[0][0]  # Return first letter: m, f, n
        return None

    def extract_gender_from_templates(self, head_templates: List[Dict]) -> Optional[str]:
        """Extract gender from head templates (common pattern)."""
        for ht in head_templates:
            tags = list(ht.get("args", {}).values())
            for tag in tags:
                if isinstance(tag, str):
                    tag = tag.lower()
                    if "masculine" in tag:
                        return "m"
                    elif "feminine" in tag:
                        return "f"
                    elif "neuter" in tag:
                        return "n"
        return None

    def extract_meanings_from_senses(self, senses: List[Dict]) -> List[str]:
        """Extract meanings from sense data (common pattern)."""
        meanings = []
        for sense in senses:
            glosses = sense.get("glosses", [])
            if glosses:
                meanings.append("; ".join(glosses))
        return meanings if meanings else None

    def clean_text_content(self, text: str) -> str:
        """Clean and normalize text content."""
        if not text:
            return ""
        return text.strip().lower().replace("(", "").replace(")", "").replace(",", "").replace("  ", " ")


class XMLParserMixin:
    """Mixin for XML parsing utilities."""

    def extract_xml_text_list(self, parent_element, xpath: str) -> List[str]:
        """Extract list of text content from XML elements."""
        return [elem.text for elem in parent_element.findall(xpath) if elem.text]

    def extract_xml_text_single(self, parent_element, xpath: str) -> Optional[str]:
        """Extract single text content from XML element."""
        elem = parent_element.find(xpath)
        return elem.text if elem is not None else None


class JSONLParserMixin:
    """Mixin for JSONL parsing utilities."""

    def parse_jsonl_file(self, file_path: str, lang_filter: Optional[str] = None):
        """Parse JSONL file and yield entries, optionally filtering by language."""
        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if lang_filter and entry.get("lang") != lang_filter:
                    continue
                yield entry


class BaseDictionaryInterface(ABC):
    """Abstract interface for dictionary operations (unified API)."""

    @abstractmethod
    def search_by_lemma(self, lemma: str, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for dictionary entries by lemma."""
        pass

    @abstractmethod
    def close(self) -> None:
        """Close database connection or cleanup resources."""
        pass


class BaseDictionary(BaseDictionaryInterface):
    schema = """
    CREATE TABLE IF NOT EXISTS dictionaries (
        id TEXT PRIMARY KEY,
        lang TEXT NOT NULL,
        word TEXT,
        kana TEXT,
        romaji TEXT,
        lemma TEXT,
        pos TEXT,
        pos_remarks TEXT,
        gender TEXT,
        meanings TEXT,
        furigana TEXT,
        level TEXT
    );
    """
    _INSERT_SQL = """
        INSERT OR REPLACE INTO dictionaries (
            id, lang, word, kana, romaji, lemma, pos, pos_remarks,
            gender, meanings, furigana, level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """

    def __init__(self, output_path: str):
        self.output_path = output_path
        self.conn = sqlite3.connect(self.output_path)
        self.conn.row_factory = sqlite3.Row

    def close(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def create_schema(self):
        self.conn.execute(self.schema)
        self.conn.commit()
        print(f"✅ Schema created in: {self.output_path}")

    def create_indexes(self):
        cursor = self.conn.cursor()
        # Composite indexes for search_japanese_word
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lang_lemma_pos ON dictionaries(lang, lemma, pos);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lang_lemma ON dictionaries(lang, lemma);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lang_kana ON dictionaries(lang, kana);")
        # Existing single-column indexes (optional, keep if used elsewhere)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_word ON dictionaries(word);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lemma ON dictionaries(lemma);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_kana ON dictionaries(kana);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lang ON dictionaries(lang);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_pos ON dictionaries(pos);")
        # Functional indexes for case-insensitive lemma search
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lower_lemma ON dictionaries(LOWER(lemma));")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lang_lower_lemma ON dictionaries(lang, LOWER(lemma));")
        self.conn.commit()
        print(f"✅ Indexes created in: {self.output_path}")

    def _bulk_insert(self, rows: Iterable[DictRow], batch_size: int = 1000):
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=OFF")
        buf = []
        for r in rows:
            buf.append((
                r.id, r.lang, r.word, r.kana, r.romaji, r.lemma,
                r.pos, r.pos_remarks, r.gender,
                json.dumps(r.meanings, ensure_ascii=False) if r.meanings else None,
                r.furigana, r.level
            ))
            if len(buf) >= batch_size:
                self.conn.executemany(self._INSERT_SQL, buf)
                buf.clear()
        if buf:
            self.conn.executemany(self._INSERT_SQL, buf)
        self.conn.commit()

    def search_by_lemma(self, lemma: str, lang: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search for dictionary entries by lemma (and optionally language)."""
        cursor = self.conn.cursor()
        lemma = lemma.lower()
        if lang:
            cursor.execute("SELECT * FROM dictionaries WHERE LOWER(lemma) = ? AND lang = ?", (lemma, lang))
        else:
            cursor.execute("SELECT * FROM dictionaries WHERE LOWER(lemma) = ?", (lemma,))
        rows = cursor.fetchall()
        return [dict(row) for row in rows]

class SqliteDictionary(BaseDictionary):
    def __init__(self, output_path: str):
        super().__init__(output_path)
        self._parsers: List = []

    def add_parser(self, parser):
        self._parsers.append(parser)

    def create_db(self):
        self.create_schema()
        for parser in self._parsers:
            self._bulk_insert(parser.parse())

    def create_indexes(self):
        super().create_indexes()

    def search_japanese_word(self, word: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Search for a Japanese dictionary entry by word dict using a prioritized matching logic. Returns a single record or None."""
        # Look for underscore-prefixed field names used for temporary dictionary search
        lemma_kana = word.get('_base_form')
        lemma_kanji = word.get('_base_form2')
        pos = word.get('_pos')
        kana = word.get('text')
        logger.info(f"Searching for Japanese word: lemma_kana={lemma_kana}, lemma_kanji={lemma_kanji}, pos={pos}, kana={kana}")
        cursor = self.conn.cursor()
        # 1. Try to match by (lang='ja', lemma_kana, pos)
        if lemma_kana and pos:
            logger.info(f"Attempting match by (lang='ja', lemma_kana={lemma_kana}, pos={pos})")
            cursor.execute(
                "SELECT * FROM dictionaries WHERE lang = ? AND lemma = ? AND pos = ?",
                ('ja', lemma_kana, pos)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Found a match by lemma_kana and pos")
                return dict(row)
        # 2. Try to match by (lang='ja', lemma_kanji, pos)
        if lemma_kanji and pos:
            logger.info(f"Attempting match by (lang='ja', lemma_kanji={lemma_kanji}, pos={pos})")
            cursor.execute(
                "SELECT * FROM dictionaries WHERE lang = ? AND lemma = ? AND pos = ?",
                ('ja', lemma_kanji, pos)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Found a match by lemma_kanji and pos")
                return dict(row)
        # 3. Try to match by (lang='ja', lemma_kana)
        if lemma_kana:
            logger.info(f"Attempting match by (lang='ja', lemma_kana={lemma_kana})")
            cursor.execute(
                "SELECT * FROM dictionaries WHERE lang = ? AND lemma = ?",
                ('ja', lemma_kana)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Found a match by lemma_kana")
                return dict(row)
        # 4. Try to match by (lang='ja', kana)
        if kana:
            logger.info(f"Attempting match by (lang='ja', kana={kana})")
            cursor.execute(
                "SELECT * FROM dictionaries WHERE lang = ? AND kana = ?",
                ('ja', kana)
            )
            row = cursor.fetchone()
            if row:
                logger.info(f"Found a match by kana")
                return dict(row)
        logger.info("No matches found for any search criteria")
        return None

class GermanWiktionaryParser(BaseDictionaryParser, JSONLParserMixin):
    def __init__(self, jsonl_path: str):
        super().__init__(jsonl_path)

    def parse(self) -> Iterable[DictRow]:
        for entry in self.parse_jsonl_file(self.source_path, lang_filter="German"):
            word = entry.get("word")
            lang = "de"
            lemma = word

            # Extract POS and remarks using base class method
            pos_raw = entry.get("pos", "")
            pos, pos_remarks = self.canonicalize_pos(pos_raw)

            # Extract gender using base class methods
            gender = self._extract_gender(entry)

            # Extract meanings using base class method
            meanings = self.extract_meanings_from_senses(entry.get("senses", []))

            id_ = self.make_entry_id(lang, lemma, pos)
            yield DictRow(
                id=id_, lang=lang, word=word, lemma=lemma, pos=pos, pos_remarks=pos_remarks,
                gender=gender, meanings=meanings
            )

    def _extract_gender(self, entry: Dict) -> Optional[str]:
        """Extract gender information from German entry."""
        # Try to extract from sense tags first
        for sense in entry.get("senses", []):
            tags = sense.get("tags", [])
            gender = self.extract_gender_from_tags(tags)
            if gender:
                return gender

        # Try to extract from head templates
        if "head_templates" in entry:
            return self.extract_gender_from_templates(entry["head_templates"])

        return None

class JapaneseJMDictParser(BaseDictionaryParser, XMLParserMixin):
    POS_REMARK_MAP = {
        "common futsuumeishi": "common noun (futsuumeishi)",
        "phrases clauses etc.": "phrase or clause",
        "quasi-adjectives keiyodoshi": "quasi-adjective (keiyodoshi)",
        "keiyoushi": "i-adjective (keiyoushi)",
        "godan with 'u' ending": "godan verb, -u ending",
        "fukushi": "adverb (fukushi)",
        "kandoushi": "interjection (kandoushi)",
        "which may take the genitive case particle 'no'": "takes 'no' (genitive case)",
        "godan with 'su' ending": "godan verb, -su ending",
        "adjectival rentaishi": "prenominal adjective (rentaishi)",
        "ichidan": "ichidan verb",
        "taking the 'to' particle": "takes 'to' particle",
        "godan with 'ku' ending": "godan verb, -ku ending",
        "godan with 'ru' ending": "godan verb, -ru ending",
        "godan - -aru special class": "godan verb (special -aru class)",
        "godan with 'mu' ending": "godan verb, -mu ending",
        "participle which takes the aux. verb suru": "participle with suru",
        "used as a suffix": "used as a suffix",
        "auxiliary": "auxiliary verb",
        "suru - special class": "suru verb (special class)",
        "shiku archaic": "shiku adjective (archaic)",
        "taru": "taru adjective",
        "godan with 'tsu' ending": "godan verb, -tsu ending",
        "suru - included": "includes suru verb",
        "godan - iku/yuku special class": "godan verb (iku/yuku special class)",
        "used as a prefix": "used as a prefix",
        "godan with 'bu' ending": "godan verb, -bu ending",
        "ichidan - zuru alternative form of -jiru verbs": "ichidan zuru verb (alt. of -jiru)",
        "keiyoushi - yoi/ii class": "i-adjective (yoi/ii class)",
        "nidan lower class with 'mu' ending archaic": "nidan verb (lower), -mu ending (archaic)",
        "su - precursor to the modern suru": "old form of suru",
        "ichidan - kureru special class": "ichidan kureru verb (special class)",
        "godan with 'ru' ending irregular verb": "godan verb, -ru ending (irregular)",
        "godan with 'nu' ending": "godan verb, -nu ending",
        "ku archaic": "ku adjective (archaic)",
        "form of na-adjective": "form of na-adjective",
        "intransitive": "intransitive verb",
        "transitive": "transitive verb",
        "copula": "copula",
        "prefix": "used as a prefix",
        "suffix": "used as a suffix",
        "archaic/formal": "archaic/formal usage"
    }
    def __init__(self, jmdict_path: str):
        super().__init__(jmdict_path)

    def to_romaji(self, text):
        items = KKS.convert(text)
        return ''.join(item['hepburn'] for item in items)

    def normalize_pos_remarks(self, remark_raw):
        if not remark_raw:
            return ""
        raw = self.clean_text_content(remark_raw)
        cleaned = self.POS_REMARK_MAP.get(raw)
        return cleaned if cleaned else raw

    def extract_pos_and_remarks(self, ent):
        raw_pos_list = self.extract_xml_text_list(ent, "sense/pos")
        if not raw_pos_list:
            return "other", ""
        for full_pos in raw_pos_list:
            raw = self.clean_text_content(full_pos)
            parts = raw.split()
            main = parts[0]
            simplified, _ = self.canonicalize_pos(main)
            if simplified == "other":
                return "other", self.normalize_pos_remarks(raw)
            else:
                return simplified, self.normalize_pos_remarks(" ".join(parts[1:]))
        return "other", ""

    def extract_level(self, ent):
        misc_tags = self.extract_xml_text_list(ent, "sense/misc")
        levels = [tag.upper() for tag in misc_tags if tag.startswith("jlpt")]
        return levels[0] if levels else None

    def extract_furigana(self, ent):
        result = []
        kanjis = self.extract_xml_text_list(ent, "k_ele/keb")
        kanas = self.extract_xml_text_list(ent, "r_ele/reb")
        for k, r in zip(kanjis, kanas):
            result.append({"kanji": k, "kana": r})
        return result if result else None

    def extract_meanings(self, ent):
        return self.extract_xml_text_list(ent, "sense/gloss")

    def parse(self) -> Iterable[DictRow]:
        # Stream parse XML
        for event, ent in ET.iterparse(self.source_path, events=("end",)):
            if ent.tag != "entry":
                continue
            lang = "ja"

            # Extract word text using helper methods
            word_text = (self.extract_xml_text_single(ent, "k_ele/keb") or
                        self.extract_xml_text_single(ent, "r_ele/reb"))
            kana_text = self.extract_xml_text_single(ent, "r_ele/reb") or ""
            romaji = self.to_romaji(kana_text) if kana_text else ""
            lemma = word_text

            # Extract structured data using helper methods
            pos, pos_remarks = self.extract_pos_and_remarks(ent)
            meanings = self.extract_meanings(ent)
            furigana = self.extract_furigana(ent)
            if furigana is not None:
                furigana = json.dumps(furigana, ensure_ascii=False)
            level = self.extract_level(ent)

            id_ = self.make_entry_id(lang, lemma, pos)
            yield DictRow(
                id=id_, lang=lang, word=word_text, kana=kana_text, romaji=romaji, lemma=lemma,
                pos=pos, pos_remarks=pos_remarks, meanings=meanings if meanings else None,
                furigana=furigana, level=level
            )
            ent.clear()

class JapaneseWiktionaryParser(BaseDictionaryParser, JSONLParserMixin):
    def __init__(self, jsonl_path: str, pos_filter=None):
        super().__init__(jsonl_path)
        self.pos_filter = pos_filter if pos_filter is not None else []

    def extract_kana(self, entry):
        if "forms" in entry:
            for form in entry["forms"]:
                if "tags" in form and ("hiragana" in form["tags"] or "katakana" in form["tags"]):
                    return form.get("form")
                if "ruby" in form:
                    return ''.join([r[1] for r in form["ruby"] if len(r) > 1])
        if "head_templates" in entry:
            for ht in entry["head_templates"]:
                kana = ht["args"].get("2")
                if kana and kana in ["hiragana", "katakana"]:
                    return ht["args"].get("1")
        return None

    def extract_romaji(self, entry):
        if "forms" in entry:
            for form in entry["forms"]:
                if "tags" in form and "romanization" in form["tags"]:
                    return form.get("form")
                if "roman" in form:
                    return form["roman"]
        if "head_templates" in entry:
            for ht in entry["head_templates"]:
                if ht["args"].get("sc") == "Latn":
                    return entry.get("word")
        return None

    def extract_furigana(self, entry):
        if "forms" in entry:
            for form in entry["forms"]:
                if "ruby" in form:
                    return form["ruby"]
        return None

    def extract_lemma(self, entry):
        if "forms" in entry:
            for form in entry["forms"]:
                if "tags" in form and "canonical" in form["tags"]:
                    return form.get("form")
        return entry.get("word")

    def extract_meanings(self, entry):
        meanings = []
        for sense in entry.get("senses", []):
            glosses = sense.get("glosses", [])
            if glosses:
                meanings.append('; '.join(glosses))
        return meanings

    def extract_level(self, entry):
        if "categories" in entry:
            for cat in entry["categories"]:
                if "jlpt" in cat["name"].lower():
                    return cat["name"].upper()
        return None

    def parse(self) -> Iterable[DictRow]:
        """Parse Japanese Wiktionary data with redirect resolution."""
        # Build lookup table and collect entries to process
        entry_lookup, entries_to_process = self._build_entry_lookup()

        # Process all entries
        for entry in entries_to_process:
            word = entry.get("word")
            lang = "ja"
            pos_raw = entry.get("pos", "")
            pos, pos_remarks = self.canonicalize_pos(pos_raw)

            if pos in self.pos_filter:
                continue

            # Handle redirects vs direct entries
            if self._is_redirect_entry(entry, pos_raw):
                yield from self._process_redirect_entry(entry, entry_lookup, word, lang, pos, pos_remarks, pos_raw)
            else:
                yield from self._process_direct_entry(entry, word, lang, pos, pos_remarks)

    def _build_entry_lookup(self):
        """Build lookup table for non-redirect entries."""
        entry_lookup = {}
        entries_to_process = []

        for entry in self.parse_jsonl_file(self.source_path, lang_filter="Japanese"):
            pos_raw = entry.get("pos", "")
            pos, _ = self.canonicalize_pos(pos_raw)

            if pos in self.pos_filter:
                continue

            entries_to_process.append(entry)

            # Add to lookup if not a redirect
            if not self._is_redirect_entry(entry, pos_raw):
                key = (entry.get("word"), pos_raw)
                entry_lookup[key] = entry

        return entry_lookup, entries_to_process

    def _is_redirect_entry(self, entry, pos_raw):
        """Check if entry is a redirect."""
        return (pos_raw == "soft-redirect" or
                entry.get("redirect") or
                entry.get("redirects"))

    def _process_redirect_entry(self, entry, entry_lookup, word, lang, pos, pos_remarks, pos_raw):
        """Process a redirect entry by finding its target."""
        target_word = entry.get("redirect") or entry.get("redirects")
        if isinstance(target_word, list):
            target_word = target_word[0] if target_word else None
        if not target_word:
            return

        target_entry = (entry_lookup.get((target_word, pos_raw)) or
                       entry_lookup.get((target_word, "")))
        if not target_entry:
            return

        yield self._create_dict_row(target_entry, word, lang, pos, pos_remarks, lemma=word)

    def _process_direct_entry(self, entry, word, lang, pos, pos_remarks):
        """Process a direct (non-redirect) entry."""
        lemma = self.extract_lemma(entry)
        yield self._create_dict_row(entry, word, lang, pos, pos_remarks, lemma=lemma)

    def _create_dict_row(self, entry, word, lang, pos, pos_remarks, lemma=None):
        """Create a DictRow from entry data (eliminates duplication)."""
        if lemma is None:
            lemma = word

        kana = self.extract_kana(entry) or lemma
        romaji = self.extract_romaji(entry)
        furigana_val = self.extract_furigana(entry)
        furigana = json.dumps(furigana_val, ensure_ascii=False) if furigana_val is not None else None
        meanings = self.extract_meanings(entry)
        level = self.extract_level(entry)

        id_ = self.make_entry_id(lang, lemma, pos)
        return DictRow(
            id=id_, lang=lang, word=word, kana=kana, romaji=romaji, lemma=lemma, pos=pos,
            pos_remarks=pos_remarks, meanings=meanings if meanings else None,
            furigana=furigana, level=level
        )
