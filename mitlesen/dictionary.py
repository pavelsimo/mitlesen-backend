import hashlib
import json
import sqlite3
from abc import ABC
from typing import List, Optional, Iterable
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from pykakasi import kakasi

import logging
logger = logging.getLogger(__name__)

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

class BaseDictionary(ABC):
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
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_word ON dictionaries(word);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lemma ON dictionaries(lemma);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_kana ON dictionaries(kana);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_lang ON dictionaries(lang);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionaries_pos ON dictionaries(pos);")
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

    def search_by_lemma(self, lemma: str, lang: Optional[str] = None) -> list[dict]:
        """Search for dictionary entries by lemma (and optionally language)."""
        cursor = self.conn.cursor()
        if lang:
            cursor.execute("SELECT * FROM dictionaries WHERE lemma = ? AND lang = ?", (lemma, lang))
        else:
            cursor.execute("SELECT * FROM dictionaries WHERE lemma = ?", (lemma,))
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

    def search_japanese_word(self, word: dict) -> dict | None:
        """Search for a Japanese dictionary entry by word dict using a prioritized matching logic. Returns a single record or None."""
        lemma_kana = word.get('base_form')
        lemma_kanji = word.get('base_form2')
        pos = word.get('pos')
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
    
class GermanWiktionaryParser:
    def __init__(self, jsonl_path: str):
        self.jsonl_path = jsonl_path

    def parse(self) -> Iterable[DictRow]:
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("lang") != "German":
                    continue
                word = entry.get("word")
                lang = "de"
                lemma = word
                gender = None
                pos_raw = entry.get("pos", "")
                pos, pos_remarks = canonicalise_pos(pos_raw)
                for sense in entry.get("senses", []):
                    tags = sense.get("tags", [])
                    gender_tags = [t for t in tags if t in {"masculine", "feminine", "neuter"}]
                    if gender_tags:
                        gender = gender_tags[0][0]
                        break
                if not gender and "head_templates" in entry:
                    for ht in entry["head_templates"]:
                        tags = list(ht.get("args", {}).values())
                        for tag in tags:
                            if isinstance(tag, str):
                                tag = tag.lower()
                                if "masculine" in tag:
                                    gender = "m"
                                elif "feminine" in tag:
                                    gender = "f"
                                elif "neuter" in tag:
                                    gender = "n"
                meanings = []
                for sense in entry.get("senses", []):
                    glosses = sense.get("glosses", [])
                    if glosses:
                        meanings.append("; ".join(glosses))
                id_ = make_id(lang, lemma, pos)
                yield DictRow(
                    id=id_, lang=lang, word=word, lemma=lemma, pos=pos, pos_remarks=pos_remarks,
                    gender=gender, meanings=meanings if meanings else None
                )

class JapaneseJMDictParser:
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
        self.jmdict_path = jmdict_path

    def to_romaji(self, text):
        items = KKS.convert(text)
        return ''.join(item['hepburn'] for item in items)

    def normalize_pos_remarks(self, remark_raw):
        if not remark_raw:
            return ""
        raw = remark_raw.strip().lower().replace("(", "").replace(")", "").replace(",", "").replace("  ", " ")
        cleaned = self.POS_REMARK_MAP.get(raw)
        return cleaned if cleaned else raw

    def extract_pos_and_remarks(self, ent):
        raw_pos_list = [tag.text for tag in ent.findall("sense/pos") if tag.text]
        if not raw_pos_list:
            return "other", ""
        for full_pos in raw_pos_list:
            raw = full_pos.lower().replace("(", "").replace(")", "").replace(",", "").strip()
            parts = raw.split()
            main = parts[0]
            simplified, _ = canonicalise_pos(main)
            if simplified == "other":
                return "other", self.normalize_pos_remarks(raw)
            else:
                return simplified, self.normalize_pos_remarks(" ".join(parts[1:]))
        return "other", ""

    def extract_level(self, ent):
        levels = [tag.text for tag in ent.findall("sense/misc") if tag.text and tag.text.startswith("jlpt")]
        return levels[0].upper() if levels else None

    def extract_furigana(self, ent):
        result = []
        kanjis = [k.text for k in ent.findall("k_ele/keb") if k.text]
        kanas = [r.text for r in ent.findall("r_ele/reb") if r.text]
        for k, r in zip(kanjis, kanas):
            result.append({ "kanji": k, "kana": r })
        return result if result else None

    def extract_meanings(self, ent):
        glosses = ent.findall("sense/gloss")
        return [g.text for g in glosses if g is not None and g.text]

    def parse(self) -> Iterable[DictRow]:
        # Stream parse XML
        for event, ent in ET.iterparse(self.jmdict_path, events=("end",)):
            if ent.tag != "entry":
                continue
            lang = "ja"
            kanji = ent.find("k_ele/keb")
            kana = ent.find("r_ele/reb")
            word_text = kanji.text if kanji is not None else (kana.text if kana is not None else None)
            kana_text = kana.text if kana is not None else ""
            romaji = self.to_romaji(kana_text) if kana_text else ""
            lemma = word_text
            pos, pos_remarks = self.extract_pos_and_remarks(ent)
            meanings = self.extract_meanings(ent)
            furigana = str(self.extract_furigana(ent))
            level = self.extract_level(ent)
            id_ = make_id(lang, lemma, pos)
            yield DictRow(
                id=id_, lang=lang, word=word_text, kana=kana_text, romaji=romaji, lemma=lemma,
                pos=pos, pos_remarks=pos_remarks, meanings=meanings if meanings else None,
                furigana=furigana, level=level
            )
            ent.clear()

class JapaneseWiktionaryParser:
    def __init__(self, jsonl_path: str, pos_filter=None):
        self.jsonl_path = jsonl_path
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
        # First pass: build a lookup table of non-redirect entries by (word, pos)
        entry_lookup = {}
        entries_to_process = []
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("lang") != "Japanese":
                    continue
                pos_raw = entry.get("pos", "")
                pos, pos_remarks = canonicalise_pos(pos_raw)
                if pos in self.pos_filter:
                    continue
                entries_to_process.append(entry)
                if not (pos_raw == "soft-redirect" or entry.get("redirect") or entry.get("redirects")):
                    key = (entry.get("word"), pos_raw)
                    entry_lookup[key] = entry
        for entry in entries_to_process:
            word = entry.get("word")
            lang = "ja"
            pos_raw = entry.get("pos", "")
            pos, pos_remarks = canonicalise_pos(pos_raw)
            if pos in self.pos_filter:
                continue
            is_soft_redirect = (
                pos_raw == "soft-redirect" or entry.get("redirect") or entry.get("redirects")
            )
            if is_soft_redirect:
                target_word = entry.get("redirect") or entry.get("redirects")
                if isinstance(target_word, list):
                    target_word = target_word[0] if target_word else None
                if not target_word:
                    continue
                target_entry = entry_lookup.get((target_word, pos_raw)) or entry_lookup.get((target_word, ""))
                if not target_entry:
                    continue
                lemma = word
                kana = self.extract_kana(target_entry)
                if kana is None:
                    kana = lemma
                romaji = self.extract_romaji(target_entry)
                furigana_val = self.extract_furigana(target_entry)
                furigana = str(furigana_val) if furigana_val is not None else None
                meanings = self.extract_meanings(target_entry)
                level = self.extract_level(target_entry)
                id_ = make_id(lang, lemma, pos)
                yield DictRow(
                    id=id_, lang=lang, word=word, kana=kana, romaji=romaji, lemma=lemma, pos=pos,
                    pos_remarks=pos_remarks, meanings=meanings if meanings else None,
                    furigana=furigana, level=level
                )
            else:
                lemma = self.extract_lemma(entry)
                kana = self.extract_kana(entry)
                if kana is None:
                    kana = lemma
                romaji = self.extract_romaji(entry)
                furigana_val = self.extract_furigana(entry)
                furigana = str(furigana_val) if furigana_val is not None else None
                meanings = self.extract_meanings(entry)
                level = self.extract_level(entry)
                id_ = make_id(lang, lemma, pos)
                yield DictRow(
                    id=id_, lang=lang, word=word, kana=kana, romaji=romaji, lemma=lemma, pos=pos,
                    pos_remarks=pos_remarks, meanings=meanings if meanings else None,
                    furigana=furigana, level=level
                )
