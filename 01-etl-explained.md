# ETL — Extract, Transform, Load

## What it is

ETL is a three-stage data integration pattern where data is transformed
**before** it lands in its final destination:

```
Source System(s) --> [EXTRACT] --> [TRANSFORM] --> [LOAD] --> Target (warehouse/lake)
```

The critical property: **the transformation happens in a separate
processing layer, outside the target system, before any data is
written to it.** The target only ever receives clean, modeled,
already-shaped data.

## Stage-by-stage breakdown

### 1. Extract

Pulling data out of one or more source systems — an OLTP database, a
SaaS API, a file drop, a message queue. Two extraction strategies
matter here, and the choice has real downstream consequences:

- **Full extraction** — pull the entire source table every run. Simple,
  always correct, but doesn't scale: extracting 50M rows every night to
  find the 200 that changed is wasteful and slow.
- **Incremental extraction** — pull only what changed since the last
  run, using a watermark column (`updated_at > last_run_timestamp`) or
  Change Data Capture (see `05-change-data-capture.md`). Scales far
  better, but requires the source to reliably expose "what changed" —
  not every system does this cleanly (hard deletes are the classic gap:
  a row that's physically removed leaves no `updated_at` to detect).

### 2. Transform

This is what defines ETL as a pattern: cleaning, joining, aggregating,
type-casting, and business-rule logic all happen **in a dedicated
processing engine** — historically a standalone ETL server (Informatica,
SSIS, Talend), today often a Spark cluster or a Python/pandas job —
sitting between the source and the target.

Typical transform-stage responsibilities:
- deduplication and null handling
- joining data from multiple sources into one shape
- applying business rules (e.g. currency conversion, unit standardization)
- data quality validation — reject or quarantine bad records *before*
  they ever reach the target
- restructuring from source shape into target schema (e.g. flattening
  a nested JSON API response into relational rows)

### 3. Load

Writing the already-transformed, already-modeled data into the target
system. Because the data arrives pre-shaped, the target's job is
comparatively simple: append or upsert clean rows into an existing
schema.

## Why ETL was the default pattern for decades

Before cheap cloud compute and cloud data warehouses, **the target
database itself was the expensive, limited resource** — an on-premises
data warehouse (Teradata, Oracle) had fixed hardware, licensed by core
count, and every CPU cycle spent transforming data inside it was a
cycle not available for end-user queries. Pushing transformation logic
onto a separate, cheaper ETL server protected the warehouse's scarce
compute for what it was actually bought for: serving queries.

## Genuine strengths of ETL (not just "the old way")

- **Sensitive data can be scrubbed/masked before it ever reaches the
  target** — relevant for PII/compliance: if a field must never exist
  in the warehouse at all (not even temporarily), ETL's pre-load
  transformation is the only pattern that guarantees that.
- **The target only ever holds clean, query-ready data** — no "raw and
  messy" intermediate state that an accidental early query might hit.
- **Transform logic is decoupled from the target's compute/pricing
  model** — relevant when the target charges per query or per compute-
  second and you don't want transformation cost mixed into that bill.

## Genuine weaknesses

- **Schema must be decided upfront**, before loading — adding a new
  source field later often means reworking the transform stage's
  logic, not just adding a column.
- **The original raw data is often not preserved** — if a transform bug
  is discovered later, there may be nothing to "replay" from, since
  only the transformed output was ever kept.
- **Transform-stage compute doesn't scale as elastically** as a modern
  cloud warehouse's compute does — a dedicated Spark cluster or ETL
  server has its own capacity ceiling, separate from the target.

## Where ETL is still the right choice today

Not obsolete — still the correct pattern when:
- regulatory/compliance requirements mean sensitive fields must be
  masked or dropped **before** they reach any persisted store
- the target system has genuinely limited compute (an operational
  database that also serves live application traffic, not a dedicated
  analytics warehouse)
- transformations are complex enough to need a general-purpose
  programming language's full capability (Python/Spark) rather than
  what's expressible in SQL alone

See `03-etl-vs-elt-comparison.md` for the full side-by-side decision
framework.
