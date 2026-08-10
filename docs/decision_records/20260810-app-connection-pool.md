# Decision Record: Process-wide app connection pool

- **Status:** Accepted
- **Decision Makers:** Engineering
- **Date:** 2026-08-10
- **Related Decision Records (Optional):** N/A

## Context

- Pipeline stage tools closed over one live `psycopg.Connection` per product so reads/writes reused a single session (design discussion: "where the nodes write", Option B).
- LangGraph's `ToolNode` can run multiple tool calls from one model turn in parallel (thread pool / `Send`). A `psycopg.Connection` is not safe for concurrent use, including read-only queries: concurrent callers race on one session and one wire protocol stream.
- Holding that connection for the whole product graph also kept sessions open across LLM latency (idle-in-transaction risk when `autocommit=False`).
- `psycopg-pool` was already a dependency; runners used one-off `psycopg.connect` via `connect_app`.

## Decision

- Introduce `platform/persistence/db.py` with a process-wide `ConnectionPool` per database URL.
- `connect_app(url)` becomes a context manager that **checks out** an exclusive connection and returns it to the pool on exit (same call-site shape: `with connect_app(url) as conn:`).
- Pipeline `StageDeps` holds the **pool**, not a connection. Tools and nodes check out per unit of work.
- Docstrings on the pool module, `connect_app`, repositories, `StageDeps`, and tool factories state explicitly that connections must not be shared across concurrent tasks.

## Consequences

- _Positive_: Parallel tool calls (e.g. multiple `search_categories` in one turn) are safe.
- _Positive_: Connections are not held across LLM waits; pool reset rolls back on check-in.
- _Positive_: Codebase documents the concurrent-access rule at the lease boundary.
- _Neutral_: `connect_app` is still the common API; most runners/tests needed no call-site change beyond pipeline graph wiring.
- _Negative_: Slightly more checkout churn than one long-lived per-product connection; bounded by `DEFAULT_POOL_MAX_SIZE` (16).
- _Negative_: Tests/session teardown must `close_app_pools()` before dropping databases so pooled sessions do not block `DROP DATABASE`.

## Alternatives Considered

- **Keep one connection + `threading.Lock` around tool bodies** — serializes DB work and still holds a session across the agent loop; rejects parallel search benefit.
- **Open a fresh unpooled connection per tool call** — safe but reconnect-heavy; pool is the same pattern with reuse.
- **Async `AsyncConnectionPool` only** — pipeline tools today are sync; sync pool matches the current stack.

## References

- `docs/plans/20260806-backend-two-stage-pipeline-design-discussion.md` (connection scope / tool factories)
- `backend/src/agentic_cataloger/platform/persistence/db.py`
