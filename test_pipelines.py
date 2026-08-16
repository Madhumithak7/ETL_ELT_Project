"""
test_pipelines.py
------------------------------------------------------------------
Verifies both demo pipelines actually produce the outputs their
respective docs describe -- run in CI on every push.
------------------------------------------------------------------
"""
import sqlite3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ETL_DIR = ROOT / "examples" / "etl_approach"
ELT_DIR = ROOT / "examples" / "elt_approach"


def run_pipeline(directory: Path, script: str):
    result = subprocess.run(
        [sys.executable, script], cwd=directory, capture_output=True, text=True
    )
    assert result.returncode == 0, f"{script} failed:\n{result.stderr}"
    return result.stdout


def test_etl_target_only_contains_clean_data():
    run_pipeline(ETL_DIR, "etl_pipeline.py")
    conn = sqlite3.connect(ETL_DIR / "etl_target.db")
    rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    conn.close()

    assert len(rows) == 3, "duplicate row should have been removed pre-load"
    assert rows[1][3] == 0, "null score should have been handled pre-load, not left NULL"
    assert rows[0][1] == "Ana Garcia", "casing should already be standardized pre-load"


def test_elt_raw_layer_preserves_original_mess():
    run_pipeline(ELT_DIR, "elt_pipeline.py")
    conn = sqlite3.connect(ELT_DIR / "elt_target.db")
    raw_rows = conn.execute("SELECT * FROM raw_customers").fetchall()
    clean_rows = conn.execute("SELECT * FROM customers ORDER BY customer_id").fetchall()
    conn.close()

    assert len(raw_rows) == 4, "raw layer must preserve the original duplicate row"
    assert raw_rows[0][1] == "ana garcia", "raw layer must NOT be cleaned/cased"
    assert len(clean_rows) == 3, "clean (silver) layer should be deduplicated"
    assert clean_rows[1][3] == 0, "clean layer should have nulls handled"
