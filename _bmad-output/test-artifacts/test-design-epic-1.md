---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted:
  [
    'step-01-detect-mode',
    'step-02-load-context',
    'step-03-risk-and-testability',
    'step-04-coverage-plan',
    'step-05-generate-output',
  ]
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-01'
mode: 'epic-level'
epic_num: 1
inputDocuments:
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/architecture/architecture-agentic-cataloger-2026-07-31/ARCHITECTURE-SPINE.md
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md
  - _bmad-output/implementation-artifacts/gates/GATE-02-db-privileges.md
  - _bmad-output/implementation-artifacts/gates/GATE-03-pgqueuer-proof.md
  - backend/pyproject.toml
  - backend/tests/domain/test_structural_seed.py
---

# Test Design: Epic 1 — Runnable Python Stack with Non-Destructive Catalog Ingest

**Date:** 2026-08-01
**Author:** Nathan
**Status:** Draft

---

## Executive Summary

**Scope:** Full epic-level test design for Epic 1 (stories 1.1–1.11), covering FR1–FR7,
FR49–FR52, FR55, FR56–FR58, governed by AD-1, AD-2, AD-6, AD-13–AD-16, AD-22, AD-23,
AD-26–AD-30.

**Risk Summary**

- Total risks identified: **16**
- High-priority risks (score ≥ 6): **7** — of which **2 score 9 (BLOCK)**
- Critical categories: **DATA** (7 risks), **TECH** (4), **OPS** (3), **SEC** (1), **PERF** (1)

**Coverage Summary**

| Bucket | Scenarios | Estimate |
| --- | :-: | --- |
| Test-harness foundation | — | ~12–20 h |
| P0 | 51 | ~60–90 h |
| P1 | 27 | ~25–40 h |
| P2 / P3 | 9 | ~9–18 h |
| **Total** | **87** | **~106–168 h (~3–5 weeks)** |

**The headline finding is sequencing, not volume.** Both score-9 risks are cheap to resolve and
severe only because the epic currently plans to discover them late:

1. **TECH-002** — **CLOSED** in Story 1.2. Dev group now includes `pytest-asyncio`,
   `testcontainers[postgres]`, `pytest-cov`; `conftest.py` provides disposable PG 18.4 plus
   `spawn_role` / `terminate_role` / `kill_role`; CI emits coverage reports.
2. **TECH-001** — **RESEQUENCED**. GATE-03 runs as Story **1.2a** immediately after 1.2
   (before Stories 1.4–1.9). Story 1.10 keeps production dispatch ACs and reuses the suite as
   regression. Proof itself is still pending (`ready-for-dev`).

The second structural finding: four of the five score-6 risks are **silent** data-integrity
failures — enrichment wipe, double-applied effects, synthesised identity, absence-driven
deletion. All four leave a system that looks healthy. The coverage plan answers this with
assertions on what did **not** change, which is a materially different test shape from happy-path
verification and is budgeted accordingly.

---

## Not in Scope

| Item | Reasoning | Mitigation |
| --- | --- | --- |
| **Epics 2–6** | All at `backlog`; Epic 1 is the only `in-progress` epic | Separate test design per epic when each activates |
| **Frontend (`frontend/`)** | Untouched until Epic 5; AD-15 keeps it on the legacy API through rebuild | Epic 5 test design; 1.11-INT-002 asserts legacy stays read-only |
| **Legacy TypeScript suites** | GATE-01 states no requirement to pass legacy build or test — reference-only until parity | Legacy frozen at ports 3010/5532; AD-15 forbids carrying legacy semantics across |
| **Multi-writer concurrency and crash-window suites** | Explicitly out of MVP under AD-16's single-writer premise (AD-31) | Story 1.3 proves the guard that makes the omission safe; suites return with the deferred concurrency machinery |
| **Taxonomy topology compare-and-set, leases, fencing tokens** | Deferred by AD-16; no code exists to test | Reopens the moment a second concurrent writer runs |
| **External authN/authZ, threat model** | Deferred to a security initiative (AD-32); public exposure prohibited | GATE-02 least-privilege tests cover the internal boundary |
| **Backup/restore drills, RPO/RTO** | Deferred — no non-local data yet; AD-15 makes recovery equal re-import | 1.11-E2E-002 proves recovery-by-replay |
| **Embeddings / `retrieval` package** | AD-35 retired by the MVP scope reduction | 1.1-UNIT-002 asserts the package stays absent |
| **Indexed comparison projection** | Deferred until derive-on-read is measured too slow | PERF-001 raised because no threshold exists to measure against (CL-3) |
| **Load and stress testing** | No performance threshold exists anywhere in Epic 1 | X-INT-001 records a non-gating baseline so a threshold can later be set from data |

---

## Risk Assessment

### Critical Risks (Score 9 — BLOCK)

| Risk ID | Category | Description | P | I | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | :-: | :-: | :-: | --- | --- | --- |
| TECH-001 | TECH | GATE-03 P1–P8 cannot all be satisfied by PgQueuer 1.3.2, reopening queue selection after dependent code exists | 3 | 3 | **9** | Run the P1–P8 proof as Story **1.2a** spike immediately after Story 1.2, before Stories 1.4–1.9 | Dev + TEA | Story 1.2a (before 1.4) — **resequenced; proof pending** |
| TECH-002 | TECH | Test toolchain cannot express Epic 1's mandatory tests — no async driver, no disposable PostgreSQL, no process harness, no coverage | 3 | 3 | **9** | Add dev dependencies, `conftest.py`, disposable-DB fixture, process-spawn/kill harness, CI coverage wiring | Dev | **CLOSED** (Story 1.2) |

### High-Priority Risks (Score 6 — MITIGATE)

| Risk ID | Category | Description | P | I | Score | Mitigation | Owner | Timeline |
| --- | --- | --- | :-: | :-: | :-: | --- | --- | --- |
| DATA-001 | DATA | D6 recurrence — catalog upsert widens over Epic 3+ and silently overwrites enrichment-owned values | 2 | 3 | 6 | Assert the upsert's **writable set**, not only the post-condition, so widening fails CI | Dev | Story 1.8, re-verified each Epic 3 story |
| TECH-003 | TECH | Session-level advisory lock taken on a pooled connection is released on return to pool; two writers run undetected | 2 | 3 | 6 | Hold the lock on a dedicated pool-excluded connection; test after pooled work has occurred | Dev | Story 1.3 |
| DATA-002 | DATA | Idempotency records reaped before queue/checkpoint replay, so replayed work applies effects twice | 2 | 3 | 6 | Bind a provisional retention figure (CL-5); assert the ordering property, not a literal duration | Architect + Dev | Before Story 1.9 |
| DATA-003 | DATA | Source identity silently synthesised from name/URL when the stable ID is missing or untrustworthy | 2 | 3 | 6 | Negative tests asserting **absence** of a product row, plus the intra-snapshot collision case | Dev | Story 1.5 |
| DATA-004 | DATA | Ingest treats a filtered selection as a full sync and deactivates or deletes unobserved products | 2 | 3 | 6 | Seed N, ingest a filter of 1, assert the other N−1 rows unchanged including enrichment state | Dev | Story 1.6 |

### Medium-Priority Risks (Score 4 — MONITOR)

| Risk ID | Category | Description | P | I | Score | Mitigation | Owner |
| --- | --- | --- | :-: | :-: | :-: | --- | --- |
| SEC-001 | SEC | `agentic_cataloger_app` over-granted — can `CREATE DATABASE`, run DDL, or reach `agentic_cataloger_phoenix` | 2 | 2 | 4 | Two negative integration tests named in the GATE-02 checklist, plus vendor-schema DDL denial | Dev |
| OPS-001 | OPS | One-shot bootstrap not idempotent on re-run; second `up` half-applies schema state | 2 | 2 | 4 | Run bootstrap twice in CI and assert the second run is a clean no-op | Dev |
| DATA-005 | DATA | Snapshot immutability enforced only in the command handler, bypassable by any adapter reaching the repository | 2 | 2 | 4 | Enforce and assert at the database level, not just the application layer | Dev |
| DATA-006 | DATA | Manifest-replay "equivalence" undefined against generated UUIDv7 identities and timestamps — assertion unwritable as stated | 2 | 2 | 4 | Resolve CL-4: define a comparison excluding generated identity and time fields | Architect |
| DATA-007 | DATA | Money precision lost — float arithmetic or float JSON encoding on `NUMERIC(24,12)` amounts | 2 | 2 | 4 | Round-trip precision test plus a serialisation contract test; escalates to critical in Epic 3 where normalization arithmetic lands | Dev |
| PERF-001 | PERF | No ingest latency or throughput threshold exists, so AD-4's "measured too slow" deferral trigger can never fire objectively | 2 | 2 | 4 | Record a non-gating baseline (X-INT-001) so a threshold can be set from data; raise CL-3 | TEA |
| TECH-004 | TECH | Hexagonal dependency direction (AD-10) erodes — a framework import lands in a domain package with nothing detecting it | 2 | 2 | 4 | Automated import-boundary check in CI | Dev |

### Low-Priority Risks (Score 1–3 — DOCUMENT)

| Risk ID | Category | Description | P | I | Score | Action |
| --- | --- | --- | :-: | :-: | :-: | --- |
| OPS-002 | OPS | Root compose leaks a legacy reference, or the `3020+n` port map drifts | 1 | 3 | 3 | Monitor — static compose parse in CI |
| OPS-003 | OPS | Phoenix 30-day retention or telemetry-disable setting silently reverts on image upgrade | 2 | 1 | 2 | Monitor — settings assertion after bootstrap |

### Residual Risk After Mitigation

Residual risk is what remains once every mitigation above is complete and green. It is not zero,
and the following is what this plan knowingly accepts:

| Area | Residual exposure | Why accepted |
| --- | --- | --- |
| Concurrency | Multi-writer races, crash-window behaviour, taxonomy topology CAS, lease/fencing correctness are **entirely untested** | AD-16 makes single-writer a mechanically enforced premise and AD-31 removes these suites from MVP. Story 1.3 tests the guard instead of the machinery. Introducing a second concurrent writer invalidates this plan. |
| Performance | No latency or throughput assurance whatsoever | No threshold exists (CL-3). X-INT-001 records a baseline but gates nothing. First real scale signal will come from Epic 2 ingest volume. |
| Security | No authN/authZ, no threat model, no secrets/redaction verification | Deferred to a security initiative; AD-32 prohibits public exposure until then. GATE-02 covers only the database privilege boundary. |
| Data recovery | No backup, restore, or RPO/RTO assurance | AD-15 makes recovery equal re-import, proved by 1.11-E2E-002. Holds only while all state is reproducible from the manifest — the first non-reproducible data invalidates it. |
| Enrichment boundary | DATA-001 is contained, not eliminated | The writable-set assertion catches widening at CI time, but the boundary is a convention enforced by tests rather than a database-level grant. Re-verification at each Epic 3 story is the standing control. |
| Source adapter breadth | Only the current CSV adapter shape is exercised | Snapshot completeness semantics are deferred until a second adapter or a genuinely delisting source arrives (AD-6). |

### Risk Category Legend

- **TECH**: Technical/Architecture (flaws, integration, scalability)
- **SEC**: Security (access controls, auth, data exposure)
- **PERF**: Performance (SLA violations, degradation, resource limits)
- **DATA**: Data Integrity (loss, corruption, inconsistency)
- **BUS**: Business Impact (UX harm, logic errors, revenue) — none identified in Epic 1
- **OPS**: Operations (deployment, config, monitoring)

---

## NFR Planning

**Purpose:** Capture epic-specific NFR thresholds, planned validation, and the evidence a later
`nfr-assess` run should consume. This is planning only — no PASS/CONCERNS/FAIL is asserted here.

| NFR Category | Requirement / Threshold | Risk Link | Planned Validation | Evidence Needed |
| --- | --- | --- | --- | --- |
| Reliability | ≤5 retries, exponential full jitter, cap 15 min | — | INT against disposable PG | pytest report + captured attempt timings |
| Reliability | Work states exactly `pending`/`running`/`retry_wait`/`completed`/`failed`/`cancelled` | — | UNIT enum contract + INT transition test | pytest report |
| Reliability | Deterministic `invalid`/`defer` never infrastructure-retries | — | INT negative test | pytest report |
| Reliability | Durable dispatch survives restart (GATE-03 P1–P8) | TECH-001 | INT + PROC | GATE-03 suite green on Linux CI + PG18 |
| Reliability | Second worker fails at boot with reserved non-zero code | TECH-003 | PROC | Process exit codes + worker logs |
| Security | `agentic_cataloger_app` cannot `CREATE DATABASE`; cannot write `agentic_cataloger_phoenix` | SEC-001 | INT negative tests | pytest report; GATE-02 checklist ticked |
| Security | App role has USE+EXECUTE but no DDL on `pgqueuer`/`langgraph` schemas | SEC-001 | INT | pytest report |
| Security | Elevated migrate credentials absent from `api`/`worker` environments | SEC-001 | INT | Environment assertion output |
| Performance | **UNKNOWN** — no ingest latency or throughput budget exists | PERF-001 | INT benchmark, non-gating | Recorded baseline number in CI artifact |
| Scalability | Exactly one worker; more is a boot failure (deliberate ceiling, not a gap) | TECH-003 | PROC | Single-writer evidence above |
| Maintainability | Domain packages import no FastAPI/Pydantic/SQLAlchemy/LangGraph/LangChain/PgQueuer/Phoenix/OTel | TECH-004 | Static import-boundary check in CI | CI job result |
| Maintainability | ≥80% line coverage on `src/agentic_cataloger/` | TECH-002 | `pytest-cov` | Coverage report |
| Observability | W3C trace context propagates onto job spans | TECH-001 | INT via Phoenix | Phoenix span inspection (GATE-03 P7) |
| Observability | Phoenix raw-trace retention 30 days; product telemetry disabled | OPS-003 | INT | Settings assertion output |
| Recoverability | Recovery is manifest re-import; no restore drill required | DATA-006 | E2E | Replay run logs + state comparison |
| Compliance | Not in scope — no PII or regulated data | — | — | — |

**Unknown thresholds — do not invent values. Tracked as clarification items:**

| ID | Question | Blocks |
| --- | --- | --- |
| **CL-1** | Which exit code signals the single-writer conflict? "Distinct non-zero" is unspecified | 1.3-PROC-002 |
| **CL-2** | Which variables are secrets, and what is the log-redaction rule? | Security evidence source |
| **CL-3** | What ingest throughput/latency is acceptable, at what catalog size? | PERF-001; AD-4 deferral trigger |
| **CL-4** | What does "equivalent" mean for two manifest replays, given UUIDv7 IDs and timestamps differ by construction? | 1.11-E2E-003 |
| **CL-5** | Provisional queue/checkpoint retention, so idempotency lifetime has a referent | 1.9-INT-005 |

---

## Entry Criteria

- [x] **TECH-002 closed** — dev dependencies, `conftest.py`, disposable PostgreSQL 18.4 fixture,
      process-spawn/kill harness, and `pytest-cov` present; coverage reports produced in CI
- [ ] Linux CI runner with Docker available for disposable PostgreSQL 18.4
- [x] GATE-01 port map and repository layout applied (Story 1.1 merged)
- [x] GATE-02 privilege manifest reflected in `docker/postgres/init/*.sql`
- [ ] CL-1 resolved (blocks 1.3-PROC-002)
- [ ] CL-4 and CL-5 resolved, or their dependent ACs formally deferred
- [ ] Catalog CSV fixtures available under `data/` for snapshot and manifest replay tests
- [ ] **TECH-001 resequenced** — Story 1.2a ready-for-dev; GATE-03 blocks 1.4+ (proof still pending)

## Exit Criteria

- [ ] All 51 P0 tests passing — no exceptions, no waivers
- [ ] P1 pass rate ≥ 95%, remaining failures triaged
- [ ] **No open P0 or P1 severity bugs.** Any defect in a DATA-category invariant is P0 by
      default regardless of observed symptom severity — these failures are silent by nature, so
      symptom severity understates them
- [ ] **TECH-001 closed** — Story 1.2a P1–P8 green (TECH-002 already closed)
- [ ] All five score-6 risks have a green owning test
- [ ] AD-31 mandatory D6 regression (1.8-INT-001) green
- [ ] GATE-03 P1–P8 green on Linux CI against PostgreSQL 18
- [ ] GATE-01 and GATE-02 story checklists fully ticked
- [ ] ≥80% line coverage on `src/agentic_cataloger/`
- [ ] Every in-scope NFR category has a named evidence artifact
- [ ] CL-1 through CL-5 resolved or explicitly accepted as deferred

## Project Team

**N/A** — single-operator project (AD-16 assumes one operator for MVP). No responsibility
mapping is needed; Dev and TEA ownership is recorded per-risk in the tables above.

---

## Test Coverage Plan

> **P0–P3 express priority and risk, not execution timing.** A P0 scenario is one that blocks
> core functionality at high risk with no workaround — it says nothing about when the test runs.
> Timing is decided separately in [Execution Strategy](#execution-strategy) on the basis of
> infrastructure overhead. Several P0 scenarios here run nightly because they spawn and kill
> processes; several P2 scenarios run on every commit because they are static assertions.

Level vocabulary, mapped onto this backend-only epic per AD-31 and the structural seed:

| Level | Meaning here | Runs against |
| --- | --- | --- |
| **UNIT** | Pure domain and static/architecture assertions | No framework, no database |
| **INT** | Persistence, UoW, queue, checkpoint, migration adapters | Disposable PostgreSQL 18.4 |
| **CONTRACT** | `contracts/v1` schemas, error codes, wire encoding | No database |
| **PROC** | Real process spawn/kill — role commands, advisory lock | Compose or spawned processes |
| **E2E** | Full manifest replay through the importer | Full stack |

`PROC` exists because Story 1.3 AC 2 ("exits with a distinct non-zero status code") and GATE-03
P4 ("SIGKILL mid-handler") are assertions about process exit and process death. They cannot be
made in-process, and folding them into INT would silently weaken both.

### P0 (Critical) — 51 scenarios

**Criteria**: Blocks core functionality + high risk + no workaround

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | :-: | --- | --- |
| 1.2 — Role commands start independently | PROC | — | 3 | DEV | `api`, `worker`, `migrate` from one image |
| 1.2 — Bootstrap order and idempotence | INT | OPS-001 | 2 | DEV | Second run must be a clean no-op |
| 1.2 — Least-privilege runtime role | INT | SEC-001 | 2 | DEV | GATE-02 named tests; both are negative |
| **1.2a — GATE-03 completion reliance (spike)** | INT + PROC | TECH-001 | 8 | DEV | P1–P8 before Story 1.4; pulled forward from 1.10 |
| 1.3 — Single-writer advisory lock | PROC | TECH-003 | 4 | DEV | Incl. lock survival after pooled DB work |
| 1.4 — Immutable snapshot registration | INT | DATA-005 | 3 | DEV | Immutability asserted at DB level |
| 1.5 — Durable source identity | INT + UNIT | DATA-003 | 6 | DEV | Incl. absence assertions and intra-snapshot collision |
| 1.6 — One selection primitive | INT | DATA-004 | 5 | DEV | Incl. unobserved-products-untouched proof |
| 1.7 — Revisioned shelf prices | INT + UNIT + CONTRACT | DATA-007 | 4 | DEV | Precision round-trip + string-encoded JSON decimal |
| 1.8 — D6 non-wipe guarantee | INT + UNIT | DATA-001 | 5 | DEV | AD-31 mandatory; incl. writable-set assertion |
| 1.9 — Command idempotency | INT + UNIT | DATA-002 | 5 | DEV | Incl. same-UoW commit of record and effects |
| 1.10 — GATE-03 regression + central retry | INT + PROC | TECH-001 | 2+reuse | DEV | Retry policy ACs; P1–P8 reused from 1.2a |
| 1.11 — Manifest rebuild | E2E + INT | — | 2 | DEV | Rebuild works; no legacy AI-derived state carried |

**Total P0**: 51 tests, ~60–90 hours

### P1 (High) — 27 scenarios

**Criteria**: Critical paths + medium/high risk

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | :-: | --- | --- |
| 1.1 — Toolchain lock resolution | INT | — | 1 | DEV | CPython 3.14.6 / uv 0.12.1; no Server-CLI extras, no Pydantic V1 |
| 1.2 — Ports, volumes, Phoenix wiring | INT | OPS-002 | 3 | DEV | 3021 Postgres, 3022 Phoenix, 3020 api |
| 1.2 — Vendor schema and credential scoping | INT | SEC-001 | 2 | DEV | No DDL on `pgqueuer`/`langgraph`; migrate creds absent |
| 1.2 — Compose carries zero legacy references | UNIT | OPS-002 | 1 | DEV | Static parse |
| 1.3 — Deploy topology and per-database scoping | PROC + INT | TECH-003 | 2 | DEV | Two-replica case; bakeoff isolation case |
| 1.4 — UoW boundary and UTC interpretation | INT + UNIT | TECH-004 | 3 | DEV | Incl. AD-14 no-direct-repository check |
| 1.5 — Application identity and policy versioning | INT + UNIT | DATA-003 | 3 | DEV | UUIDv7 distinct from source identity |
| 1.6 — No mode-specific branch | UNIT | — | 1 | DEV | Static check across ingest path |
| 1.7 — Enum, currency, and amount validation | UNIT | DATA-007 | 2 | DEV | ISO 4217; positive Decimal |
| 1.8 — Minimal enrichment table scope | INT | — | 1 | DEV | Creates the boundary and nothing more |
| 1.9 — Idempotency outlives retention | INT | DATA-002 | 1 | DEV | Blocked on CL-5; assert ordering property |
| 1.10 — Work-state enum and no producer bridge | UNIT | — | 2 | DEV | Static + enum contract |
| 1.11 — Recovery, replay equivalence, legacy read-only | E2E + INT + UNIT | DATA-006 | 4 | DEV | Equivalence blocked on CL-4 |
| X — AD-10 import boundary | UNIT | TECH-004 | 1 | DEV | CI-enforced |

**Total P1**: 27 tests, ~25–40 hours

### P2 (Medium) — 8 scenarios

**Criteria**: Secondary flows + low/medium risk

| Requirement | Test Level | Risk Link | Test Count | Owner | Notes |
| --- | --- | --- | :-: | --- | --- |
| 1.1 — Structural seed and relocation layout | UNIT | OPS-002 | 5 | DEV | 3 already exist; +2 for "no domain logic" and relocation layout |
| 1.2 — Phoenix retention and telemetry | INT | OPS-003 | 1 | DEV | 30 days; telemetry off |
| 1.2 — No Redis or external workflow runtime | UNIT | — | 1 | DEV | Dependency and service graph |
| 1.2 — Devcontainer/CI parity | UNIT | — | 1 | DEV | Same role commands, same PG image |

**Total P2**: 8 tests, ~6–12 hours

### P3 (Low) — 1 scenario

**Criteria**: Benchmarks and exploratory

| Requirement | Test Level | Test Count | Owner | Notes |
| --- | --- | :-: | --- | --- |
| X — Ingest throughput/latency baseline | INT | 1 | TEA | Non-gating; records a number so CL-3 can be answered from data |

**Total P3**: 1 test, ~3–6 hours

> The full scenario-by-scenario matrix with individual IDs (`1.3-PROC-003`, `1.8-INT-001`, …)
> lives in §4.1 of `test-design-progress.md`. The tables above aggregate it by requirement so
> this document stays readable; the two are consistent at 87 scenarios.

---

## Execution Strategy

**Philosophy: run everything in PRs if it fits in 15 minutes; defer only what is expensive or
long-running.** Priority does not decide timing — infrastructure overhead does.

| Stage | Contents | Count | Budget |
| --- | --- | :-: | --- |
| **PR** | All UNIT and CONTRACT scenarios, plus every INT scenario that does not need a full compose stack | 65 | < 15 min |
| **Nightly** | All 9 PROC scenarios; full compose bootstrap incl. idempotent re-run (2 INT); complete GATE-03 P1–P8 (7 INT + 1 PROC, already counted); manifest rebuild and recovery-by-replay (2 E2E) | 20 | ~30–45 min |
| **Weekly** | Double replay at full manifest size (1.11-E2E-003); ingest throughput/latency baseline (X-INT-001) | 2 | unbounded |

Nightly deferral is justified by cost and flake risk, not by importance — most of that set is
P0. Process spawn, SIGKILL recovery, and container bootstrap are the slowest and least stable
things in this epic, and holding every PR behind them would make the loop unusable.

**Two standing exceptions, both story-scoped:**

- **GATE-03 P1–P8 runs in PR for Story 1.2a**, then moves to nightly (and remains PR-blocking
  regression for Story 1.10). It is the spike's acceptance gate and must not be soft-skipped.
- **Story 1.3's PROC scenarios run in its own PR.** Its acceptance criteria *are* process
  assertions — there is nothing left to verify if they are deferred.

Playwright parallelisation guidance does not apply: Epic 1 has no browser surface, and the
suite is pytest against PostgreSQL. PR-stage throughput depends instead on database
provisioning strategy — see the contingency under [Risks to Plan](#risks-to-plan).

---

## Resource Estimates

### Test Development Effort

Ranges rather than the template's fixed per-test multipliers. A single INT scenario against a
real PostgreSQL — fixture, migration, seed, teardown — costs several times what a static UNIT
assertion costs, and a flat 2.0 h/test would misstate both ends of this epic.

| Priority | Count | Hours/Test | Total Hours | Notes |
| --- | :-: | --- | --- | --- |
| **Foundation** | — | — | **done** | TECH-002 closed in Story 1.2 |
| P0 | 51 | 1.2–1.8 | 60–90 | INT-heavy; GATE-03 alone is ~20–30 h of this |
| P1 | 27 | 0.9–1.5 | 25–40 | Standard coverage |
| P2 | 8 | 0.7–1.5 | 6–12 | Mostly static assertions |
| P3 | 1 | 3.0–6.0 | 3–6 | Benchmark harness costs more than the assertion |
| **Total** | **87** | **—** | **106–168** | **~3–5 weeks** |

Roughly 3–5 weeks of dedicated test effort for one engineer, interleaved across the eleven
stories rather than batched at the end.

**Two figures worth reading together:** the foundation bucket is 12–20 h and blocks all 106–168 h
behind it. GATE-03 is ~20–30 h and is entirely at risk if TECH-001 materialises after Stories
1.4–1.9 are built on it. Both arguments point the same way — front-load.

### Prerequisites

**Test Data**

- Catalog snapshot factory — source records with controllable `(namespace, product_id, variant_id)`,
  including missing-ID and colliding-ID variants for DATA-003
- Product fixture supporting seed → mutate → re-import cycles for the D6 regression
- Enrichment-owned attribute seeder, needed by 1.8-INT-001 and 1.6-INT-004
- Immutable source manifest fixture for Story 1.11 replay
- Decimal edge-case set at `NUMERIC(24,12)` bounds for DATA-007

**Tooling** — all currently missing; this list *is* TECH-002

- Async test driver (`pytest-asyncio` or `anyio`) — every repository and UoW is async
- Disposable PostgreSQL 18.4 (`testcontainers[postgres]` or `pytest-postgresql`) — required by AD-31
- Process-spawn/kill harness — Story 1.3 and GATE-03 P4 cannot run in-process
- `pytest-cov` — no coverage evidence is producible without it
- Import-boundary linter for AD-10 (TECH-004)

**Environment**

- Linux CI with Docker — AD-27 names Linux CI against PostgreSQL 18.4 as compatibility authority
- Phoenix `arizephoenix/phoenix:version-19.11.1` reachable for GATE-03 P7 trace assertions
- Ports 3020–3023 free; legacy 3010/5532 must remain untouched

---

## Quality Gate Criteria

### Pass/Fail Thresholds

- **P0 pass rate**: 100% — no exceptions, no waivers
- **P1 pass rate**: ≥95% — waivers required for failures
- **P2/P3 pass rate**: ≥90% — informational
- **High-risk mitigations**: 100% complete or approved waivers

### Coverage Targets

- **Line coverage on `src/agentic_cataloger/`**: ≥80%
- **Security scenarios (SEC-001)**: 100%
- **Data-integrity scenarios (DATA-001…007)**: 100% — this is the epic's thesis
- **Edge cases**: ≥50%

### Non-Negotiable Requirements

- [ ] All 51 P0 tests pass
- [ ] No score-9 risk open — TECH-002 closed; TECH-001 closed when Story 1.2a is green
- [ ] No score-6 risk unmitigated
- [ ] AD-31 mandatory D6 regression (1.8-INT-001) green
- [ ] GATE-03 P1–P8 green on Linux CI against PostgreSQL 18
- [ ] SEC category passes 100%
- [ ] PERF: baseline recorded — **no threshold to meet**, pending CL-3
- [ ] Planned NFR evidence exists, or `nfr-assess` has documented CONCERNS/waivers

### Gate Decision Rule

Per `risk-governance.md`: any unresolved score-9 risk or any P0 coverage gap → **FAIL**.
Score 6–8 risks with a named owner and mitigation plan → **CONCERNS**. Otherwise → **PASS**.

**Epic 1 cannot currently reach PASS** — TECH-002 is closed; TECH-001 is resequenced but the
P1–P8 proof is not yet green (Story 1.2a `ready-for-dev`). Until that suite passes (or queue
selection is explicitly reopened), the risk-governance rule still fails on the open score-9.

---

## Mitigation Plans

### TECH-001: GATE-03 PgQueuer completion reliance may not hold (Score 9)

**Mitigation Strategy:** Resequence rather than merely test. Story **1.2a**
(`1-2a-prove-pgqueuer-completion-reliance.md`) builds
`backend/tests/integration/test_pgqueuer_reliance.py` covering P1–P8 as a spike immediately
after Story 1.2, before Stories 1.4–1.9 accumulate code that assumes PgQueuer. The proof costs
the same either way; the cost of *failure* drops by an epic's worth of rework. Probability is
Likely because P6 (cancellation at a safe boundary) and P7 (W3C trace context on job spans) are
not first-class PgQueuer features — both need custom envelope work that must then survive P4's
SIGKILL recovery.
**Owner:** Dev + TEA
**Timeline:** Story 1.2a — before Story 1.4 starts
**Status:** Resequenced — story `ready-for-dev`; proof not yet green
**Verification:** All eight scenarios green on Linux CI against PostgreSQL 18; GATE-03 checklist
ticked. If any scenario cannot be satisfied, escalate to the Architect — AD-22 queue selection
reopens, and that decision must precede further dispatch-backed work.

### TECH-002: Test toolchain cannot express Epic 1's mandatory tests (Score 9)

**Mitigation Strategy:** Add to the `dev` dependency group an async driver, disposable
PostgreSQL 18.4 provisioning, and `pytest-cov`; add `backend/tests/conftest.py` exposing a
per-test disposable-database fixture; add a process-spawn/kill harness for Story 1.3 and
GATE-03 P4. Wire coverage into Linux CI.
**Owner:** Dev
**Timeline:** Before Story 1.2 merges
**Status:** **CLOSED** — `pytest-asyncio`, `testcontainers[postgres]`, `pytest-cov`,
`conftest.py` (`spawn_role` / `terminate_role` / `kill_role`), and CI coverage reports are on
disk as of Story 1.2.
**Verification:** Representative INT and PROC tests green; coverage XML/term reports produced
in `.github/workflows/backend.yml`.

### DATA-001: D6 enrichment wipe recurrence (Score 6)

**Mitigation Strategy:** The AD-31 mandatory regression test, written to fail on **widening**
rather than only on wiping — assert the upsert's declared writable set, not just the
post-condition. Pair it with the TECH-004 import-boundary check so that a new enrichment column
mapping appearing in the catalog repository fails CI on the commit that introduces it.
**Owner:** Dev
**Timeline:** Story 1.8, re-verified at every Epic 3 story
**Status:** Planned
**Verification:** 1.8-INT-001 and 1.8-UNIT-001/002 green; a deliberate widening of the upsert
in a scratch branch must turn CI red.

### TECH-003: Advisory lock released by connection pooling (Score 6)

**Mitigation Strategy:** Acquire the lock on a dedicated, pool-excluded connection held for
process lifetime. The stack pins `psycopg-pool==3.3.1`, and a session-level `pg_advisory_lock`
taken on a pooled connection is released the moment that connection returns to the pool, with
nothing surfacing the failure. AD-16 rests four other invariants (AD-3, AD-17, AD-21, AD-22
concurrency machinery) on this lock holding.
**Owner:** Dev
**Timeline:** Story 1.3
**Status:** Planned
**Verification:** 1.3-PROC-003 — worker 1 performs pooled database work *first*, then worker 2
must still fail to boot. A test that checks only at startup passes even when the bug is present.

### DATA-002: Idempotency records expire before replay (Score 6)

**Mitigation Strategy:** Story 1.9's AC asserts record lifetime "exceeds queue and checkpoint
retention", but retention is an open item in the deferred register — the AC is currently
untestable because there is no number to exceed. Bind a provisional retention figure (CL-5),
then assert the ordering property (idempotency TTL > queue TTL) rather than a literal duration,
so the test survives later retuning.
**Owner:** Architect (threshold) + Dev (test)
**Timeline:** Before Story 1.9
**Status:** Blocked on CL-5
**Verification:** 1.9-INT-005 green with a referent recorded in the architecture.

### DATA-003: Source identity silently synthesised (Score 6)

**Mitigation Strategy:** Negative tests are the primary control. A record with a missing or
untrustworthy stable ID must defer or fail *and* leave no catalog product row — assert the
absence, not merely the raised error. Include the intra-snapshot collision case, which is the
one most likely to be silently resolved by an upsert.
**Owner:** Dev
**Timeline:** Story 1.5
**Status:** Planned
**Verification:** 1.5-UNIT-001, 1.5-INT-004, 1.5-INT-005 green.

### DATA-004: Filtered selection treated as a full sync (Score 6)

**Mitigation Strategy:** Probability is elevated by precedent — the legacy importer operated on
whole-file semantics, and "reconcile everything not seen" is the default mental model for
importers. MVP explicitly forbids it (AD-6: no completeness assertion, no absence-driven
deactivation). The canonical test seeds N products, ingests a filter matching one, and asserts
the remaining N−1 rows are unchanged — including their enrichment state, which also exercises
DATA-001.
**Owner:** Dev
**Timeline:** Story 1.6
**Status:** Planned
**Verification:** 1.6-INT-004 and 1.6-INT-005 green.

---

## Assumptions and Dependencies

### Assumptions

1. Epic 1 is the correct target — it is the only epic at `in-progress` in `sprint-status.yaml`;
   Epics 2–6 are all `backlog`.
2. Story 1.1 lands as reviewed; its three existing structural tests remain valid and are counted
   as already-delivered coverage.
3. Legacy TypeScript tests contribute nothing transferable — different language, different
   schema, and AD-15 forbids carrying legacy semantics across. No reuse credit is taken.
4. Linux CI with Docker is available; AD-27 names it the compatibility authority.
5. `uuid.uuid7()` from the CPython 3.14 standard library satisfies AD-26, so UUIDv7 generation
   needs no third-party dependency and carries no additional risk.
6. Single-operator, single-worker runtime holds throughout Epic 1 (AD-16). If a second concurrent
   writer is ever introduced, this plan is invalidated — the deferred concurrency test suites
   return with it.

### Dependencies

1. **TECH-002 closure** — **done** (Story 1.2). Hard blocker on all other testing is lifted.
2. **TECH-001 / Story 1.2a** — GATE-03 P1–P8 spike; required before Story 1.4.
3. **CL-1 (single-writer exit code)** — required before Story 1.3.
4. **CL-5 (queue/checkpoint retention)** — required before Story 1.9.
5. **CL-4 (replay equivalence definition)** — required before Story 1.11.
6. **GATE-02 init scripts** — required before the SEC-001 negative tests can run.
7. **Phoenix instance reachable** — required for GATE-03 P7.

### Risks to Plan

- **Risk**: GATE-03 fails and AD-22 queue selection reopens.
  - **Impact**: ~20–30 h of GATE-03 work is lost; **Stories 1.4–1.9 have not yet assumed
    PgQueuer** because the spike runs as Story 1.2a.
  - **Contingency**: Story 1.2a is the scheduled spike. Escalate to Architect before 1.4.

- **Risk**: Disposable-PostgreSQL provisioning proves too slow to keep PR under 15 minutes.
  - **Impact**: The PR/nightly split degrades; INT feedback moves to nightly and defect
    detection slows across every story.
  - **Contingency**: Share one container across the session with per-test schema or database
    isolation instead of per-test containers; keep teardown assertions unchanged.

- **Risk**: CL-1 through CL-5 remain unanswered.
  - **Impact**: Five acceptance criteria stay unverifiable and their stories cannot exit.
  - **Contingency**: Formally defer the affected ACs with the Architect rather than inventing
    thresholds. Guessing values here would produce tests that pass while proving nothing.

---

## Follow-on Workflows (Manual)

- Run `*atdd` to generate failing P0 tests — separate workflow, not auto-run from here.
- Run `*automate` for broader coverage once implementation exists.
- Run `*trace` to build the traceability matrix and the formal gate decision.
- Run `*nfr-assess` once implementation evidence exists — this document plans NFR validation but
  asserts no PASS/CONCERNS/FAIL.

---

## Approval

**Test Design Approved By:**

- [ ] Product Manager: ______________________ Date: __________
- [ ] Tech Lead: ______________________ Date: __________
- [ ] QA Lead: ______________________ Date: __________

**Comments:**

---

## Interworking & Regression

| Service/Component | Impact | Regression Scope |
| --- | --- | --- |
| **Legacy NestJS API (`legacy/backend`, port 3010)** | Must remain reachable and **read-only** throughout the rebuild (AD-15) | 1.11-INT-002; no new-stack component may write to it. No legacy test execution required (GATE-01) |
| **Legacy PostgreSQL (port 5532)** | Must stay fully separate from the new stack — no shared volume, `depends_on`, or connection string (GATE-02) | 1.2-UNIT-001 static compose parse; OPS-002 |
| **Frontend (`frontend/`, port 3023)** | Continues consuming the legacy API; unaffected by Epic 1 | No frontend regression suite in this epic; revisit at Epic 5 |
| **Phoenix (`agentic_cataloger_phoenix`, port 3022)** | New dependency; owns its own database, no cross-DB access from the app | 1.2-INT-004 (app cannot write it), 1.2-INT-010 (retention/telemetry), GATE-03 P7 |
| **PgQueuer (`pgqueuer` schema)** | Vendor-owned tables inside the application database | 1.2-INT-008 (no DDL from app role); full GATE-03 suite |
| **LangGraph checkpointer (`langgraph` schema)** | Vendor-owned tables inside the application database | 1.2-INT-008; GATE-03 P5 resume |
| **`data/` catalog CSVs** | Source input for snapshot registration and manifest replay | Fixtures must not mutate `data/`; replay tests read-only |

---

## Appendix

### Knowledge Base References

- `risk-governance.md` — risk classification and gate decision rules
- `probability-impact.md` — 1–9 scoring methodology and action thresholds
- `test-levels-framework.md` — test level selection
- `test-priorities-matrix.md` — P0–P3 prioritisation
- `nfr-criteria.md` — NFR category definitions

### Related Documents

- Epic: `_bmad-output/planning-artifacts/epics.md` (Epic 1, lines 336–711)
- Architecture: `_bmad-output/planning-artifacts/architecture/architecture-agentic-cataloger-2026-07-31/ARCHITECTURE-SPINE.md`
- Spec: `_bmad-output/specs/spec-2026-agent-workflow/SPEC.md`
- Gates: `_bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md`,
  `GATE-02-db-privileges.md`, `GATE-03-pgqueuer-proof.md`
- Implementation readiness: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-08-01.md`
- Working notes and full scenario matrix: `_bmad-output/test-artifacts/test-design-progress.md`

---

**Generated by**: BMad TEA Agent — Test Architect Module
**Workflow**: `bmad-testarch-test-design`
**Version**: 4.0 (BMad v6)
