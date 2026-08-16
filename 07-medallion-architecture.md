# Medallion Architecture (Bronze / Silver / Gold)

## What it is

A layered organization pattern for data lakes/warehouses, splitting
data into three progressively refined stages. This is the exact
pattern implemented in this repo series' AWS pipeline project
(`sales-data-pipeline`), where it's called "raw/staging/marts" — the
naming differs by vendor/team, the structure is identical.

```
Source --> BRONZE (raw) --> SILVER (cleaned) --> GOLD (business-ready)
```

## Bronze — raw

An untouched, as-extracted copy of the source data. No cleaning, no
joins, no business logic — this is exactly the output of ELT's "Load"
stage (`02-elt-explained.md`). Its entire purpose is to **preserve the
original** so that any downstream transform bug can be fixed and
re-run from here, without re-extracting from the source system (which
may not even hold the old data anymore by the time the bug is found).

*Maps to: `raw/` in the AWS project, `source()` references in dbt.*

## Silver — cleaned

Deduplicated, null-handled, type-cast, structurally valid — but **not
yet joined across sources or laden with business logic**. This is a
deliberate scope boundary: silver models should be 1:1 with a single
bronze source, doing only the cleaning that source needs, nothing more.

*Maps to: `dbt_project/models/staging/` in the AWS project —
`stg_orders.sql`, `stg_customers.sql`, `stg_products.sql` are textbook
silver-layer models: each cleans exactly one source table, no joins.*

## Gold — business-ready

Joined, aggregated, business-logic-applied tables that analysts and BI
tools query directly. This is where derived metrics live, where
multiple silver tables get combined into a single denormalized fact
table, and where explicit business decisions (e.g. "exclude cancelled
orders") get applied.

*Maps to: `dbt_project/models/marts/fct_sales.sql` in the AWS project —
joins all three staging models, applies the cancelled-order filter,
and derives `revenue_tier` and `days_to_ship`.*

## Why three layers, specifically — the design reasoning

**Each layer has exactly one job, which makes debugging tractable.** If
a number in a dashboard looks wrong, the layered structure gives a
clear diagnostic path: is the raw (bronze) data itself wrong (a source
system problem)? Is the silver cleaning logic wrong (a dedup or
null-handling bug)? Or is the gold business logic wrong (a join
condition or a filter mistake)? Without layering, all of this logic
lives in one tangled query, and a bug could be anywhere.

**Reusability compounds going up the stack.** A silver-layer
`stg_customers` model, cleaned once, can feed *any number* of
gold-layer marts — a sales fact table, a support-ticket fact table, a
marketing-attribution table — all sharing the same cleaning logic
rather than each mart re-implementing its own null-handling.

**This is exactly the ADR reasoning documented in the AWS project's
`docs/decisions.md` (ADR-1)** — worth reading directly, since it's the
same architectural decision, previously justified in the context of a
specific real pipeline rather than in the abstract.

## A common mistake worth naming

Skipping straight from bronze to gold — joining and applying business
logic directly against raw data — is the most common medallion
anti-pattern. It works fine until a cleaning bug (a bad dedup, a
missed null case) needs fixing, at which point it's tangled into every
downstream business-logic query rather than isolated in one silver
model. The extra layer is what buys debuggability and reuse; skipping
it to "save a step" gives that up for very little actual benefit.
