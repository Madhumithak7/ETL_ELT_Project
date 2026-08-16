"""
etl_pipeline.py
------------------------------------------------------------------
Demonstrates the ETL pattern: extract -> transform (in Python,
outside the target) -> load (only clean, final-shape data reaches
the target).

Notice what's absent here on purpose: at no point does the "target"
(here, a simple SQLite file standing in for a warehouse) ever see
the raw, uncleaned rows. By the time load_clean_data() runs, every
row has already been deduplicated, had nulls handled, and been
reshaped into its final schema -- exactly matching the definition
in docs/01-etl-explained.md.

Run: python etl_pipeline.py
------------------------------------------------------------------
"""
import sqlite3
from pathlib import Path

RAW_SOURCE = [
    # simulates rows straight from an upstream operational system --
    # deliberately messy: a duplicate, a null score, inconsistent casing
    {"customer_id": 1, "name": "ana garcia", "country": "germany", "score": 450},
    {"customer_id": 2, "name": "Lukas Meyer", "country": "Germany", "score": None},
    {"customer_id": 2, "name": "Lukas Meyer", "country": "Germany", "score": None},  # duplicate row
    {"customer_id": 3, "name": "SOPHIE DUBOIS", "country": "france", "score": 720},
]

DB_PATH = Path(__file__).parent / "etl_target.db"


def extract():
    """Stage 1: pull data from the source. In a real pipeline this
    would be a DB query, API call, or file read."""
    print(f"[EXTRACT] Pulled {len(RAW_SOURCE)} raw rows from source")
    return RAW_SOURCE


def transform(rows):
    """Stage 2: ALL cleaning and shaping happens here, before the
    target ever sees the data. This is the defining property of ETL."""
    seen_ids = set()
    cleaned = []
    for row in rows:
        if row["customer_id"] in seen_ids:
            continue  # dedup
        seen_ids.add(row["customer_id"])

        cleaned.append({
            "customer_id": row["customer_id"],
            "name": row["name"].title(),               # standardize casing
            "country": row["country"].title(),          # standardize casing
            "score": row["score"] if row["score"] is not None else 0,  # null handling
        })
    print(f"[TRANSFORM] {len(rows)} raw rows -> {len(cleaned)} cleaned rows "
          f"(deduped, nulls handled, casing standardized)")
    return cleaned


def load_clean_data(rows):
    """Stage 3: the target only ever receives already-clean data.
    No raw/messy intermediate state ever touches this database."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS customers")
    conn.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT, country TEXT, score INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO customers VALUES (:customer_id, :name, :country, :score)",
        rows,
    )
    conn.commit()
    print(f"[LOAD] Wrote {len(rows)} clean rows -> {DB_PATH}")
    conn.close()


if __name__ == "__main__":
    raw = extract()
    clean = transform(raw)      # <-- transformation happens BEFORE load
    load_clean_data(clean)      # <-- target only ever sees final-shape data

    # verify: query the target and show it only ever held clean data
    conn = sqlite3.connect(DB_PATH)
    print("\n[VERIFY] Contents of target database:")
    for row in conn.execute("SELECT * FROM customers"):
        print(" ", row)
    conn.close()
