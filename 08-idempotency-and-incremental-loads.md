# Idempotency & Incremental Loading

## What idempotency means in a pipeline context

**A pipeline run is idempotent if running it twice (with the same
input) produces the same result as running it once.** This sounds
obvious until a pipeline actually fails partway through and needs to
be re-run — which is not a hypothetical, it's a routine operational
event (a network blip, a source timeout, a downstream dependency being
temporarily unavailable).

## Why this matters more than it first appears

Imagine a daily pipeline that runs `INSERT INTO fct_sales SELECT ... FROM
todays_orders`. If this job fails halfway through (after inserting half
the day's rows) and Airflow's retry logic simply re-runs it, the
successfully-inserted rows from the first attempt get inserted **again**
— now every order from that day is duplicated. This is one of the most
common real production data-quality incidents, and it's entirely
preventable with the right load pattern.

## Patterns that achieve idempotency

**1. Full overwrite / `TRUNCATE` + reload**
Delete everything in the target for the relevant period, then reload.
Simplest to reason about — re-running always produces the same end
state, regardless of how many times or in what partial state it failed
before. Costly for large tables if done on every run, but the standard
choice for small dimension tables.

**2. `MERGE`/`UPSERT` keyed on a natural or surrogate key**
Instead of blind `INSERT`, use `INSERT ... ON CONFLICT DO UPDATE`
(Postgres), `MERGE` (SQL Server/Snowflake), or dbt's `incremental`
materialization with a `unique_key`. Re-running with the same input
updates existing rows rather than duplicating them — this is the
standard pattern for large fact tables where a full overwrite would be
too expensive to run on every incremental load.

**3. Partition-scoped delete-then-insert**
The pattern used in this repo series' AWS pipeline: data is loaded
partitioned by `ingest_date`. A re-run for a specific day deletes only
that day's partition first, then reloads it — idempotent *per day*
without needing to touch the entire table's history. This is
specifically why `docs/runbook.md` in the AWS project documents
backfilling a single failed day rather than the whole table.

## The connection to CDC and watermarks

An incremental extract using a watermark (`WHERE updated_at >
last_run_timestamp`, see `01-etl-explained.md`) has its own idempotency
subtlety: if the *load* step fails after a *successful* extract, and
the watermark has already advanced, re-running the extract will skip
the rows that failed to load — a silent data loss, not just a
duplicate. The fix is to only advance the watermark **after** a
confirmed successful load, not after extraction — a small but
consequential ordering detail that's easy to get wrong.

## The interview-answerable version of this topic

If asked "how do you handle pipeline failures/retries" — the strong
answer names idempotency explicitly and picks a specific pattern (most
often: partition-scoped delete-then-insert, or MERGE-based upsert) with
a reason tied to the data's actual shape (fact table size, whether
natural keys exist, whether partial-day reloads are common). A weak
answer just says "Airflow retries automatically" without addressing
what happens to *already-written* rows from the failed attempt — that
gap is exactly what this topic exists to close.
