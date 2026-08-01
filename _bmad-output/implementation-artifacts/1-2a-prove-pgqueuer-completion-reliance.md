---
baseline_commit: pending
---

# Story 1.2a: Prove PgQueuer Completion Reliance (GATE-03 Spike)

Status: ready-for-dev

## Story

As an operator,
I want the PgQueuer completion-reliance proof (GATE-03 P1–P8) to run immediately after the local stack is up and **before** catalog ingest work begins,
so that queue selection is confirmed or reopened before Stories 1.4–1.9 accumulate code that assumes AD-22.

**Gate:** [`GATE-03-pgqueuer-proof.md`](gates/GATE-03-pgqueuer-proof.md)

**Why this story exists (TECH-001):** The architecture says GATE-03 failure "reopens queue selection." Scheduling the proof at Story 1.10 (tenth of eleven) means Stories 1.4–1.9 would already be written against PgQueuer. Running the same proof after Story 1.2 costs the same and removes an epic's worth of rework exposure. P6 (cancellation) and P7 (W3C trace context on job spans) are not first-class PgQueuer features — both need custom envelope work that must then survive P4's SIGKILL recovery.

## Acceptance Criteria

1. **P1–P8 green on Linux CI + PostgreSQL 18.4**
   - **Given** a disposable PostgreSQL 18.4 (testcontainers or CI service) with migrate complete
   - **When** `backend/tests/integration/test_pgqueuer_reliance.py` runs
   - **Then** scenarios P1–P8 in GATE-03 all pass on a single worker
   - **And** the suite is wired into Linux CI (PR-blocking for this story; nightly thereafter)

2. **Minimal fixture surface only — no catalog domain**
   - **Given** this is a platform spike
   - **When** the proof is implemented
   - **Then** it uses a throwaway owner-row / work-state table (or equivalent fixture) — **not** catalog/taxonomy/enrichment domain tables
   - **And** domain packages remain empty of business logic
   - **And** enqueue remains **after** commit (no transaction-joining producer bridge)

3. **Failure escalates before Story 1.4**
   - **Given** any of P1–P8 cannot be satisfied with PgQueuer 1.3.2
   - **When** the spike concludes
   - **Then** AD-22 queue selection is explicitly reopened with the Architect **before** Story 1.4 starts
   - **And** Stories 1.4–1.9 must not assume PgQueuer until selection is re-bound

4. **GATE-03 checklist and Story 1.10 handoff**
   - **Given** P1–P8 are green
   - **When** this story merges
   - **Then** GATE-03 checklist items for the suite and CI are ticked
   - **And** Story 1.10 retains production dispatch + central retry policy ACs; it reuses this suite as regression rather than discovering reliance late

## Tasks / Subtasks

- [ ] **Scaffold reliance suite** (AC: #1, #2)
  - [ ] Create `backend/tests/integration/test_pgqueuer_reliance.py` with one test per P1–P8 (map IDs in docstrings)
  - [ ] Add a minimal application work-state fixture (states: `pending`, `running`, `retry_wait`, `completed`, `failed`, `cancelled`)
  - [ ] Enqueue-after-commit helper; idempotent handler; re-drive-from-owner-row path

- [ ] **P1–P5 core reliance** (AC: #1)
  - [ ] P1 Enqueue-after-commit — job runs once after owner row commits
  - [ ] P2 Lost enqueue — re-drive recovers; no duplicate effect
  - [ ] P3 Duplicate enqueue — second handler invocation is a no-op
  - [ ] P4 SIGKILL mid-handler — use `kill_role` from `tests/conftest.py`; restart reaches terminal state without double effect
  - [ ] P5 LangGraph resume — `AsyncPostgresSaver` resumes same `thread_id` (`pipeline_run_id`)

- [ ] **P6–P8 envelope gaps** (AC: #1 — highest risk)
  - [ ] P6 Cancellation — run reaches `cancelled` at a safe boundary
  - [ ] P7 Trace propagation — W3C trace context visible on job spans in Phoenix (`pricecomp_phoenix` / port 3022)
  - [ ] P8 Exhausted retries — state `failed`, row inspectable, manual requeue works (≤5 attempts, 15-min cap; `invalid`/`defer` never infra-retry)

- [ ] **CI + gate evidence** (AC: #1, #4)
  - [ ] Ensure `.github/workflows/backend.yml` runs the reliance suite against PostgreSQL 18
  - [ ] Tick GATE-03 checklist; note Story 1.10 inherits green proof
  - [ ] If any scenario fails permanently, stop and escalate — do not paper over with skips

## Dev Notes

### Sequencing (binding)

| Before | This spike | After |
|--------|------------|-------|
| Story 1.2 (stack + roles) merged | GATE-03 P1–P8 | Story 1.3 may proceed in parallel; **Story 1.4+ blocked until green or queue re-selected** |

Story 1.3 (advisory lock) does **not** depend on PgQueuer. Stories 1.4–1.9 must not land dispatch-backed assumptions until this spike passes.

### Architecture compliance

| Decision | Binding |
|----------|---------|
| **AD-22** | Enqueue after commit; idempotent handlers; work states; central retry policy; no transaction-joining producer |
| **AD-16** | Single-worker MVP only — multi-worker races out of scope |
| **AD-12** | W3C trace context on job spans (P7) |
| **AD-27 / NFR17** | PgQueuer 1.3.2, PostgreSQL 18.4, Linux CI is authority |
| **AD-31** | INT + PROC (P4) against disposable Postgres |

### Harness already on disk (TECH-002 closed)

Reuse — do not reinvent:

- `backend/tests/conftest.py` — `postgres_container`, `migrated_database`, `spawn_role`, `terminate_role`, `kill_role`
- Dev deps: `pytest-asyncio`, `testcontainers[postgres]`, `pytest-cov`
- Migrate already installs `pgqueuer` + `langgraph` schemas

### Out of scope

- Catalog snapshot/product/price domain tables (Stories 1.4–1.8)
- Production retry-policy wiring beyond what P8 needs (Story 1.10)
- Multi-worker, leases, fencing, transaction-joining producer
- Changing queue vendor without Architect decision

### References

- [Source: `_bmad-output/implementation-artifacts/gates/GATE-03-pgqueuer-proof.md`]
- [Source: `_bmad-output/test-artifacts/test-design-epic-1.md` — TECH-001 mitigation]
- [Source: `_bmad-output/planning-artifacts/architecture/.../ARCHITECTURE-SPINE.md` — AD-22 + deferred register]
- [Source: `_bmad-output/planning-artifacts/epics.md` — Story 1.10 ACs retained for production dispatch]

## Dev Agent Record

### Agent Model Used

_(pending)_

### Debug Log References

### Completion Notes List

### File List
