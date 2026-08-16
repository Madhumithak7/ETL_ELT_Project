# ETL_ELT_Project

# Data Pipeline Concepts — ETL, ELT, and Modern Data Engineering Patterns

A depth-first companion to this series' hands-on SQL and AWS pipeline
projects: not "how do I write the code," but **why pipelines are
designed the way they are** — the trade-offs behind ETL vs ELT, batch
vs streaming, CDC, SCD, medallion architecture, idempotency, and the
tool landscape those decisions map to.

Every concept doc ends with an honest framing of when the "obvious"
answer is actually wrong, and where relevant, points to the exact file
in this series' other two projects (`sql-portfolio-quickbyte`,
`sales-data-pipeline`) where that concept is implemented for real —
so nothing here is theory disconnected from working code.

## Why this project exists

Two other projects in this series prove I can *build* a pipeline and
*write* production-shaped SQL. This one exists to prove the layer
underneath that: that the design decisions in those projects weren't
copied defaults, but reasoned choices I can explain, defend, and know
when to make differently.

## Start here

| Doc | Covers |
|---|---|
| [`01-etl-explained.md`](docs/01-etl-explained.md) | What ETL is, why it was the historical default, where it's still the right call today |
| [`02-elt-explained.md`](docs/02-elt-explained.md) | What ELT is, why cloud warehouse economics made it the modern default |
| [`03-etl-vs-elt-comparison.md`](docs/03-etl-vs-elt-comparison.md) | Direct comparison table + a 3-question decision framework + the "ELT isn't strictly better" interview trap |
| [`04-batch-vs-streaming.md`](docs/04-batch-vs-streaming.md) | The orthogonal freshness axis; when streaming's complexity is actually worth it |
| [`05-change-data-capture.md`](docs/05-change-data-capture.md) | Why watermark-based incremental extraction can't see deletes, and how log-based CDC fixes that |
| [`06-slowly-changing-dimensions.md`](docs/06-slowly-changing-dimensions.md) | SCD Types 0-3, and why Type 2 is the default when in doubt |
| [`07-medallion-architecture.md`](docs/07-medallion-architecture.md) | Bronze/silver/gold, mapped directly to real files in the AWS pipeline project |
| [`08-idempotency-and-incremental-loads.md`](docs/08-idempotency-and-incremental-loads.md) | Why "just retry the failed job" can silently duplicate or lose data, and the load patterns that prevent it |
| [`09-data-quality-and-testing.md`](docs/09-data-quality-and-testing.md) | The three testing layers, and which specific failure mode each one catches |
| [`10-orchestration-and-tool-landscape.md`](docs/10-orchestration-and-tool-landscape.md) | Mapping tool names (Airflow, dbt, Fivetran, Glue...) to the actual problem each one solves |

## Runnable proof, not just diagrams

`examples/` contains two small, real, executable pipelines processing
the **exact same messy source data** — one using the ETL pattern, one
using ELT — so the difference isn't just described, it's demonstrable:

```bash
python examples/etl_approach/etl_pipeline.py
python examples/elt_approach/elt_pipeline.py
```

**What each one proves, verified by `tests/test_pipelines.py` (run in
CI on every push):**

- **ETL** (`etl_pipeline.py`): the target database's `customers` table
  *only ever* contains clean, deduplicated, properly-cased data — the
  transformation happened in Python before a single row was written.
- **ELT** (`elt_pipeline.py`): the target database ends up with **two**
  tables — `raw_customers` (the original mess: duplicates, nulls,
  inconsistent casing, untouched) and `customers` (clean, produced by
  a SQL transformation run *after* loading, directly against the
  target). Both coexist — this is the bronze/silver split from
  `07-medallion-architecture.md`, shown in miniature.

Real output from an actual run:
```
[EXTRACT] Pulled 4 raw rows from source
[TRANSFORM] 4 raw rows -> 3 cleaned rows (deduped, nulls handled, casing standardized)
[LOAD] Wrote 3 clean rows -> etl_target.db

[EXTRACT] Pulled 4 raw rows from source
[LOAD] Wrote 4 RAW (unmodified) rows -> raw_customers table
[TRANSFORM] Ran SQL in-place against the target -> produced 3 clean rows in a separate 'customers' table
```

## How this connects to the other two projects in this series

| This project's concept | Where it's implemented for real |
|---|---|
| ELT / dbt transformation | `sales-data-pipeline/dbt_project/models/` |
| Medallion architecture | `sales-data-pipeline`'s raw → staging → marts layers |
| Idempotent partition loading | `sales-data-pipeline/docs/runbook.md` backfill procedure |
| Orchestration dependency-waiting | `sales-data-pipeline/dags/sales_pipeline_dag.py` |
| The full SQL transformation layer, hands-on | `sql-portfolio-quickbyte` — every window function, CTE, and query pattern referenced conceptually here is implemented and tested there |

## Repo structure

```
data-pipeline-concepts/
├── docs/                    # the 10 concept deep-dives
├── examples/
│   ├── etl_approach/        # runnable ETL demo
│   └── elt_approach/        # runnable ELT demo
├── tests/test_pipelines.py  # verifies both demos behave as documented
└── .github/workflows/ci.yml # runs the tests + checks for broken doc links on every push
```

## A note on how this was built

Drafted with an AI assistant, the same way the companion SQL portfolio
was — and verified the same way: every code example in `examples/` was
actually executed, not just written, with real output captured before
being documented as fact. The docs themselves make claims that are
checked against real, running code wherever a claim could be verified,
rather than asserted from memory.
