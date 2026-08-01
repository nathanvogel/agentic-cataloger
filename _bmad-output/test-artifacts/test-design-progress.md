---
workflowStatus: 'completed'
totalSteps: 5
stepsCompleted: ['step-01-detect-mode', 'step-02-load-context', 'step-03-risk-and-testability', 'step-04-coverage-plan', 'step-05-generate-output']
lastStep: 'step-05-generate-output'
nextStep: ''
lastSaved: '2026-08-01'
inputDocuments:
  - _bmad-output/planning-artifacts/epics.md
  - _bmad-output/planning-artifacts/architecture/architecture-pricecomp-2026-07-31/ARCHITECTURE-SPINE.md
  - _bmad-output/specs/spec-2026-agent-workflow/SPEC.md
  - _bmad-output/implementation-artifacts/sprint-status.yaml
  - _bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md
  - _bmad-output/implementation-artifacts/gates/GATE-02-db-privileges.md
  - _bmad-output/implementation-artifacts/gates/GATE-03-pgqueuer-proof.md
  - backend/pyproject.toml
  - backend/tests/domain/test_structural_seed.py
  - _bmad/tea/config.yaml
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/risk-governance.md
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/probability-impact.md
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/test-levels-framework.md
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/test-priorities-matrix.md
  - .claude/skills/bmad-testarch-test-design/resources/knowledge/nfr-criteria.md
---

# Test Design Progress — pricecomp

## Step 01: Mode Detection & Prerequisites

**Mode selected:** Epic-Level Mode (Phase 4)

**Detection path:** Rule B (file-based detection). No explicit user intent was
supplied with the skill invocation. `_bmad-output/implementation-artifacts/sprint-status.yaml`
exists → Epic-Level Mode.

**Target epic:** Epic 1 — the only epic with status `in-progress`. Story
`1-1-relocate-legacy-typescript-and-seed-the-python-monolith` is at `review`;
stories 1-2 through 1-11 are at `backlog`. All other epics (2–6) are `backlog`.

**Planned output:** `_bmad-output/test-artifacts/test-design-epic-1.md`

### Prerequisite Check (Epic-Level)

| Requirement | Source | Status |
| --- | --- | --- |
| Epic/story requirements with acceptance criteria | `_bmad-output/planning-artifacts/epics.md` (2417 lines) | Available |
| Architecture context | `_bmad-output/planning-artifacts/architecture/architecture-pricecomp-2026-07-31/ARCHITECTURE-SPINE.md` (422 lines) | Available |
| Spec kernel | `_bmad-output/specs/spec-2026-agent-workflow/SPEC.md` (116 lines) | Available |
| Implementation gates | `_bmad-output/implementation-artifacts/gates/GATE-01..04` | Available |
| Sprint tracking | `_bmad-output/implementation-artifacts/sprint-status.yaml` | Available |

No HALT conditions triggered.

### Activation Notes

- Customization resolver (`_bmad/scripts/resolve_customization.py`) failed: requires
  Python 3.11+ (`tomllib`); system default is Python 3.9.6. Workflow block resolved
  manually per SKILL.md fallback.
- No team override (`_bmad/custom/bmad-testarch-test-design.toml`) or user override
  (`.user.toml`) exists → base `customize.toml` defaults apply unchanged.
- `persistent_facts` glob `**/project-context.md` matched no files → no static facts loaded.
- `activation_steps_prepend`, `activation_steps_append`, `on_complete` are all empty.

---

## Step 02: Context & Knowledge Loading

### Config Flags Resolved

| Flag | Value | Effect on this run |
| --- | --- | --- |
| `tea_use_playwright_utils` | `true` | **Not applied** — Epic 1 is Python-backend only; Playwright Utils are TS/Playwright fixtures with no Epic 1 surface |
| `tea_use_pactjs_utils` | `false` | Pact.js fragments not loaded |
| `tea_pact_mcp` | `none` | `pact-mcp.md` not loaded |
| `tea_browser_automation` | `auto` | Browser exploration **skipped** — Epic 1 exposes no UI; fell back to code/doc analysis per the step's fallback clause |
| `test_stack_type` | `auto` | Auto-detected below |
| `risk_threshold` | `p1` | Governs coverage gating |

### Stack Detection

Auto-detection found both families → `fullstack` at repo level:

- **Backend:** `backend/pyproject.toml` (CPython 3.14.6, uv 0.12.1)
- **Frontend:** `frontend/package.json` (React Router + Vite)
- **Legacy (reference-only):** `legacy/backend/package.json`, `legacy/data-importer/package.json`

**Effective stack for Epic 1: `backend`.** Epic 1 delivers only the Python monolith, Compose
topology, and catalog ingest. The frontend is untouched until Epic 5. Knowledge loading
therefore used the backend/API profile, not the full UI+API profile.

### Artifacts Loaded

- Epic 1 in full — stories 1.1–1.11, `epics.md` lines 336–711 (FR1–FR7, FR49–FR52, FR55, FR56–FR58)
- `ARCHITECTURE-SPINE.md` — all 34 live ADs, stack pins, structural seed, deferred register
- GATE-01 (bootstrap/ports/layout), GATE-02 (db roles/privileges), GATE-03 (PgQueuer P1–P8)
- Current backend source and test tree

### Knowledge Fragments Loaded (Epic-Level Required)

| Fragment | Tier | Purpose |
| --- | --- | --- |
| `risk-governance.md` | core | Scoring matrix, gate decision rules (PASS/CONCERNS/FAIL/WAIVED) |
| `probability-impact.md` | core | 1–9 scale, DOCUMENT/MONITOR/MITIGATE/BLOCK thresholds |
| `test-levels-framework.md` | core | Unit vs integration vs E2E selection |
| `test-priorities-matrix.md` | core | P0–P3 criteria and coverage targets |
| `nfr-criteria.md` | extended | Loaded — Epic 1 carries reliability (AD-22 retry), security/privilege (GATE-02), and operational (AD-29 bootstrap) requirements |

### Existing Test Coverage Analysis

**Python (active tree) — near-zero:**

- `backend/tests/domain/test_structural_seed.py` is the only test: 3 structural assertions
  (packages import, `retrieval/` absent per retired AD-35, required dirs exist)
- `backend/tests/{integration,contract,evals}/` exist but are **empty** — no `__init__.py`, no cases
- No `conftest.py`, no fixtures, no factories anywhere in `backend/`

**Legacy TypeScript — 14 spec files**, reference-only. GATE-01 explicitly states no requirement
to pass legacy build or test. Treated as **non-transferable**: different language, different
schema, and AD-15 forbids carrying legacy AI-derived semantics across. No reuse credit taken.

### Testability Gap Found (pre-implementation blocker)

`backend/pyproject.toml` dev dependency group contains **only `pytest==9.1.1`**. Epic 1 as
specified cannot be tested with that alone. Missing, and needed before story 1.3 onward:

- **async test driver** — every repository/UoW is SQLAlchemy 2 async + Psycopg 3 (AD-23);
  stories 1.3, 1.9, 1.10 are inherently async. No `pytest-asyncio`/`anyio` present.
- **disposable PostgreSQL 18.4 provisioning** — AD-31 mandates adapter tests run against real
  disposable Postgres on Linux CI. No `testcontainers`/`pytest-postgresql` present.
- **process-level harness** — stories 1.3 (second worker exits non-zero) and GATE-03 P4
  (SIGKILL mid-handler) require spawning and killing real processes, not in-process calls.
- **coverage measurement** — no `pytest-cov`; no way to evidence coverage at the gate.

This is carried into Step 3 as a testability risk and into the plan's entry criteria.

### Confirmation

All Epic-Level prerequisites were satisfiable from repository artifacts. Nothing was missing
that required asking Nathan to supply it.

---

## Step 03: Risk Assessment & NFR Planning

### 3.1 Testability Review — Not Applicable

Section 1 of this step is gated to System-Level Mode. This run is Epic-Level, so no
architecture testability review or ASR classification is produced here. The architecture
was already assessed in `implementation-readiness-report-2026-08-01.md`.

### 3.2 Risk Register

Scored per `probability-impact.md`: Probability 1–3 × Impact 1–3 → 1–9.
Thresholds: 1–3 DOCUMENT · 4–5 MONITOR · 6–8 MITIGATE · 9 BLOCK.

| ID | Cat | Risk | P | I | Score | Action |
| --- | --- | --- | :-: | :-: | :-: | --- |
| TECH-001 | TECH | GATE-03 P1–P8 cannot all be satisfied by PgQueuer 1.3.2, reopening queue selection after dependent code exists | 3 | 3 | **9** | **BLOCK** |
| TECH-002 | TECH | Test toolchain cannot express Epic 1's mandatory tests (no async driver, no disposable Postgres, no process harness) | 3 | 3 | **9** | **BLOCK** |
| DATA-001 | DATA | D6 recurrence — catalog upsert widens over Epics 3+ and silently overwrites enrichment-owned values | 2 | 3 | 6 | MITIGATE |
| TECH-003 | TECH | Session-level advisory lock taken on a pooled connection is released on return to pool; two writers run undetected | 2 | 3 | 6 | MITIGATE |
| DATA-002 | DATA | Idempotency records are reaped before queue/checkpoint replay, so replayed work applies business effects twice | 2 | 3 | 6 | MITIGATE |
| DATA-003 | DATA | Source identity silently synthesised from name/URL when the stable ID is missing or untrustworthy | 2 | 3 | 6 | MITIGATE |
| DATA-004 | DATA | Ingest treats a filtered selection as a full sync and deactivates/deletes unobserved products | 2 | 3 | 6 | MITIGATE |
| SEC-001 | SEC | `pricecomp_app` over-granted — can `CREATE DATABASE`, run DDL, or reach `pricecomp_phoenix` | 2 | 2 | 4 | MONITOR |
| OPS-001 | OPS | One-shot bootstrap is not idempotent on re-run; second `up` corrupts or half-applies schema state | 2 | 2 | 4 | MONITOR |
| DATA-005 | DATA | Snapshot immutability enforced only in the command handler, bypassable by any adapter reaching the repository | 2 | 2 | 4 | MONITOR |
| DATA-006 | DATA | Manifest-replay "equivalence" is undefined against generated UUIDv7 identities and timestamps — assertion is unwritable as stated | 2 | 2 | 4 | MONITOR |
| DATA-007 | DATA | Money precision lost — float arithmetic or float JSON encoding on `NUMERIC(24,12)` amounts | 2 | 2 | 4 | MONITOR |
| PERF-001 | PERF | No ingest latency or throughput threshold exists anywhere, so AD-4's "measured too slow" deferral trigger can never fire objectively | 2 | 2 | 4 | MONITOR |
| TECH-004 | TECH | Hexagonal dependency direction (AD-10) erodes — a framework import lands in a domain package with nothing detecting it | 2 | 2 | 4 | MONITOR |
| OPS-002 | OPS | Root compose leaks a legacy reference, or the `3020+n` port map drifts | 1 | 3 | 3 | DOCUMENT |
| OPS-003 | OPS | Phoenix 30-day retention or telemetry-disable setting silently reverts on image upgrade | 2 | 1 | 2 | DOCUMENT |

### 3.3 High Risks — Mitigation, Owner, Timeline

#### TECH-001 · PgQueuer completion reliance (score 9 — BLOCK)

**Why 9:** The architecture itself makes this conditional — "failure reopens queue selection"
(Deferred register). AD-22 is bound into AD-14, AD-16, AD-21, and AD-29, and dispatch backs
Epics 1, 2, 4, and 5. Probability is *Likely* because P6 (cancellation at a safe boundary) and
P7 (W3C trace context on job spans) are not first-class PgQueuer features — both need custom
envelope work that may not survive SIGKILL recovery in P4.

**Mitigation — resequence, do not just test.** GATE-03 currently blocks Story 1.10, which sits
tenth in the epic. Build `backend/tests/integration/test_pgqueuer_reliance.py` as a **spike
immediately after Story 1.2**, before Stories 1.4–1.9 accumulate code that assumes PgQueuer.
The cost of the proof is identical; the cost of failure drops by an epic's worth of rework.

**Action taken (2026-08-01):** Story `1-2a-prove-pgqueuer-completion-reliance` created at
`ready-for-dev`; GATE-03, sprint-status, and epics resequenced so the spike blocks 1.4+;
Story 1.10 retains production dispatch and treats P1–P8 as regression.

**Owner:** Dev + TEA · **Timeline:** Story 1.2a before Story 1.4 · **Status:** RESEQUENCED
(story `ready-for-dev`; proof pending)

#### TECH-002 · Test toolchain gap (score 9 — BLOCK)

**Why 9:** Present, observed condition — `pyproject.toml` dev group is `pytest==9.1.1` alone.
AD-31's mandatory D6 regression test, the GATE-03 suite, and every integration test in this
plan are unwritable against it. Impact is Critical because it blocks *all* Epic 1 verification.

**Mitigation — trivial to close, blocking only because everything depends on it.** Before Story
1.2 merges, add to the dev group: an async driver (`pytest-asyncio` or `anyio`), disposable
PostgreSQL 18.4 provisioning (`testcontainers[postgres]` or `pytest-postgresql`), `pytest-cov`,
and a `conftest.py` exposing a per-test disposable database fixture. Add a process-spawning
harness for the Story 1.3 and GATE-03 P4 scenarios, which cannot run in-process.

**Owner:** Dev · **Timeline:** before Story 1.2 merges · **Status:** CLOSED (Story 1.2 —
deps, conftest, kill harness, CI coverage)

#### DATA-001 · D6 enrichment wipe (score 6 — MITIGATE)

**Why 6:** Impact Critical — silent loss of paid LLM output that also poisons eval baselines.
Probability Possible rather than Likely because Story 1.8 builds the ownership boundary
structurally; the exposure is *erosion* as Epic 3 extends the same table.

**Mitigation:** the AD-31 mandatory regression test, written so it fails on widening rather than
only on wiping — assert the upsert's writable set, not just the post-condition. Pair it with
TECH-004's dependency-direction check so a new enrichment column mapping in the catalog
repository fails CI.

**Owner:** Dev · **Timeline:** Story 1.8, re-verified at every Epic 3 story · **Status:** OPEN

#### TECH-003 · Advisory lock and connection pooling (score 6 — MITIGATE)

**Why 6:** AD-16 states four other invariants (AD-3, AD-17, AD-21, AD-22 concurrency machinery)
are omitted *because* this lock holds. The stack pins `psycopg-pool==3.3.1`; a session-level
`pg_advisory_lock` acquired on a pooled connection is released the moment that connection
returns to the pool, and nothing surfaces the failure.

**Mitigation:** acquire the lock on a dedicated, pool-excluded connection held for process
lifetime. Test must assert the lock still blocks a second worker *after* the first worker has
performed pooled database work — not merely at startup.

**Owner:** Dev · **Timeline:** Story 1.3 · **Status:** OPEN

#### DATA-002 · Idempotency lifetime vs retention (score 6 — MITIGATE)

**Why 6:** Story 1.9's AC asserts record lifetime "exceeds queue and checkpoint retention", but
retention is an open item — "Queue/checkpoint maintenance thresholds: before sustained ingest,
set retention…" (Deferred register). The AC is therefore **currently untestable**: there is no
number to exceed.

**Mitigation:** bind a provisional retention figure before Story 1.9 so the assertion has a
referent, and test the ordering property (idempotency TTL > queue TTL) rather than a literal
duration, so the test survives later retuning.

**Owner:** Architect (threshold) + Dev (test) · **Timeline:** before Story 1.9 · **Status:** OPEN

#### DATA-003 · Source identity fallback (score 6 — MITIGATE)

**Mitigation:** negative tests are the primary control — a record with a missing stable ID must
defer/fail, and must *not* produce a product row. Assert absence, not just the error. Include
the intra-snapshot collision case (AC 4), which is the one most likely to be silently resolved
by an upsert.

**Owner:** Dev · **Timeline:** Story 1.5 · **Status:** OPEN

#### DATA-004 · Selection treated as full sync (score 6 — MITIGATE)

**Why 6:** Probability is elevated by precedent — the legacy importer operated on whole-file
semantics, and "reconcile everything not seen" is the default mental model for importers. MVP
explicitly forbids it: no completeness assertion, no absence-driven deactivation (AD-6).

**Mitigation:** the canonical test seeds N products, ingests a filter matching one, and asserts
the other N-1 rows are byte-identical afterwards — including their enrichment state, which
overlaps DATA-001.

**Owner:** Dev · **Timeline:** Story 1.6 · **Status:** OPEN

### 3.4 NFR Planning Assessment

Planning only — no PASS/CONCERNS/FAIL is asserted here. Run `nfr-assess` once implementation
evidence exists.

| Category | In scope for Epic 1 | Threshold | Source | Planned evidence |
| --- | --- | --- | --- | --- |
| Reliability | Yes | 5 retries, exponential full jitter, cap 15 min | AD-22, GATE-03 | Integration test asserting attempt count and backoff ceiling |
| Reliability | Yes | Work states exactly `pending`/`running`/`retry_wait`/`completed`/`failed`/`cancelled` | AD-22 | Enum contract test + state-transition integration test |
| Reliability | Yes | `invalid`/`defer` never infrastructure-retry | AD-22 | Negative integration test |
| Reliability | Yes | Second worker exit code — **UNKNOWN**, "distinct non-zero" is unspecified | Story 1.3 AC | Clarification item CL-1 |
| Security | Yes | `pricecomp_app` cannot `CREATE DATABASE`; cannot write `pricecomp_phoenix` | GATE-02 | Two negative integration tests (named in GATE-02 checklist) |
| Security | Yes | Migrate-role credentials absent from `api`/`worker` environment | GATE-02 | Compose/env assertion test |
| Security | Deferred | External authN/authZ — out of initiative scope | AD-32 | None; AD-32 prohibits public exposure |
| Security | Yes | Secret handling and log redaction — **UNKNOWN** | Deferred: "Configuration and secrets contract" | Clarification item CL-2 |
| Performance | Yes | **UNKNOWN** — no ingest latency or throughput budget exists | — | Clarification item CL-3; capture baseline as observability, not a gate |
| Scalability | Bounded | Exactly one worker; more is a boot failure | AD-16 | Covered by TECH-003 tests; not a gap but a deliberate ceiling |
| Maintainability | Yes | Domain packages import no FastAPI/Pydantic/SQLAlchemy/LangGraph/LangChain/PgQueuer/Phoenix/OTel | AD-10 | Automated import-boundary check in CI (currently absent — TECH-004) |
| Observability | Partial | W3C trace context propagates onto job spans | AD-12, GATE-03 P7 | GATE-03 P7 |
| Observability | Yes | Phoenix raw-trace retention 30 days; product telemetry off | Story 1.2 AC | Post-bootstrap settings assertion |
| Recoverability | Yes | Recovery is manifest re-import; no restore drill required | AD-15 | Story 1.11 replay-equivalence test (blocked on DATA-006) |
| Recoverability | Deferred | RPO/RTO — **UNKNOWN** | Deferred: "Backup/recovery contract" | Out of Epic 1 scope; no local data yet |
| Compliance | No | No PII or regulated data in scope | — | None |

**Clarification items raised (do not guess these):**

- **CL-1** — Which exit code signals the single-writer conflict? Needed to assert Story 1.3 AC 2.
- **CL-2** — Which variables are secrets, and what is the log-redaction rule?
- **CL-3** — What ingest throughput/latency is acceptable, and at what catalog size? Without it,
  PERF-001 stands and AD-4's deferred-projection trigger has no objective threshold.
- **CL-4** — What does "equivalent" mean for two manifest replays, given UUIDv7 identities and
  timestamps differ by construction? (DATA-006)
- **CL-5** — Provisional queue/checkpoint retention, so DATA-002's assertion has a referent.

### 3.5 Risk Summary

**16 risks: 2 BLOCK, 5 MITIGATE, 7 MONITOR, 2 DOCUMENT.**

Both BLOCK-level risks are about **sequencing, not difficulty**. Neither is expensive to
resolve; both are severe only because the epic currently plans to discover them late. TECH-002
is a four-line dependency change that every other test in this plan waits on. TECH-001 is a
proof the architecture already requires — it is scheduled tenth in an epic whose Stories 1.4–1.9
all assume its outcome.

The dominant risk category is **DATA (7 of 16)**, which is faithful to the epic: Epic 1's entire
thesis is non-destructive ingest under durable identity. Four of the five MITIGATE risks are
data-integrity failures that are *silent* — enrichment wipe, double-applied effects, synthesised
identity, and absence-driven deletion all leave a system that looks healthy. That shapes the
coverage plan in Step 4: these need assertions on what did **not** change, which is a materially
different test shape from asserting a happy path.

Five acceptance criteria are currently **untestable as written** and are tracked as CL-1 to CL-5.

---

## Step 04: Coverage Plan & Execution Strategy

### 4.0 Level Vocabulary

Epic 1 has no UI, so the standard E2E/API/Component/Unit ladder is mapped onto the backend
shape declared by AD-31 and the structural seed:

| Level | Meaning here | Runs against |
| --- | --- | --- |
| **UNIT** | Pure domain and static/architecture assertions | No framework, no database |
| **INT** | Persistence, UoW, queue, checkpoint, migration adapters | Disposable PostgreSQL 18.4 |
| **CONTRACT** | `contracts/v1` schemas, error codes, wire encoding | No database |
| **PROC** | Real process spawn/kill — role commands, advisory lock | Compose or spawned processes |
| **E2E** | Full manifest replay through the importer | Full stack |

`PROC` exists because Story 1.3 AC 2 ("exits with a distinct non-zero status code") and
GATE-03 P4 ("SIGKILL mid-handler") are assertions about process exit and process death. They
cannot be made in-process, and collapsing them into INT would silently weaken both.

### 4.1 Coverage Matrix

**Story 1.1 — Relocate Legacy TypeScript and Seed the Python Monolith** *(status: review)*

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.1-UNIT-001 | UNIT | Seed packages import — all nine | P2 | — |
| 1.1-UNIT-002 | UNIT | `retrieval/` absent (AD-35 retired) | P2 | — |
| 1.1-UNIT-003 | UNIT | `migrations/` and four test dirs exist | P2 | — |
| 1.1-UNIT-004 | UNIT | Seed carries no domain logic — packages contain `__init__.py` only | P2 | — |
| 1.1-UNIT-005 | UNIT | Relocation layout: `legacy/*` present, `data/`+`frontend/` at root, `sync-ai-rules.sh` and `.cursor/rules/` absent | P2 | OPS-002 |
| 1.1-INT-001 | INT | `uv sync` on committed lock resolves CPython 3.14.6 / uv 0.12.1; no LangGraph Server/CLI extras; no Pydantic V1 in resolved set | P1 | — |

*1.1-UNIT-001/002/003 already exist in `tests/domain/test_structural_seed.py`. Husky `pre-commit`
scoping is left to review rather than automated — asserting on a git hook costs more than it returns.*

**Story 1.2 — Run the Stack Locally with Role Commands**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.2-PROC-001 | PROC | `api` role starts independently from the shared image | P0 | — |
| 1.2-PROC-002 | PROC | `worker` role starts independently from the shared image | P0 | — |
| 1.2-PROC-003 | PROC | `migrate` role runs one-shot and exits 0 | P0 | — |
| 1.2-INT-001 | INT | Bootstrap executes in order: db/role → Alembic → PgQueuer → LangGraph → Phoenix → readiness | P0 | OPS-001 |
| 1.2-INT-002 | INT | Every bootstrap step is idempotent — second run is a clean no-op | P0 | OPS-001 |
| 1.2-INT-003 | INT | `pricecomp_app` cannot `CREATE DATABASE` | P0 | SEC-001 |
| 1.2-INT-004 | INT | `pricecomp_app` cannot write to `pricecomp_phoenix` | P0 | SEC-001 |
| 1.2-INT-005 | INT | PostgreSQL 18.x on host 3021, durable volume at `/var/lib/postgresql` | P1 | OPS-002 |
| 1.2-INT-006 | INT | Phoenix `version-19.11.1` on 3022, `PHOENIX_SQL_DATABASE_URL` → `pricecomp_phoenix` | P1 | OPS-002 |
| 1.2-INT-007 | INT | `api` binds host 3020 when started | P1 | OPS-002 |
| 1.2-INT-008 | INT | App role has USE+EXECUTE but no DDL on `pgqueuer` and `langgraph` schemas | P1 | SEC-001 |
| 1.2-INT-009 | INT | Migrate/elevated credentials absent from `api` and `worker` environments | P1 | SEC-001 |
| 1.2-UNIT-001 | UNIT | Root compose parses with zero legacy references — no env var, volume, `depends_on`, or connection string | P1 | OPS-002 |
| 1.2-INT-010 | INT | Phoenix raw-trace retention 30 days; product telemetry disabled | P2 | OPS-003 |
| 1.2-UNIT-002 | UNIT | No Redis or external workflow runtime in the dependency or service graph | P2 | — |
| 1.2-UNIT-003 | UNIT | Devcontainer and CI invoke the same role commands and same PostgreSQL image | P2 | — |

**Story 1.2a — Prove PgQueuer Completion Reliance (GATE-03 Spike)** *(pulled forward from 1.10 — TECH-001)*

| ID | Level | Scenario | Pri | Risk | Gate |
| --- | --- | --- | :-: | --- | --- |
| 1.2a-INT-001 | INT | Job runs once after the owner row commits | P0 | TECH-001 | P1 |
| 1.2a-INT-002 | INT | Lost enqueue recovered by re-driving from the owner row; no duplicate effect | P0 | TECH-001 | P2 |
| 1.2a-INT-003 | INT | Duplicate enqueue — second handler invocation is a no-op | P0 | TECH-001 | P3 |
| 1.2a-PROC-001 | PROC | SIGKILL mid-handler → restart reaches terminal state without double effect | P0 | TECH-001 | P4 |
| 1.2a-INT-004 | INT | `AsyncPostgresSaver` resumes the same `thread_id` (`pipeline_run_id`) | P0 | TECH-001 | P5 |
| 1.2a-INT-005 | INT | Cancellation drives the run to `cancelled` at a safe boundary | P0 | TECH-001 | P6 |
| 1.2a-INT-006 | INT | W3C trace context propagates onto job spans and is visible in Phoenix | P0 | TECH-001 | P7 |
| 1.2a-INT-007 | INT | Exhausted retries → state `failed`, row inspectable, manual requeue works | P0 | TECH-001 | P8 |

*These eight scenarios are the GATE-03 suite. Story 1.10 reuses them as regression and adds
central-retry-policy ACs. File: `backend/tests/integration/test_pgqueuer_reliance.py`.*

**Story 1.3 — Enforce the Single Writer at Worker Startup**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.3-PROC-001 | PROC | First worker acquires the session-level advisory lock and proceeds to serve work | P0 | TECH-003 |
| 1.3-PROC-002 | PROC | Second worker does no work, exits with the reserved non-zero code, logs the single-writer cause | P0 | TECH-003 |
| 1.3-PROC-003 | PROC | **Lock survives pooled activity** — after worker 1 performs pooled DB work, worker 2 still fails to boot | P0 | TECH-003 |
| 1.3-PROC-004 | PROC | Worker killed (SIGKILL) → database releases lock → next worker starts successfully | P0 | TECH-003 |
| 1.3-PROC-005 | PROC | Two-replica / rolling deploy: second fails to boot, first keeps serving uninterrupted | P1 | TECH-003 |
| 1.3-INT-001 | INT | Lock is scoped per application database — two workers on two databases both start (bakeoff case) | P1 | TECH-003 |

*1.3-PROC-003 is the scenario that actually retires TECH-003. A naive test acquires the lock and
immediately checks a second boot, which passes even when the lock sits on a pooled connection
that has not yet been returned. Doing pooled work first is what exposes it.*
*1.3-PROC-002 is blocked on CL-1 until the reserved exit code is chosen.*

**Story 1.4 — Register an Immutable Catalog Snapshot**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.4-INT-001 | INT | Registration creates a row with UTC source-observed time, input checksum, adapter version, UUIDv7 identity | P0 | — |
| 1.4-INT-002 | INT | Identifying-field modification is rejected **at the database level**, row unchanged | P0 | DATA-005 |
| 1.4-INT-003 | INT | Same checksum + adapter version registered twice resolves to the existing snapshot, no duplicate | P0 | — |
| 1.4-INT-004 | INT | Write occurs inside one Unit of Work through a single command handler | P1 | — |
| 1.4-UNIT-001 | UNIT | Source-observed time is interpreted as UTC, including a non-UTC input | P1 | — |
| 1.4-UNIT-002 | UNIT | No adapter reaches the repository or SQL directly (AD-14 static check) | P1 | TECH-004 |

*1.4-INT-002 asserts at the database level deliberately. Enforcing immutability only in the
command handler leaves DATA-005 open, because the assertion would pass while any future
repository call could still mutate the row.*

**Story 1.5 — Import Products Under Durable Source Identity**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.5-INT-001 | INT | Product keyed by `(namespace, product_id, variant_id)` with `UNIQUE NULLS NOT DISTINCT` — null variant collides as expected | P0 | DATA-003 |
| 1.5-INT-002 | INT | Re-import after name/URL change resolves to the same catalog product | P0 | DATA-003 |
| 1.5-INT-003 | INT | Changed name and URLs land as new mutable observations, not as identity | P0 | DATA-003 |
| 1.5-UNIT-001 | UNIT | Record with missing or untrustworthy stable ID → adapter defers or fails explicitly | P0 | DATA-003 |
| 1.5-INT-004 | INT | Deferred record produces **no** catalog product row — assert absence, not just the error | P0 | DATA-003 |
| 1.5-INT-005 | INT | Two records colliding on one source identity within a snapshot → collision reported, not silently resolved | P0 | DATA-003 |
| 1.5-INT-006 | INT | Product carries a UUIDv7 application identity distinct from its source identity | P1 | — |
| 1.5-INT-007 | INT | Namespace identity-policy change without a migration/alias map is refused | P1 | DATA-003 |
| 1.5-UNIT-002 | UNIT | Adapter declares a versioned normalization policy, recorded with the import | P1 | — |

**Story 1.6 — Select What to Ingest**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.6-INT-001 | INT | Empty filter selects the whole snapshot (bulk) | P0 | — |
| 1.6-INT-002 | INT | Filter matching one product performs single-product ingest through the identical path | P0 | — |
| 1.6-INT-003 | INT | Category/keyword filter selects the subset and records an immutable ingest-selection manifest | P0 | — |
| 1.6-INT-004 | INT | **Unobserved products untouched** — seed N, ingest a filter of 1, assert the other N-1 rows unchanged including enrichment state | P0 | DATA-004, DATA-001 |
| 1.6-INT-005 | INT | No deactivation applied and no completeness assertion recorded for absent products | P0 | DATA-004 |
| 1.6-UNIT-001 | UNIT | No mode-specific branch exists in the ingest or downstream agent path (static check) | P1 | — |

**Story 1.7 — Record Revisioned Shelf Prices**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.7-INT-001 | INT | `NUMERIC(24,12)` round-trips through the adapter with no precision loss | P0 | DATA-007 |
| 1.7-INT-002 | INT | Newer revision supersedes prior; **database constraint** enforces ≤1 current row per kind | P0 | — |
| 1.7-UNIT-001 | UNIT | Price selection across several current kinds follows one deterministic rule — identical inputs, identical output | P0 | — |
| 1.7-CONTRACT-001 | CONTRACT | JSON serialisation emits the decimal as a string, never a float | P0 | DATA-007 |
| 1.7-UNIT-002 | UNIT | Kind enum is exactly `regular`/`promo`/`per_unit`, lowercase snake_case | P1 | — |
| 1.7-UNIT-003 | UNIT | Amount must be a positive Decimal; currency validated as ISO 4217 | P1 | DATA-007 |

**Story 1.8 — Guarantee Re-Import Never Wipes Enrichment** *(AD-31 mandatory)*

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.8-INT-001 | INT | **D6 regression** — seed enrichment-owned attributes, run a full re-import, assert every value unchanged | P0 | DATA-001 |
| 1.8-UNIT-001 | UNIT | Catalog upsert's declared writable set contains only catalog-owned tables and columns | P0 | DATA-001 |
| 1.8-UNIT-002 | UNIT | No code path, repository, or column mapping reaches enrichment-owned state from the import path | P0 | DATA-001, TECH-004 |
| 1.8-INT-002 | INT | Deterministic catalog-owned fields **do** update from the new observation | P0 | DATA-001 |
| 1.8-INT-003 | INT | Writing an enrichment-owned value through the import path is rejected, not silently applied | P0 | DATA-001 |
| 1.8-INT-004 | INT | Minimal enrichment-owned attribute revision table created — and nothing beyond it | P1 | — |

*1.8-UNIT-001 is the test that makes DATA-001 durable. 1.8-INT-001 alone proves today's upsert
does not wipe; only the writable-set assertion fails when Epic 3 widens the upsert, which is the
actual failure mode the AC names ("fails if the upsert is ever widened").*

**Story 1.9 — Make Commands Idempotent Under Replay**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.9-UNIT-001 | UNIT | Record scoped by `(command_type, caller, key)` and bound to a canonical payload hash | P0 | — |
| 1.9-INT-001 | INT | Resubmitting an in-progress triple observes in-progress state; no second execution starts | P0 | DATA-002 |
| 1.9-INT-002 | INT | Terminal + identical payload returns the stored result; no business effect applied twice | P0 | DATA-002 |
| 1.9-INT-003 | INT | Terminal + changed payload is rejected with a stable domain error code | P0 | — |
| 1.9-INT-004 | INT | Idempotency record and business effects commit in the same Unit of Work | P0 | DATA-002 |
| 1.9-INT-005 | INT | Record still resolves after queue/checkpoint retention has elapsed — asserted as an ordering property (idempotency TTL > queue TTL) | P1 | DATA-002 |

*1.9-INT-005 is blocked on CL-5. Testing the ordering property rather than a literal duration
keeps the test valid when retention is later retuned.*

**Story 1.10 — Dispatch Durable Work with a Central Retry Policy** *(GATE-03 regression; proof owned by 1.2a)*

| ID | Level | Scenario | Pri | Risk | Gate |
| --- | --- | --- | :-: | --- | --- |
| 1.10-INT-001…007 / 1.10-PROC-001 | INT+PROC | P1–P8 (same assertions as 1.2a-*) | P0 | TECH-001 | P1–P8 |
| 1.10-INT-008 | INT | Transient infra failure retries ≤5 times, exponential full jitter, capped at 15 min | P0 | — | — |
| 1.10-INT-009 | INT | Deterministic `invalid`/`defer` outcome triggers no infrastructure retry | P0 | — | — |
| 1.10-UNIT-001 | UNIT | Work state enum is exactly the six AD-22 states | P1 | — | — |
| 1.10-UNIT-002 | UNIT | No transaction-joining producer bridge exists (static check) | P1 | — | — |

*P1–P8 IDs 1.10-INT-001…007 / 1.10-PROC-001 are aliases of the 1.2a suite — do not double-count
toward the 51 P0 total. Story 1.10's unique P0 additions are the two retry-policy scenarios.*

**Story 1.11 — Rebuild the Catalog from an Immutable Source Manifest**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| 1.11-E2E-001 | E2E | Fresh databases + manifest replay through the Python importer rebuilds the catalog | P0 | — |
| 1.11-INT-001 | INT | No legacy AI-derived category or attribute state present after replay | P0 | — |
| 1.11-E2E-002 | E2E | Recovery is achieved purely by re-running the manifest replay | P1 | — |
| 1.11-E2E-003 | E2E | Same manifest replayed twice into fresh databases yields equivalent state | P1 | DATA-006 |
| 1.11-INT-002 | INT | Legacy remains read-only while the rebuild runs | P1 | — |
| 1.11-UNIT-001 | UNIT | No flat-taxonomy compatibility layer exists on the taxonomy surface | P1 | — |

*1.11-E2E-003 is blocked on CL-4 — "equivalent" is undefined against UUIDv7 identities and
timestamps that differ by construction. It needs a stated comparison that excludes generated
identity and time fields, or the assertion cannot be written.*

**Cross-Cutting**

| ID | Level | Scenario | Pri | Risk |
| --- | --- | --- | :-: | --- |
| X-UNIT-001 | UNIT | Domain packages import no FastAPI/Pydantic/SQLAlchemy/LangGraph/LangChain/PgQueuer/Phoenix/OTel (AD-10 boundary check in CI) | P1 | TECH-004 |
| X-INT-001 | INT | Ingest throughput/latency baseline captured as a recorded number, non-gating | P3 | PERF-001 |

### 4.2 Coverage Totals

| Priority | Count | Share |
| --- | :-: | :-: |
| P0 | 51 | 59% |
| P1 | 27 | 31% |
| P2 | 8 | 9% |
| P3 | 1 | 1% |
| **Total** | **87** | |

| Level | Count |
| --- | :-: |
| INT | 51 |
| UNIT | 23 |
| PROC | 9 |
| E2E | 3 |
| CONTRACT | 1 |

*Counts derived mechanically from §4.1 rather than tallied by hand.*

The P0 share is high for an epic, and that is deliberate rather than inflation: Epic 1 is
foundational infrastructure where "blocks core functionality, high risk, no workaround" is
simply true of most of it. Every downstream epic builds on ingest identity, dispatch, and the
ownership boundary.

INT dominance follows AD-31 — pure domain logic is thin in Epic 1, and almost every invariant
is a persistence, constraint, or transaction property that only a real PostgreSQL 18.4 can prove.

### 4.3 NFR Coverage and Evidence Plan

| NFR category | Validation level / tool | Scenarios | Evidence artifact for `nfr-assess` |
| --- | --- | --- | --- |
| Reliability — retry policy | INT against disposable PG | 1.10-INT-008, 1.10-INT-009 | pytest report + captured attempt timings |
| Reliability — durable dispatch | INT + PROC | 1.10-INT-001…007, 1.10-PROC-001 | GATE-03 suite green on Linux CI |
| Reliability — single writer | PROC | 1.3-PROC-001…005, 1.3-INT-001 | Process exit codes + worker logs |
| Security — least privilege | INT negative tests | 1.2-INT-003, 1.2-INT-004, 1.2-INT-008 | pytest report; GATE-02 checklist ticked |
| Security — credential scoping | INT | 1.2-INT-009 | Environment assertion output |
| Security — secrets/redaction | **Blocked** | — | CL-2 must land first |
| Performance | INT benchmark, non-gating | X-INT-001 | Recorded baseline number in CI artifact |
| Maintainability — AD-10 | Static import-boundary check in CI | X-UNIT-001, 1.8-UNIT-002 | CI job result |
| Observability — trace context | INT via Phoenix | 1.10-INT-006 | Phoenix span inspection |
| Observability — Phoenix config | INT | 1.2-INT-010 | Settings assertion output |
| Recoverability | E2E | 1.11-E2E-001…003 | Replay run logs + state comparison |
| Scalability | Bounded by AD-16, not measured | 1.3-* | Single-writer evidence above |
| Compliance | Not in scope | — | — |

Blockers and assumptions: PERF-001 has no threshold (CL-3), so X-INT-001 records a number
rather than gating on one. Security secrets/redaction has no evidence source until CL-2.

### 4.4 Execution Strategy

| Stage | Contents | Budget |
| --- | --- | --- |
| **PR** | All UNIT + CONTRACT, plus INT against a disposable PostgreSQL 18.4 | < 15 min |
| **Nightly** | All PROC (process spawn, SIGKILL, rolling deploy), full compose bootstrap incl. idempotent re-run, complete GATE-03 P1–P8, 1.11-E2E-001/002 | ~30–45 min |
| **Weekly** | 1.11-E2E-003 double replay at full manifest size, X-INT-001 perf baseline | unbounded |

Two deviations from the default model, both deliberate:

- **GATE-03 runs in PR for Story 1.10 itself**, then moves to nightly. It is the gate artifact
  for that story; discovering a P1–P8 failure the night after merge defeats its purpose.
- **PROC tests are nightly, not PR.** Process spawn and SIGKILL recovery are slow and the
  likeliest source of CI flake. Story 1.3's own PR is the exception — its ACs *are* PROC tests.

Story 1.1's suite is already PR-resident and stays there.

### 4.5 Resource Estimates

Ranges only — these are backend integration tests against real PostgreSQL, where fixture and
teardown work typically exceeds assertion work.

| Bucket | Scope | Estimate |
| --- | --- | --- |
| **Foundation** | Close TECH-002 — dev deps, `conftest.py`, disposable-DB fixture, process-spawn harness, CI wiring | ~12–20 h |
| P0 | 51 scenarios, INT-heavy, incl. full GATE-03 suite | ~60–90 h |
| P1 | 27 scenarios | ~25–40 h |
| P2 | 8 scenarios | ~6–12 h |
| P3 | 1 scenario | ~3–6 h |
| **Total** | | **~106–168 h** |

Roughly 3–5 weeks of dedicated test effort for one engineer, interleaved across the eleven
stories rather than batched. The foundation bucket is the critical path — nothing else starts
until it lands, which is exactly why TECH-002 scores BLOCK.

GATE-03 alone is ~20–30 h of the P0 figure. If TECH-001 materialises and queue selection
reopens, that work is largely lost, which is the second argument for running it early.

### 4.6 Quality Gates

| Gate | Threshold |
| --- | --- |
| P0 pass rate | 100% — no exceptions, no waivers |
| P1 pass rate | ≥ 95% |
| P2/P3 | Tracked, non-blocking |
| High-risk mitigation | Both BLOCK risks (TECH-001, TECH-002) closed before the epic is called done |
| Score-6 risks | All five MITIGATE risks have a green owning test |
| Line coverage | ≥ 80% on `src/pricecomp/`, measured once `pytest-cov` exists |
| Mandatory tests | AD-31's D6 regression (1.8-INT-001) and GATE-03 P1–P8 green on Linux CI + PostgreSQL 18 |
| NFR evidence | Every in-scope NFR category has a named evidence artifact; UNKNOWN thresholds resolved or explicitly accepted |
| Clarifications | CL-1 through CL-5 resolved, or their dependent ACs formally deferred |

Gate decision follows `risk-governance.md`: any unresolved score-9 risk or any P0 coverage gap
→ **FAIL**. Score 6–8 risks with an owner and mitigation plan → **CONCERNS**. Otherwise **PASS**.

**Epic 1 cannot currently reach PASS** — TECH-001 and TECH-002 are both open at score 9. That is
the expected state at test-design time, not a defect in the epic; it is what the plan exists to
retire.

---

## Step 05: Output Generation & Validation

### Execution Mode Resolved

`tea_execution_mode: auto`, `tea_capability_probe: true`. Step 5 §1 states Epic-Level Mode
"remains single-worker by default (one output artifact)", so no subagent or agent-team
orchestration was used — a single output document does not decompose into parallel workers.

### Output

- **`_bmad-output/test-artifacts/test-design-epic-1.md`** — generated from `test-design-template.md`
- Handoff document **not** generated: §4 restricts it to System-Level Mode

### Checklist Validation

Validated against `checklist.md`. Passing on all Epic-Level sections. Four items required
correction during validation, all now fixed:

| Checklist item | Finding | Fix applied |
| --- | --- | --- |
| Execution Strategy — "Simple structure: PR / Nightly / Weekly (NOT complex smoke/P0/P1/P2 tiers)" | Draft carried a fourth "Smoke" tier, and the template's own §Execution Order uses P0/P1/P2 tiers — template and checklist conflict | Collapsed to PR / Nightly / Weekly; renamed the section to Execution Strategy; added the "<15 min in PR" philosophy statement. Checklist wins over template here — it marks the item CRITICAL |
| Priority Assignment — "Note at top of Test Coverage Plan clarifies P0–P3 = priority/risk, NOT execution timing" | Missing | Added as a callout above the coverage plan |
| Risk Assessment — "Residual risk documented" | Missing | Added §Residual Risk After Mitigation with six accepted exposures |
| Exit Criteria — "Bug severity gate defined" | Missing | Added no-open-P0/P1-bugs gate, with DATA-category defects defaulting to P0 |

Deliberate deviations, each recorded in the document itself:

- **Risk IDs are category-prefixed** (`TECH-001`, `DATA-001`) rather than `R-001`. The checklist
  requires unique IDs and gives `R-00N` as an example; category prefixes satisfy uniqueness and
  make the DATA concentration legible at a glance.
- **Resource estimate table uses hour ranges per test** rather than the template's fixed
  multipliers (P0 = 2.0 h, etc.). A flat multiplier would misstate both ends — an INT scenario
  against real PostgreSQL costs far more than a static UNIT assertion.
- **Execution budgets exceed the template's envelopes** (P0 in <10 min). Not achievable for an
  epic whose P0 set includes container bootstrap and SIGKILL recovery.
- **Playwright parallelisation note: N/A** — no browser surface in Epic 1.
- **Project Team section: N/A** — single-operator project; ownership is recorded per-risk.

Housekeeping:

- No CLI browser sessions were opened, so none needed cleanup.
- All artifacts written under `_bmad-output/test-artifacts/`; nothing left in `/tmp` or elsewhere.

### Not Done — and why

**`sprint-status.yaml` was subsequently updated (2026-08-01)** to insert Story 1.2a at
`ready-for-dev` when TECH-001 was resequenced. No "Quality & Testing Progress" section was
added — that generator contract concern still stands.

### Completion Report

**Mode:** Epic-Level (Phase 4), Epic 1 — Runnable Python Stack with Non-Destructive Catalog Ingest

**Outputs:**

- `_bmad-output/test-artifacts/test-design-epic-1.md` (final deliverable)
- `_bmad-output/test-artifacts/test-design-progress.md` (working notes + full scenario matrix)

**Key risks:** 16 total — TECH-002 **CLOSED**; TECH-001 **RESEQUENCED** (Story 1.2a; proof
pending), 5 MITIGATE, 7 MONITOR, 2 DOCUMENT. Dominant category DATA (7 of 16).

**Gate thresholds:** P0 100%, P1 ≥95%, ≥80% line coverage, D6 regression and GATE-03 P1–P8 green
on Linux CI + PostgreSQL 18. Epic 1 still **FAIL**s risk-governance until Story 1.2a turns
GATE-03 green (TECH-002 no longer blocks).

**Open assumptions:** CL-1 through CL-5 unresolved; five acceptance criteria are untestable as
written until they are answered or formally deferred.

### Post-Validation Correction

A mechanical recount of §4.1 during final polish found the summary tables had drifted from the
matrix. The matrix is authoritative; summaries in both documents were corrected to match:

| Figure | Was | Now |
| --- | :-: | :-: |
| Total scenarios | 88 | **87** |
| P1 / P2 / P3 | 28 / 7 / 2 | **27 / 8 / 1** |
| INT / UNIT | 55 / 21 | **51 / 23** |
| PR-stage count | 77 | **65** |

Two substantive fixes came out of it, not just arithmetic:

- A **duplicated P1 row** for Story 1.1's relocation-layout assertions, which were already
  counted at P2. Removed — it also violated the checklist's no-duplicate-coverage rule.
- A **redundant P3 scenario**, "exploratory replay at full manifest size", which duplicated
  1.11-E2E-003 already scheduled weekly at full size. Removed.

P0 was unaffected at 51 throughout.
