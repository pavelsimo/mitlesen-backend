import os
import sqlite3
from datetime import datetime, timezone
from dotenv import load_dotenv
from mitlesen.db import Database
from mitlesen.logger import logger
from mitlesen import DICTIONARIES_DIR

# Configuration
BATCH_SIZE = 5000
TABLE_NAME = "dictionaries"
SQLITE_PATH = os.path.join(DICTIONARIES_DIR, "output", "dictionary.sqlite")

load_dotenv()

def process_row(row: sqlite3.Row | dict) -> dict:
    """Prepare a row from SQLite for Supabase."""
    row = dict(row) if not isinstance(row, dict) else row
    for k, v in list(row.items()):
        if v == "":
            row[k] = None
    ts = datetime.now(timezone.utc).isoformat()
    row.setdefault("created_at", ts)
    row.setdefault("updated_at", ts)
    return row


def _extract(resp, field, default=None):
    """
    Handle both the PostgrestResponse object (attrs) and the plain-dict
    style that older supabase-py versions returned.
    """
    if hasattr(resp, field):
        return getattr(resp, field)
    if isinstance(resp, dict):
        return resp.get(field, default)
    return default


def upsert_batch(client, table_name: str, batch: list[dict]) -> None:
    """Send one batch to Supabase, raising on error."""
    resp = client.table(table_name).upsert(batch).execute()
    status = _extract(resp, "status_code", 0)
    err = _extract(resp, "error")
    logger.debug("Supabase response: %s", resp)
    if err or (status and status >= 400):
        # Promote key details to the error logs
        logger.error(
            "❌ Supabase upsert failed | status=%s | error=%s | rows=%d | sample=%s",
            status,
            err,
            len(batch),
            batch[0] if batch else "N/A",
        )
        raise RuntimeError(f"Upsert failed (status={status}, error={err})")

    logger.info("✅ Upserted %d rows (status=%s)", len(batch), status)


def main() -> None:
    db = Database()

    with sqlite3.connect(SQLITE_PATH) as conn:
        conn.row_factory = sqlite3.Row
        rows = conn.execute(f"SELECT * FROM {TABLE_NAME}").fetchall()

    batch, total = [], 0
    for idx, row in enumerate(rows, 1):
        batch.append(process_row(row))

        if len(batch) == BATCH_SIZE:
            upsert_batch(db.client, TABLE_NAME, batch)
            total += len(batch)
            batch.clear()
            logger.info("Inserted %d entries so far…", total)

        if idx % BATCH_SIZE == 0:
            logger.debug("Processed %d rows…", idx)

    if batch:
        upsert_batch(db.client, TABLE_NAME, batch)
        total += len(batch)

    logger.info("🎉 Finished: %d entries inserted.", total)
    db.close()


if __name__ == "__main__":
    main()
