# Data Quality & Testing

## Why this is a distinct topic from "the pipeline runs successfully"

A pipeline can execute without any errors and still produce **wrong**
data — a job that runs green every night while silently dropping 30%
of rows due to a bad join condition is a common, dangerous failure
mode precisely because nothing alerts anyone. Data quality testing
exists to catch *correctness* failures, which are a different problem
from *execution* failures (which orchestration retries/alerting,
`08-idempotency-and-incremental-loads.md`, already handle).

## The three layers of testing, matched to this repo series

This exact three-layer structure was implemented in the AWS pipeline
project — worth pointing back to as a concrete example rather than
just theory:

**1. Unit tests on transformation logic**
Test the *rules* in isolation, with small hand-built inputs — does the
dedup logic actually dedup, does a boundary value (exactly 400.00,
not 399.99) land in the right tier. See `sales-data-pipeline/tests/test_transform.py`
for a real example, including the explicit boundary-value tests that
catch the classic `<` vs `<=` off-by-one bug.

**2. Schema/data tests against real materialized data**
Assertions run against the actual built tables: uniqueness, not-null,
accepted-value-set checks. dbt's built-in test types (`unique`,
`not_null`, `accepted_values`, `relationships`) cover the majority of
real-world cases — see `sales-data-pipeline/dbt_project/models/schema.yml`
for these applied to a real fact table.

**3. Pipeline-level smoke tests**
Run the full extract → transform flow end-to-end in CI on every
change, catching integration-level breaks (a column rename in one
module that another module still expects) that isolated unit tests
miss. See the `.github/workflows/ci.yml` in the AWS project.

## Categories of data quality checks, independent of which layer runs them

- **Uniqueness** — is this supposed-to-be-unique key actually unique?
  (catches duplicate extraction/join fan-out bugs)
- **Completeness/not-null** — are required fields actually populated?
- **Referential integrity** — does every foreign key actually resolve
  to a row in the parent table? (catches join/extraction ordering bugs
  — e.g. loading orders before the customers they reference exist)
- **Validity/accepted values** — does a categorical column only contain
  values from its known valid set? (catches upstream schema drift —
  a new order status value appearing that downstream logic doesn't
  know how to handle)
- **Freshness** — has this table actually been updated recently, or is
  a silently-failing upstream job leaving it stale?
- **Volume/anomaly checks** — did today's row count fall within a
  normal range, or did it unexpectedly drop to zero or spike 10x?
  (catches extraction failures that technically "succeeded" but pulled
  wrong/incomplete data)

## Where to run each check — a genuine trade-off, not just "test everything everywhere"

Running every check at every layer is wasteful; the right question is
**where does this specific failure mode actually originate**:
- Logic correctness (a tiering threshold, a dedup rule) → unit test,
  cheap and fast, run on every code change before any real data is
  touched
- Structural integrity of real data (uniqueness, nulls, referential
  integrity) → schema tests against materialized tables, since these
  can only be verified against real data shape, not a hand-built test
  fixture
- "Did the whole pipeline actually work end to end" → CI smoke test /
  post-load pipeline assertions

## The interview-answerable framing

A strong answer to "how do you ensure data quality" names this layered
structure explicitly, with a concrete example of a bug each layer
would have caught that the others wouldn't — e.g. "a unit test catches
a wrong tiering formula before it ever touches real data; a uniqueness
test on the materialized table catches a join that accidentally
fanned out order rows; neither would catch an upstream API silently
going down, which is what a freshness check is for." Naming *which*
failure mode each check catches is what distinguishes a real
understanding from reciting a list of test types.
