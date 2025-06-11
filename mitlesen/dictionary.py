import sqlite3
from abc import ABC, abstractmethod
from typing import List
import hashlib
import json
import xml.etree.ElementTree as ET
from pykakasi import kakasi

class BaseDictionary(ABC):
    schema = """
    CREATE TABLE IF NOT EXISTS dictionary (
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
        ogg_url TEXT,
        mp3_url TEXT,
        level TEXT
    );
    """

    def __init__(self, output_path: str):
        self.output_path = output_path

    @abstractmethod
    def create(self):
        """Create or update the dictionary in the output_path database."""
        pass

    def create_schema(self):
        """Create the dictionary table schema in the output_path database."""
        conn = sqlite3.connect(self.output_path)
        conn.execute(self.schema)
        conn.commit()
        conn.close()
        print(f"✅ Schema created in: {self.output_path}")

    def create_indexes(self):
        """Add indexes to relevant fields for search. Call on demand only."""
        conn = sqlite3.connect(self.output_path)
        cursor = conn.cursor()
        # Add indexes for search-relevant fields
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionary_word ON dictionary(word);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionary_lemma ON dictionary(lemma);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionary_lang ON dictionary(lang);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_dictionary_pos ON dictionary(pos);")
        conn.commit()
        conn.close()
        print(f"✅ Indexes created in: {self.output_path}")

class GermanDictionary(BaseDictionary):
    POS_MAP = {
        "noun": "noun",
        "verb": "verb",
        "adjective": "adjective",
        "adverb": "adverb",
        "pronoun": "pronoun",
        "conjunction": "conjunction",
        "interjection": "interjection",
        "particle": "particle",
        "numeral": "number",
        "letter": "letter"
    }

    def __init__(self, output_path: str, jsonl_path: str):
        super().__init__(output_path)
        self.jsonl_path = jsonl_path

    @staticmethod
    def make_id(lang, lemma, pos):
        return hashlib.sha1(f"{lang}:{lemma}:{pos}".encode("utf-8")).hexdigest()

    def create(self):
        conn = sqlite3.connect(self.output_path)
        with open(self.jsonl_path, "r", encoding="utf-8") as f:
            for line in f:
                entry = json.loads(line)
                if entry.get("lang") != "German":
                    continue
                word = entry.get("word")
                lang = "de"
                lemma = word
                gender = None
                pos_raw = entry.get("pos", "").lower()
                pos = self.POS_MAP.get(pos_raw, "other")
                pos_remarks = pos_raw if pos == "other" else ""
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
                meaning_text = "; ".join(meanings) if meanings else None
                sounds = entry.get("sounds", [])
                ogg_url = None
                mp3_url = None
                for s in sounds:
                    if not ogg_url and "ogg_url" in s:
                        ogg_url = s["ogg_url"]
                    if not mp3_url and "mp3_url" in s:
                        mp3_url = s["mp3_url"]
                id_ = self.make_id(lang, lemma, pos)
                conn.execute(
                    """
                    INSERT OR REPLACE INTO dictionary (
                        id, lang, word, kana, romaji, lemma, pos, pos_remarks, gender,
                        meanings, furigana, ogg_url, mp3_url, level
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        id_, lang, word, None, None, lemma, pos, pos_remarks, gender,
                        meaning_text, None, ogg_url, mp3_url, None
                    )
                )
        conn.commit()
        conn.close()
        print(f"✅ Created database: {self.output_path}")

class JapaneseDictionary(BaseDictionary):
    POS_MAP = {
        "noun": "noun",
        "nouns": "noun",
        "verb": "verb",
        "adjective": "adjective",
        "adjectival": "adjective",
        "adverb": "adverb",
        "pronoun": "pronoun",
        "conjunction": "conjunction",
        "interjection": "interjection",
        "numeric": "number",
        "counter": "number"
    }
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
    def __init__(self, output_path: str, jmdict_path: str):
        super().__init__(output_path)
        self.jmdict_path = jmdict_path
        self.kks = kakasi()

    @staticmethod
    def make_id(lang, lemma, pos):
        return hashlib.sha1(f"{lang}:{lemma}:{pos}".encode('utf-8')).hexdigest()

    def to_romaji(self, text):
        items = self.kks.convert(text)
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
            simplified = self.POS_MAP.get(main, "other")
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
        return "; ".join(g.text for g in glosses if g is not None and g.text)

    def create(self):
        conn = sqlite3.connect(self.output_path)
        tree = ET.parse(self.jmdict_path)
        root = tree.getroot()
        entries = root.findall("entry")
        for ent in entries:
            lang = "ja"
            kanji = ent.find("k_ele/keb")
            kana = ent.find("r_ele/reb")
            word_text = kanji.text if kanji is not None else kana.text
            kana_text = kana.text if kana is not None else ""
            romaji = self.to_romaji(kana_text) if kana_text else ""
            lemma = word_text
            pos, pos_remarks = self.extract_pos_and_remarks(ent)
            meanings = self.extract_meanings(ent)
            furigana = str(self.extract_furigana(ent))
            level = self.extract_level(ent)
            id_ = self.make_id(lang, lemma, pos)
            conn.execute(
                '''
                INSERT OR REPLACE INTO dictionary (
                    id, lang, word, kana, romaji, lemma, pos, pos_remarks, gender,
                    meanings, furigana, ogg_url, mp3_url, level
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
                (
                    id_, lang, word_text, kana_text, romaji, lemma, pos, pos_remarks, None,
                    meanings, furigana, None, None, level
                )
            )
        conn.commit()
        print(f"Inserted {len(entries)} entries.")
        conn.close()

class Dictionary:
    def __init__(self, output_path: str):
        self.output_path = output_path
        self._builders: List[BaseDictionary] = []

    def add_dictionary(self, builder: BaseDictionary):
        self._builders.append(builder)

    def create_db(self):
        if self._builders:
            self._builders[0].create_schema()
            
        for builder in self._builders:
            builder.create()

    def create_indexes(self):
        # Only need to create indexes once, use the first builder
        if self._builders:
            self._builders[0].create_indexes() 