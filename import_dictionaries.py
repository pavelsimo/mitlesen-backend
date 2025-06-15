import os
from dotenv import load_dotenv
from mitlesen import DICTIONARIES_DIR
from mitlesen.dictionary import GermanWiktionaryParser, JapaneseWiktionaryParser, JapaneseJMDictParser
from mitlesen.db import Dictionary, Database
from mitlesen.logger import logger

load_dotenv()

def main():
    db = Database()
    german_jsonl = os.path.join(DICTIONARIES_DIR, "input", "kaikki.org-dictionary-German.jsonl")
    japanese_xml = os.path.join(DICTIONARIES_DIR, "input", "JMdict_e.xml")

    parsers = [
        #GermanWiktionaryParser(german_jsonl),
        JapaneseJMDictParser(japanese_xml)
    ]

    batch = []
    batch_size = 100
    total_inserted = 0
    for parser in parsers:
        logger.info(f"Parsing entries from {parser.__class__.__name__}...")
        for row in parser.parse():
            entry = Dictionary(
                id=row.id,
                lang=row.lang,
                word=row.word,
                kana=row.kana,
                romaji=row.romaji,
                lemma=row.lemma,
                pos=row.pos,
                pos_remarks=row.pos_remarks,
                gender=row.gender,
                meanings=row.meanings,
                furigana=row.furigana,
                level=row.level
            ).to_dict()
            batch.append(entry)
            if len(batch) >= batch_size:
                _insert_batch(db.client, batch)
                total_inserted += len(batch)
                logger.info(f"Inserted {total_inserted} entries so far...")
                batch.clear()
    if batch:
        _insert_batch(db.client, batch)
        total_inserted += len(batch)
        logger.info(f"Inserted {total_inserted} entries in total.")
    logger.info("✅ Dictionary import to Supabase complete.")
    db.close()

def _insert_batch(client, batch):
    response = client.table('dictionaries').upsert(batch).execute()
    if response.error:
        logger.error(f"Batch insert error: {response.error.message}")
        raise RuntimeError(f"Failed to insert batch: {response.error.message}")

if __name__ == "__main__":
    main() 