# GATE-03: PgQueuer completion-reliance proof

**Status:** bound (2026-08-01)  
**Blocks:** Story 1.10 and any dispatch-backed feature  
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

- [ ] Integration suite covers P1–P8
- [ ] Story 1.10 AC references this file as proof artifact
- [ ] CI job runs suite against disposable Postgres 18
