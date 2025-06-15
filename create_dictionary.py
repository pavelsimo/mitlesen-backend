import os
from mitlesen import DICTIONARIES_DIR
from mitlesen.dictionary import SqliteDictionary, GermanWiktionaryParser, JapaneseJMDictParser

def main():
    db_path = os.path.join(DICTIONARIES_DIR, "output", "dictionary.sqlite")
    german_jsonl = os.path.join(DICTIONARIES_DIR, "input", "kaikki.org-dictionary-German.jsonl")
    japanese_xml = os.path.join(DICTIONARIES_DIR, "input", "JMdict_e.xml")

    db = SqliteDictionary(db_path)
    db.add_parser(JapaneseJMDictParser(japanese_xml))
    db.add_parser(GermanWiktionaryParser(german_jsonl))
    print("Creating dictionary entries...")
    db.create_db()
    print(f"✅ Combined dictionary created at: {db_path}")
    print("Creating indexes...")
    db.create_indexes()
    print("✅ Indexes created")

if __name__ == "__main__":
    main() 