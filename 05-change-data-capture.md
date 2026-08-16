# Change Data Capture (CDC)

## The problem CDC solves

Referenced back in `01-etl-explained.md`: incremental extraction using
a watermark column (`WHERE updated_at > last_run`) has a fundamental
gap — it can't see **deletes**. If a row is physically removed from the
source, there's no `updated_at` value to compare against; the row is
just gone, and a watermark-based extract silently never notices.

CDC solves this by reading the source database's own internal record
of every change — inserts, updates, *and* deletes — rather than
querying the current state of a table and inferring what changed.

## How it actually works

Most production CDC implementations read the database's **transaction
log** (Postgres's WAL — Write-Ahead Log, MySQL's binlog, SQL Server's
change tracking) — the same internal log the database uses for its own
crash recovery and replication. Every write to the database, of any
kind, is recorded there in order, before the write is even considered
committed.

A CDC tool (Debezium is the most common open-source one; Fivetran and
similar vendors implement this internally too) tails that log
continuously and emits a stream of change events:
```
{"op": "INSERT", "table": "orders", "before": null, "after": {...}}
{"op": "UPDATE", "table": "orders", "before": {...}, "after": {...}}
{"op": "DELETE", "table": "orders", "before": {...}, "after": null}
```
These events are typically published to a message queue (Kafka is the
standard pairing with Debezium), from which a downstream consumer
writes them into the target — often as a stream, connecting this
concept directly back to `04-batch-vs-streaming.md`.

## Why log-based CDC over "just query the table more often"

- **Deletes are captured** — the transaction log records a delete as an
  explicit event, unlike a watermark query which has nothing to select.
- **No extra load on the source database's query engine** — reading the
  transaction log is a fundamentally different, much lighter operation
  than running repeated `SELECT` queries against production tables,
  which matters when the source is also serving live application
  traffic and can't tolerate heavy extraction queries competing for
  resources.
- **Every intermediate state is captured, not just the latest** — if a
  row is updated three times between extraction runs, a watermark-based
  batch extract only ever sees the final state; log-based CDC sees all
  three changes, which matters for use cases like audit trails or
  event-sourced rebuilding of history.

## Trade-offs worth naming honestly

- Meaningfully more infrastructure to operate than a scheduled SQL
  query — a message queue, a CDC connector, and typically a streaming
  consumer, versus a single cron-scheduled `SELECT`.
- Requires the source database to support log-based replication in the
  first place, and often requires elevated database permissions to set
  up — not something every team controlling the source system will
  grant readily.
- Schema changes on the source (a column added/renamed) need explicit
  handling in the CDC pipeline, or downstream consumers can break.

## When it's worth the complexity

CDC earns its operational cost when: deletes genuinely matter to
downstream consumers (not just inserts/updates), the source is a
high-write-volume operational database that can't tolerate heavy
polling queries, or near-real-time freshness is a real requirement
(connecting back to streaming, `04-batch-vs-streaming.md`). For a
low-write-volume source with a daily batch requirement and no
meaningful delete activity, a simple watermark-based incremental
extract is usually the right, much simpler choice — CDC is not a
default, it's a tool reached for when its specific problem (deletes,
write-heavy sources, real-time needs) is actually present.
