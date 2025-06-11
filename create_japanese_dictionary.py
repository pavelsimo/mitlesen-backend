import hashlib
import sqlite3
import xml.etree.ElementTree as ET
from pykakasi import kakasi

JMDICT_PATH = 'dict/input/JMdict_e.xml'
DB_PATH = 'dict/output/japanese_dictionary.sqlite'

# Init kakasi
kks = kakasi()

def make_id(lang, lemma, pos):
    return hashlib.sha1(f"{lang}:{lemma}:{pos}".encode('utf-8')).hexdigest()

def to_romaji(text):
    items = kks.convert(text)
    return ''.join(item['hepburn'] for item in items)

# Simplified POS mapping
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

# Clean POS remark mappings
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

def normalize_pos_remarks(remark_raw):
    if not remark_raw:
        return ""
    raw = remark_raw.strip().lower().replace("(", "").replace(")", "").replace(",", "").replace("  ", " ")
    cleaned = POS_REMARK_MAP.get(raw)
    return cleaned if cleaned else raw

def extract_pos_and_remarks(ent):
    raw_pos_list = [tag.text for tag in ent.findall("sense/pos") if tag.text]

    if not raw_pos_list:
        return "other", ""

    for full_pos in raw_pos_list:
        raw = full_pos.lower().replace("(", "").replace(")", "").replace(",", "").strip()
        parts = raw.split()
        main = parts[0]
        simplified = POS_MAP.get(main, "other")
        if simplified == "other":
            return "other", normalize_pos_remarks(raw)
        else:
            return simplified, normalize_pos_remarks(" ".join(parts[1:]))

    return "other", ""

def extract_level(ent):
    levels = [tag.text for tag in ent.findall("sense/misc") if tag.text and tag.text.startswith("jlpt")]
    return levels[0].upper() if levels else None

def extract_furigana(ent):
    result = []
    kanjis = [k.text for k in ent.findall("k_ele/keb") if k.text]
    kanas = [r.text for r in ent.findall("r_ele/reb") if r.text]
    for k, r in zip(kanjis, kanas):
        result.append({ "kanji": k, "kana": r })
    return result if result else None

def extract_meanings(ent):
    glosses = ent.findall("sense/gloss")
    return "; ".join(g.text for g in glosses if g is not None and g.text)

def create_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute('''
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
    ''')
    return conn

def parse_jmdict(conn):
    tree = ET.parse(JMDICT_PATH)
    root = tree.getroot()
    entries = root.findall("entry")

    for ent in entries:
        lang = "ja"
        kanji = ent.find("k_ele/keb")
        kana = ent.find("r_ele/reb")

        word_text = kanji.text if kanji is not None else kana.text
        kana_text = kana.text if kana is not None else ""
        romaji = to_romaji(kana_text) if kana_text else ""
        lemma = word_text
        pos, pos_remarks = extract_pos_and_remarks(ent)
        meanings = extract_meanings(ent)
        furigana = str(extract_furigana(ent))
        level = extract_level(ent)

        id_ = make_id(lang, lemma, pos)

        conn.execute('''
        INSERT OR REPLACE INTO dictionary (
            id, lang, word, kana, romaji, lemma, pos, pos_remarks, gender,
            meanings, furigana, ogg_url, mp3_url, level
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            id_, lang, word_text, kana_text, romaji, lemma, pos, pos_remarks, None,
            meanings, furigana, None, None, level
        ))

    conn.commit()
    print(f"Inserted {len(entries)} entries.")

if __name__ == "__main__":
    conn = create_db()
    parse_jmdict(conn)
    conn.close()
