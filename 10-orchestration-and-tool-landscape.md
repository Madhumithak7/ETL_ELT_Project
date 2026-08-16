# Orchestration & the Modern Data Tool Landscape

## What "orchestration" actually means

Coordinating *when* and *in what order* pipeline steps run, handling
dependencies between them, retrying failures, and surfacing what
happened. This is a distinct concern from any single step's own logic
— an orchestrator doesn't extract or transform data itself, it decides
when the extract step should run, waits for it to genuinely finish
before triggering the next step, and handles what happens when a step
fails. See `sales-data-pipeline/dags/sales_pipeline_dag.py`'s own
docstring for a concrete real-example justification of why this
coordination layer earns its complexity over a simpler script.

## Mapping tools to the concept they solve — not just a list of names

It's easy to memorize tool names without understanding what job each
one does. Grouped by function instead:

### Extraction / Loading (the "EL" in ELT)
- **Fivetran, Airbyte** — managed/open-source connectors that handle
  extraction + raw loading for hundreds of common source types
  (Salesforce, Stripe, Postgres) without hand-writing extraction code.
  The trade-off: less control over exactly how extraction happens, in
  exchange for not building/maintaining connector code yourself.
- **Custom scripts (boto3, requests, DB drivers)** — full control, more
  maintenance burden. The right choice when a source isn't supported
  by a managed connector, or extraction logic has unusual requirements.
  This is what `sales-data-pipeline/src/extract/` and `src/load/`
  demonstrate directly.

### Transformation (the "T")
- **dbt** — SQL-based, version-controlled transformation, the standard
  choice for ELT-pattern pipelines (`02-elt-explained.md`). Doesn't
  move data; generates and runs SQL against the warehouse.
- **Spark (PySpark, Databricks)** — distributed processing for
  transformations too large or complex for single-node SQL, or that
  need Python's full capability mid-transform (ML preprocessing, complex
  parsing). More often paired with the ETL pattern or very large-scale
  ELT.

### Orchestration
- **Airflow** — the most widely-used open-source orchestrator; DAGs
  defined in Python, strong ecosystem of pre-built operators (including
  the AWS Glue operators used in `sales-data-pipeline/dags/`).
- **Dagster, Prefect** — newer alternatives with a stronger emphasis on
  data-asset-centric (not just task-centric) orchestration and local
  development ergonomics. Worth naming as alternatives in an interview
  to show awareness the field isn't Airflow-only, even if Airflow is
  what's actually implemented in a given project.

### Storage / Warehouse
- **S3 / GCS / Azure Blob** — object storage, the "lake" layer.
- **Snowflake, BigQuery, Redshift, Athena** — cloud warehouses/query
  engines, the "L" and "T" destination in ELT. Athena specifically
  (used in `sales-data-pipeline`) is serverless/pay-per-query rather
  than a provisioned cluster — see that project's `docs/decisions.md`
  (ADR-2) for the explicit cost reasoning behind that specific choice.

### Cataloging / Metadata
- **AWS Glue Data Catalog, Hive Metastore** — track what tables/schemas
  exist across the lake, enabling query engines like Athena to know
  what's queryable without manually maintained DDL.

## The genuinely important interview point

**Tool knowledge is not the same as pattern knowledge, and interviewers
who are any good can tell the difference.** Knowing that "Airflow
orchestrates and dbt transforms" is trivia; being able to explain *why*
a DAG needs to wait for a Glue Crawler before running dbt (a genuine
dependency, not just "because that's the order") is understanding. Every
tool in this landscape is replaceable — Dagster instead of Airflow,
Snowflake instead of Athena — but the underlying problem each one
solves (coordination, extraction, transformation, storage, cataloging)
doesn't change. This entire docs series is written to prioritize that
distinction throughout.
