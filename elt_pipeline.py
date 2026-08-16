"""
elt_pipeline.py
------------------------------------------------------------------
Demonstrates the ELT pattern: extract -> load (raw, as-is) ->
transform (in-place, using the target's own SQL engine).

Notice the key difference from etl_pipeline.py: the raw, messy rows
(duplicates, nulls, inconsistent casing) DO land in the target -- in
a "raw_customers" table -- exactly as extracted. Only afterward does
a SQL transformation step (standing in for a dbt model) produce a
separate, clean "customers" table. Both the raw and the clean version
coexist in the target simultaneously -- this is the medallion pattern
in miniature (see docs/07-medallion-architecture.md), and it's what
lets you re-run the transform later without re-extracting from source.

Run: python elt_pipeline.py
------------------------------------------------------------------
"""
import sqlite3
from pathlib import Path

RAW_SOURCE = [
    # identical messy source data to etl_pipeline.py, so the two
    # approaches are directly comparable against the same input
    {"customer_id": 1, "name": "ana garcia", "country": "germany", "score": 450},
    {"customer_id": 2, "name": "Lukas Meyer", "country": "Germany", "score": None},
    {"customer_id": 2, "name": "Lukas Meyer", "country": "Germany", "score": None},
    {"customer_id": 3, "name": "SOPHIE DUBOIS", "country": "france", "score": 720},
]

DB_PATH = Path(__file__).parent / "elt_target.db"


def extract():
    print(f"[EXTRACT] Pulled {len(RAW_SOURCE)} raw rows from source")
    return RAW_SOURCE


def load_raw(rows):
    """Stage 2: raw data lands in the target AS-IS -- duplicates,
    nulls, and inconsistent casing all included. No cleaning has
    happened yet. This is the ELT 'raw/bronze' layer."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS raw_customers")
    conn.execute("""
        CREATE TABLE raw_customers (
            customer_id INTEGER, name TEXT, country TEXT, score INTEGER
        )
    """)
    conn.executemany(
        "INSERT INTO raw_customers VALUES (:customer_id, :name, :country, :score)",
        rows,
    )
    conn.commit()
    print(f"[LOAD] Wrote {len(rows)} RAW (unmodified) rows -> raw_customers table")
    conn.close()


def transform_in_place():
    """Stage 3: transformation happens INSIDE the target, via SQL --
    this is exactly what a dbt staging model does, just run directly
    here instead of through the dbt CLI. Note this SQL mirrors the
    dbt stg_customers.sql model from the companion SQL portfolio
    project almost exactly: COALESCE for nulls, dedup logic, casing
    standardization -- same logic, same place it belongs (post-load,
    in SQL), just demonstrated without the dbt tooling layer."""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS customers")
    conn.execute("""
        CREATE TABLE customers AS
        SELECT
            customer_id,
            -- SQLite lacks INITCAP; this mimics title-casing for the demo
            UPPER(SUBSTR(name, 1, 1)) || LOWER(SUBSTR(name, 2)) AS name,
            UPPER(SUBSTR(country, 1, 1)) || LOWER(SUBSTR(country, 2)) AS country,
            COALESCE(score, 0) AS score
        FROM (
            SELECT *, ROW_NUMBER() OVER (
                PARTITION BY customer_id ORDER BY customer_id
            ) AS rn
            FROM raw_customers
        )
        WHERE rn = 1
    """)
    conn.commit()
    n = conn.execute("SELECT COUNT(*) FROM customers").fetchone()[0]
    print(f"[TRANSFORM] Ran SQL in-place against the target -> "
          f"produced {n} clean rows in a separate 'customers' table")
    conn.close()


if __name__ == "__main__":
    raw = extract()
    load_raw(raw)          # <-- raw data lands FIRST, unmodified
    transform_in_place()   # <-- transformation happens AFTER, inside the target

    conn = sqlite3.connect(DB_PATH)
    print("\n[VERIFY] Raw layer still exists, untouched:")
    for row in conn.execute("SELECT * FROM raw_customers"):
        print(" ", row)
    print("\n[VERIFY] Clean layer, derived from raw via in-place SQL:")
    for row in conn.execute("SELECT * FROM customers"):
        print(" ", row)
    print("\nBoth tables coexist in the same target database -- this is")
    print("the medallion pattern: raw_customers = bronze, customers = silver.")
    conn.close()
