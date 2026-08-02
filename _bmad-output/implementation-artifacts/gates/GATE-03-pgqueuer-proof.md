# GATE-03: PgQueuer completion-reliance proof

**Status:** bound (2026-08-01); **resequenced** (2026-08-01) per TECH-001  
**Blocks:** Stories **1.4+** and any dispatch-backed feature — proof must be green (or queue selection reopened) **before** catalog ingest accumulates PgQueuer assumptions  
**Runs as:** Story **1.2a** spike immediately after Story 1.2; Story **1.10** reuses the suite as regression while landing production dispatch + central retry policy  
**Evidence location:** `backend/tests/integration/test_pgqueuer_reliance.py` (green on Linux CI + Postgres 18)

## Scope (binding)

Single-worker MVP only. **Out of scope:** multi-worker races, transaction-joining producer, leases/fencing tokens.

## Required scenarios (binding)

| ID | Scenario | Pass when |
|----|----------|-----------|
| P1 | Enqueue-after-commit | Job runs once after owner row commits |
| P2 | Lost enqueue | Re-drive from owner row recovers work; no duplicate effect |
| P3 | Duplicate enqueue | Second handler invocation is a no-op |
| P4 | SIGKILL mid-handler | Restart reaches terminal state without double effect |
| P5 | LangGraph resume | `AsyncPostgresSaver` resumes same `thread_id` (`pipeline_run_id`) |
| P6 | Cancellation | Run reaches `cancelled` at safe boundary |
| P7 | Trace propagation | W3C trace context visible on job spans in Phoenix |
| P8 | Exhausted retries | State `failed`, row inspectable, manual requeue works |

## Work states (binding — AD-22)

`pending`, `running`, `retry_wait`, `completed`, `failed`, `cancelled`.

Transient infra: up to **5** retries, exponential full jitter, cap **15 min**.  
`invalid` / `defer`: **no** infrastructure retry.

## Story checklist (implementation fills these)

- [x] Integration suite covers P1–P8 (`test_pgqueuer_reliance.py`)
- [x] Story **1.2a** AC references this file as proof artifact; Story **1.10** AC references it as regression
- [x] CI job runs suite against disposable Postgres 18 (PR-blocking for 1.2a; nightly thereafter)
- [ ] If any scenario cannot be satisfied, Architect reopens AD-22 queue selection **before** Story 1.4

**Evidence (2026-08-01):** `backend/tests/integration/test_pgqueuer_reliance.py` — P1–P8 green. Story 1.10 reuses this suite as regression; production dispatch + central retry policy remain Story 1.10.
