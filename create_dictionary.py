from mitlesen.dictionary import Dictionary, GermanDictionary, JapaneseDictionary

def main():
    db_path = "dict/output/dictionary.sqlite"
    german_jsonl = "dict/input/kaikki.org-dictionary-German.jsonl"
    japanese_xml = "dict/input/JMdict_e.xml"

    db = Dictionary(db_path)
    db.add_dictionary(GermanDictionary(db_path, german_jsonl))
    db.add_dictionary(JapaneseDictionary(db_path, japanese_xml))
    print("Creating dictionary entries...")
    db.create_db()
    print(f"✅ Combined dictionary created at: {db_path}")
    print("Creating indexes...")
    db.create_indexes()
    print("✅ Indexes created")

if __name__ == "__main__":
    main() 