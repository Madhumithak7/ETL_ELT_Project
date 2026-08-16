# Batch vs Streaming Processing

## The core distinction

**Batch**: data is collected over a window of time, then processed all
at once, on a schedule (hourly, nightly, weekly).
**Streaming**: data is processed continuously, record-by-record (or in
very small "micro-batches"), as it arrives — with results available
within seconds of an event happening.

This is an orthogonal axis to ETL vs ELT — either transform-ordering
pattern can be run in batch or streaming mode. The two decisions
(where transformation happens, and how often/how continuously it runs)
are independent choices.

## Batch processing

**How it works:** a job runs on a schedule (via Airflow, cron, or a
warehouse's native scheduler), reads everything that's accumulated
since the last run, processes it, and finishes. The pipeline built in
this repo's companion AWS project (`sales-data-pipeline`) is a batch
pipeline — the Airflow DAG runs `@daily`.

**When it's the right choice:**
- the business question doesn't need up-to-the-second freshness (a
  "yesterday's sales" report is fine to compute once, overnight)
- source systems naturally produce data in batches anyway (a daily
  file export from a partner)
- simpler to build, test, and reason about — a batch job either ran
  and succeeded, or it didn't; there's a clear notion of "this run's
  output"

**Genuine limitation:** data is only ever as fresh as the last run.
A daily batch means a number reported at 9am could be up to 24 hours
stale.

## Streaming processing

**How it works:** a continuously-running process consumes events as
they're produced — typically from a message queue/log (Kafka, Kinesis,
Pub/Sub) — and processes each event (or small micro-batch of events)
immediately, often within milliseconds to seconds.

**When it's the right choice:**
- the business need genuinely requires near-real-time answers (fraud
  detection, live inventory counts, real-time personalization)
- source events are naturally a continuous stream (clickstream data,
  IoT sensor readings, application logs)

**Genuine costs:**
- meaningfully more operationally complex — a streaming job doesn't
  "finish," it runs forever, which means monitoring, alerting, and
  failure recovery all look different from a batch job's simple
  success/fail model
- exactly-once processing guarantees (making sure an event is counted
  exactly once, not zero or twice, even across failures/restarts) are
  a genuinely hard distributed-systems problem — this is where most
  streaming pipeline bugs live
- typically more expensive to run continuously than to run a batch job
  once a day

## The honest framing for an interview answer

**Don't default to "streaming is more advanced/better."** The correct
answer to "would you use batch or streaming here" is almost always
"it depends on how fresh the answer needs to be, weighed against the
real operational complexity streaming adds." A daily sales dashboard
built with unnecessary streaming infrastructure is over-engineering,
not sophistication — and naming that trade-off explicitly is a much
stronger interview answer than reflexively reaching for Kafka.

## A useful middle ground: micro-batch

Many "streaming" systems in practice run in very small batches (every
1-5 minutes) rather than true per-event processing — this captures
most of the freshness benefit of streaming with meaningfully less
operational complexity than true event-at-a-time processing. Worth
naming as an option: it's often the pragmatic answer between "daily
batch" and "true streaming," and tools like Spark Structured Streaming
default to this model.
