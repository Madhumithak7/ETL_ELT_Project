# ETL vs ELT — Direct Comparison & Decision Framework

## Side-by-side

| Dimension | ETL | ELT |
|---|---|---|
| Transform location | Dedicated engine, outside the target | Inside the target, using its own compute |
| Raw data preserved? | Usually not | Yes — this is the whole point of the bronze/raw layer |
| Schema decided | Before loading | After loading (schema-on-read) |
| Best fit for | On-prem warehouses, strict pre-load data masking | Cloud warehouses with elastic compute |
| Reprocessing a bug | Often requires re-extracting from source | Re-run transform against preserved raw data |
| Primary transform language | General-purpose (Python, Java, Spark) or ETL-tool GUI | Primarily SQL (dbt) |
| Storage cost | Lower — only final shape is kept | Higher — raw + intermediate + final all persisted |
| Compute cost model | Separate ETL infra, billed independently | Shows up directly on warehouse compute bill |
| Compliance: sensitive fields | Can be scrubbed before ever reaching the target | Sits in target at least briefly, even if masked downstream |
| Tooling era | Informatica, SSIS, Talend, hand-rolled Spark jobs | dbt, Fivetran/Airbyte (load) + dbt (transform) |

## The decision framework — ask these three questions, in order

**1. Does compliance require certain data to never be persisted in the
target, even temporarily?**
If yes → ETL. This is the one constraint ELT genuinely cannot satisfy,
because ELT's defining property is "raw data lands first." No amount
of downstream masking changes the fact that the raw data touched the
target at some point.

**2. Is the target's compute cheap, elastic, and billed per-use (a
modern cloud warehouse)?**
If yes → ELT is very likely the better default. The historical reason
to avoid transforming inside the target (protecting scarce, expensive
compute) doesn't apply.
If no (the target is compute-constrained, e.g. an operational database
also serving live application traffic) → ETL, to keep transform load
off that system entirely.

**3. Are the transformations expressible in SQL, or do they need a
general-purpose language's full capability** (calling external APIs
mid-transform, complex NLP/ML preprocessing, non-relational data
munging)?
SQL-expressible → ELT (dbt).
Needs Python/Spark-level capability → ETL, or a hybrid (see below).

## It's rarely 100% one or the other in practice

Most real-world modern pipelines are a **hybrid**: extraction tools
(Fivetran, Airbyte, custom scripts) do light validation/type-casting
during load (a small "T" before the "L"), then the bulk of business
logic transformation happens post-load in dbt (the large "T" after).
This is sometimes informally called "ELT with a light ETL step" — worth
naming explicitly in an interview if asked "which one do you use,"
since claiming a pipeline is purely one or the other is often not
accurate to how production systems are actually built.

**The AWS portfolio project in this series is a real example of this
hybrid**: the Python extract script does light cleaning during
generation, `load_to_s3.py` loads raw data into S3 essentially
untransformed (the ELT "L" step), and dbt then does all substantive
transformation against Athena (the ELT "T" step) — see that project's
`docs/decisions.md` (ADR-4) for the explicit reasoning behind choosing
dbt/ELT for that specific pipeline.

## A common interview trap worth naming directly

**"ELT is strictly better/newer, so ETL is outdated"** is a wrong
answer, and interviewers who ask this question are often specifically
listening for whether a candidate falls into that trap. The honest
answer is that ELT became the *more common default* because cloud
warehouse economics changed — not because ETL was a worse idea that
got fixed. ETL remains the *correct* choice under the specific
conditions in the decision framework above (compliance-driven pre-load
masking being the clearest one). A strong interview answer names the
trade-off explicitly rather than declaring a winner.
