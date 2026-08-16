# ELT — Extract, Load, Transform

## What it is

ELT reorders the same three operations so that raw data is loaded into
the target **first**, and transformation happens **after**, using the
target system's own compute:

```
Source System(s) --> [EXTRACT] --> [LOAD] --> Target (warehouse/lake) --> [TRANSFORM, in-place]
```

The critical property: **the target system does the transformation
work itself**, typically via SQL run directly against the warehouse
(often orchestrated by a tool like dbt — see this project's earlier
SQL portfolio for a worked example of exactly this: raw tables →
staging models → mart models, all transformed via SQL running inside
Postgres/Athena, not in an external engine).

## Stage-by-stage breakdown

### 1. Extract

Identical concern to ETL's extract stage — full vs. incremental
extraction, watermarking, CDC. The *extraction* problem doesn't change
between ETL and ELT; only what happens after loading does.

### 2. Load

Raw, untransformed (or minimally transformed — see "raw vs. lightly
cleaned" below) data is loaded directly into the target as-is. This is
what enables the medallion/bronze-silver-gold pattern
(`07-medallion-architecture.md`): the "raw" or "bronze" layer is
*exactly* what ELT's load stage produces — an untouched copy of the
source, landed before any transformation logic has touched it.

### 3. Transform

Transformation happens **inside** the target system, using its own
query engine — SQL primarily, sometimes Python via the warehouse's
native support (e.g. Snowpark, BigQuery's Python UDFs). This is where
tools like **dbt** live: dbt doesn't move data anywhere — it generates
and runs SQL `CREATE TABLE/VIEW AS SELECT` statements against the
warehouse's own compute, turning raw tables into staging models into
business-ready marts, entirely inside the target.

## Why ELT became the default pattern for cloud data platforms

The core enabler: **modern cloud warehouses (Snowflake, BigQuery,
Redshift, Athena) decouple storage from compute and scale compute
elastically, billed per-second or per-query.** The old ETL-era
assumption — "the warehouse's compute is scarce and expensive, protect
it" — stopped being true. Once warehouse compute is cheap and scales on
demand, there's no longer a strong reason to do transformation work
somewhere else first; you might as well load the raw data immediately
and let the warehouse itself do the (now-cheap) transformation work,
with all the benefits that follow from doing so.

## Genuine strengths of ELT

- **Raw data is always preserved** — the untouched bronze/raw layer
  means a transform bug discovered months later can be fixed and
  simply *re-run* against the original data, with no re-extraction
  needed from the source system (which may not even have the old data
  anymore).
- **Schema-on-read flexibility** — since raw data lands before any
  schema decisions are enforced, adding a new downstream transformation
  that uses a field nobody previously cared about doesn't require
  re-architecting the extraction pipeline — the field was already
  landed, just unused.
- **Transformation logic lives in version-controlled SQL** (dbt models),
  giving lineage, testing, and documentation essentially for free —
  this is the exact structure demonstrated in this project's companion
  SQL portfolio (`09_views_ctas_procs_triggers.sql` and the star-schema
  capstone).
- **Leverages the warehouse's massively parallel compute** instead of a
  separate, smaller processing cluster — often meaningfully faster for
  large joins/aggregations than an external Spark job would be.

## Genuine weaknesses

- **Raw, unmasked data sits in the target, even if only briefly** — a
  real problem if the target has looser access controls than the
  source, or if compliance requires certain fields to never be
  persisted at all (not even temporarily pre-transformation). This is
  ELT's sharpest disadvantage versus ETL.
- **Storage cost for raw + intermediate + final layers** — medallion
  architecture typically keeps bronze, silver, *and* gold copies of the
  data simultaneously, which costs more storage than ETL's
  transform-then-load-once approach (usually a worthwhile trade for
  cheap object storage, but a real cost nonetheless).
- **Transform logic is now coupled to the target's SQL dialect and
  compute pricing** — a transformation that would be trivial in Python
  (calling an external ML model, complex string parsing) can be awkward
  or impossible in pure SQL, and every transformation run now shows up
  directly on the warehouse's compute bill.

## Where ELT is the right default today

The default choice for most modern analytics pipelines, specifically
when:
- the target is a cloud warehouse/lake with elastic, reasonably-priced
  compute (which is now the common case)
- transformations are primarily SQL-expressible (joins, aggregations,
  business logic on structured data)
- raw-data lineage and re-processability matter (e.g. "we found a bug
  in a transform from 3 months ago, we need to re-derive corrected
  numbers")
- the team wants transformation logic version-controlled, tested, and
  documented as code (dbt's entire value proposition)

See `03-etl-vs-elt-comparison.md` for the full side-by-side decision
framework, and `examples/` in this repo for runnable code demonstrating
both patterns against the same source data.
