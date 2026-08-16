# Slowly Changing Dimensions (SCD)

## The problem this solves

Dimension tables (customers, products, employees — the "who/what/where"
tables joined against a fact table) change over time: a customer moves
country, a product gets recategorized, an employee changes department.
The question SCD types answer: **when a dimension row changes, what
happens to the history of facts that referenced the old version?**

## SCD Type 0 — retain original

The dimension attribute is never updated after the first load, even if
the source value changes. Used for genuinely immutable facts (e.g. a
customer's original signup date/channel) where preserving the
*original* value is the entire point.

## SCD Type 1 — overwrite (no history kept)

The old value is simply replaced with the new one. Simplest to
implement — a plain `UPDATE`. **The cost:** every fact previously
joined to this row now shows the *new* attribute value, even for facts
that happened before the change. If a customer moves from Germany to
France, Type 1 makes it look like they were always in France — all
their historical orders now report as French orders too.

**When it's the right choice:** the attribute is a correction, not a
real change (fixing a typo in a name), or historical accuracy for this
specific attribute genuinely doesn't matter for the business questions
being asked.

## SCD Type 2 — add a new row, preserve history (the most common approach)

Instead of overwriting, a **new row** is inserted with the updated
value, and the old row is kept but marked as no-longer-current —
typically via `effective_date`, `end_date`, and `is_current` columns:

```
customer_id  surrogate_key  country  effective_date  end_date    is_current
1            101            Germany  2023-01-01      2024-06-14  false
1            102            France   2024-06-15      NULL        true
```
Facts are joined against the surrogate key that was current *at the
time the fact occurred* — so historical orders correctly still show
"Germany," while new orders correctly show "France." This is what
actually preserves history.

**Cost:** more complex ETL/ELT logic (the load step must compare
incoming rows against current dimension state and decide whether to
insert a new version or leave as-is), and dimension tables grow over
time as history accumulates.

**This is the industry-standard default** for dimensions where
historical accuracy matters — which is most of them in a genuine
analytics warehouse.

## SCD Type 3 — track limited history in the same row

Instead of new rows, the change is tracked in additional columns on the
*same* row: `current_country`, `previous_country`. Only remembers
**one** prior state, not full history — a second change overwrites the
"previous" column, losing the state before that.

**When it's the right choice:** genuinely rare — only when a business
question specifically needs "current vs. immediately prior" and never
needs anything further back, and the team wants to avoid Type 2's
row-growth. Type 2 is almost always preferred when in doubt, since it
doesn't foreclose future questions the way Type 3's limited memory does.

## Quick decision guide

| Need | Type |
|---|---|
| Attribute should never change after first load | 0 |
| Only the latest value matters, ever | 1 |
| Full history matters, facts should reflect the value *at the time* | 2 (default choice when unsure) |
| Only "current vs. one-step-back" matters | 3 |

## Where this connects to ETL/ELT

SCD Type 2 logic is a genuine example of transformation complexity
that pushes a pipeline toward the ELT/dbt pattern discussed in
`03-etl-vs-elt-comparison.md` — dbt has built-in **snapshot**
functionality specifically for implementing SCD Type 2 as version-
controlled SQL, comparing each run's incoming data against the
dimension's current state and automatically managing the
effective_date/end_date/is_current bookkeeping described above.
