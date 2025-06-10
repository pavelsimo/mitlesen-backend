import sqlite3
import hashlib
import json

# Define database path and input file
db_path = "dict/german_dictionary.sqlite"
jsonl_path = "dict/kaikki.org-dictionary-German.jsonl"

# Schema: similar to the Japanese one, but no kana/romaji/furigana
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

# Simplify POS mapping
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

def make_id(lang, lemma, pos):
    return hashlib.sha1(f"{lang}:{lemma}:{pos}".encode("utf-8")).hexdigest()

# Prepare the database
conn = sqlite3.connect(db_path)
conn.execute(schema)

# Parse JSONL
with open(jsonl_path, "r", encoding="utf-8") as f:
    for line in f:
        entry = json.loads(line)
        if entry.get("lang") != "German":
            continue

        word = entry.get("word")
        lang = "de"
        lemma = word
        gender = None
        pos_raw = entry.get("pos", "").lower()
        pos = POS_MAP.get(pos_raw, "other")
        pos_remarks = pos_raw if pos == "other" else ""

        # Extract gender from tags or head_templates
        for sense in entry.get("senses", []):
            tags = sense.get("tags", [])
            gender_tags = [t for t in tags if t in {"masculine", "feminine", "neuter"}]
            if gender_tags:
                gender = gender_tags[0][0]  # 'm', 'f', or 'n'
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

        # Extract glosses
        meanings = []
        for sense in entry.get("senses", []):
            glosses = sense.get("glosses", [])
            if glosses:
                meanings.append("; ".join(glosses))
        meaning_text = "; ".join(meanings) if meanings else None

        # Extract audio URLs
        sounds = entry.get("sounds", [])
        ogg_url = None
        mp3_url = None
        for s in sounds:
            if not ogg_url and "ogg_url" in s:
                ogg_url = s["ogg_url"]
            if not mp3_url and "mp3_url" in s:
                mp3_url = s["mp3_url"]

        # Generate ID
        id_ = make_id(lang, lemma, pos)

        # Insert into DB
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
print(f"✅ Created database: {db_path}")
