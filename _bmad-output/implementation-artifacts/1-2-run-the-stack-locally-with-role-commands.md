---
baseline_commit: ae142e5e7b947e858b43adc980f4e92099aabf1f
---

# Story 1.2: Run the Stack Locally with Role Commands

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want one backend image exposing `api`, `worker`, and `migrate` commands alongside PostgreSQL and Phoenix via root `docker-compose.yml`,
so that I can bring the new stack up locally and in CI with identical commands.

**Gates:** [`GATE-01-bootstrap.md`](gates/GATE-01-bootstrap.md), [`GATE-02-db-privileges.md`](gates/GATE-02-db-privileges.md)

## Acceptance Criteria

1. **Role commands from one image (FR49 / AD-29)**
   - **Given** the backend image
   - **When** it is invoked with `api`, `worker`, or `migrate`
   - **Then** each role starts independently from the same image
   - **And** no Redis or external workflow runtime is required

2. **One-shot bootstrap order and idempotence (NFR19)**
   - **Given** a clean environment
   - **When** the one-shot bootstrap runs (`pricecomp migrate`)
   - **Then** it executes in order: database/role bootstrap → Alembic → PgQueuer install/upgrade → LangGraph checkpointer setup → Phoenix migration readiness → service readiness
   - **And** each step is idempotent on re-run (second `migrate` is a clean no-op)

3. **Root Compose topology (GATE-01 / GATE-02)**
   - **Given** root `docker compose up -d`
   - **When** the Compose environment is brought up
   - **Then** PostgreSQL **18.4** runs on host port **3021** (`3020+1`) with its durable volume mounted at `/var/lib/postgresql`
   - **And** Phoenix runs from `arizephoenix/phoenix:version-19.11.1` on host port **3022** (`3020+2`) against `pricecomp_phoenix` via `PHOENIX_SQL_DATABASE_URL`
   - **And** the `api` role binds host port **3020** when started
   - **And** root compose references **only** the new Postgres instance on **3021** — no env vars, volumes, `depends_on`, or connection strings for legacy (`legacy/docker-compose.yml` / **5532** remain fully separate)

4. **Least-privilege databases and roles (GATE-02)**
   - **Given** the database role and privilege manifest
   - **When** bootstrap provisions databases and roles
   - **Then** `pricecomp_app` and `pricecomp_phoenix` exist with least-privilege runtime roles per GATE-02
   - **And** runtime credentials cannot create databases or run arbitrary migrations
   - **And** PgQueuer (`pgqueuer` schema) and LangGraph (`langgraph` schema) tables live in the application database but remain vendor-owned with their own schemas and `search_path`
   - **And** elevated migrate credentials are **not** present in `api` or `worker` environments

5. **Phoenix project settings (NFR14)**
   - **Given** Phoenix has started for the first time
   - **When** its project settings are inspected
   - **Then** raw trace retention is set to **30 days**
   - **And** Phoenix product telemetry is disabled

6. **Devcontainer and CI parity (NFR18)**
   - **Given** the devcontainer and CI
   - **When** each runs the stack
   - **Then** both use the same role commands (`pricecomp api` | `worker` | `migrate`) and the same PostgreSQL **18.4** image

## Tasks / Subtasks

- [x] **Close TECH-002 test toolchain gap** (AC: all; blocks verification)
  - [x] Add dev dependencies to `backend/pyproject.toml`: `pytest-asyncio`, disposable PostgreSQL 18.4 (`testcontainers[postgres]` or equivalent), `pytest-cov` (optional but recommended per test design)
  - [x] Add `backend/tests/conftest.py` with a disposable-DB fixture (PostgreSQL 18.4) for integration tests
  - [x] Add a process-spawn harness helper for PROC-level tests (`api`/`worker`/`migrate` exit codes)
  - [x] Run `uv lock` with uv **0.12.1** and commit updated `uv.lock`

- [x] **Postgres init and GATE-02 privilege manifest** (AC: #3, #4)
  - [x] Create `docker/postgres/init/` SQL creating **only** `pricecomp_app` and `pricecomp_phoenix` databases + runtime roles (no legacy DB on new instance)
  - [x] Grant `pricecomp_app` CRUD on `public`; USE+EXECUTE (no DDL) on `pgqueuer` and `langgraph` after migrate creates them
  - [x] Ensure `pricecomp_phoenix` role is Phoenix-only; app role cannot write `pricecomp_phoenix`
  - [x] Document elevated bootstrap credentials used **only** by `migrate` (postgres superuser or dedicated bootstrap role inside compose network — never in api/worker env)

- [x] **Root `docker-compose.yml`** (AC: #3, #5; GATE-01 + GATE-02)
  - [x] Service `postgres`: image `postgres:18.4` (pin exact — not floating `18-alpine`), host **3021:5432**, volume at `/var/lib/postgresql`, mount `docker/postgres/init/`
  - [x] Service `phoenix`: image `arizephoenix/phoenix:version-19.11.1`, host **3022:6006**, `PHOENIX_SQL_DATABASE_URL` → `pricecomp_phoenix` on internal `postgres:5432`
  - [x] Set `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS=30` and `PHOENIX_TELEMETRY_ENABLED=false` on Phoenix service
  - [x] **No** legacy references: no `legacy/`, no port 5532, no shared volumes, no `depends_on` to legacy stack
  - [x] Optional compose profiles for `api` / `worker` services built from backend image (or document host-run pattern for dev — but `api` on **3020** must be demonstrable)

- [x] **Backend Dockerfile + role entrypoint** (AC: #1, #3)
  - [x] Add `backend/Dockerfile` — multi-stage or slim Python 3.14.6 base; install via `uv sync --frozen`; expose CLI entrypoint
  - [x] Register console script `pricecomp` in `pyproject.toml` → dispatches `api` | `worker` | `migrate`
  - [x] `api`: minimal FastAPI app on **0.0.0.0:3020** with `/health` (and readiness that checks DB connectivity); **no** domain routes yet
  - [x] `worker`: long-running process that starts cleanly and blocks (advisory lock is Story **1.3** — do not implement lock here)
  - [x] `migrate`: one-shot orchestrator per NFR19 bootstrap order, exit **0** on success

- [x] **Wire Alembic + vendor schema bootstrap inside `migrate`** (AC: #2, #4)
  - [x] Add `alembic.ini` + `migrations/env.py` targeting `pricecomp_app` via migrate credentials
  - [x] Initial Alembic revision may be empty/minimal (`alembic_version` only) — no domain tables yet
  - [x] PgQueuer: run `pgq install` / upgrade into `pgqueuer` schema (idempotent)
  - [x] LangGraph: run `AsyncPostgresSaver.setup()` into `langgraph` schema (idempotent)
  - [x] Phoenix migration step: wait for Phoenix DB reachable / Phoenix container healthy (Phoenix owns its schema in `pricecomp_phoenix`)
  - [x] Re-run safety: second `migrate` must not error or duplicate objects

- [x] **Devcontainer** (AC: #6; NFR18)
  - [x] Add `.devcontainer/devcontainer.json` using the same `docker-compose.yml` + `postgres:18.4` image
  - [x] Devcontainer invokes same `pricecomp` role commands (document in `backend/README.md`)
  - [x] Mount `backend/` for live edit; `uv sync` on post-create

- [x] **CI workflow skeleton** (AC: #6; NFR18)
  - [x] Add `.github/workflows/backend.yml` (or equivalent) running on Linux with PostgreSQL **18.4**
  - [x] CI uses same role commands: at minimum `uv run pytest`, `pricecomp migrate` against service container, and smoke `api` health on 3020
  - [x] Do **not** block on full GATE-03 PgQueuer proof — that spike is scheduled **after** this story per test design

- [x] **Integration + PROC tests** (AC: #1–#6; test-design 1.2-*)
  - [x] `1.2-PROC-001/002/003`: spawn `api`, `worker`, `migrate` from image/venv independently
  - [x] `1.2-INT-001/002`: bootstrap order + idempotent re-run
  - [x] `1.2-INT-003/004`: `pricecomp_app` cannot `CREATE DATABASE`; cannot write `pricecomp_phoenix`
  - [x] `1.2-INT-005/006/007`: ports 3021/3022/3020 wiring (compose or testcontainers)
  - [x] `1.2-INT-008/009`: vendor schema DDL denied to app role; migrate creds absent from api/worker env
  - [x] `1.2-UNIT-001`: static parse of root compose — zero legacy references
  - [x] `1.2-INT-010`: Phoenix retention 30d + telemetry off (env assertion or settings API if available)
  - [x] `1.2-UNIT-002`: no Redis/external workflow in dependency graph
  - [x] `1.2-UNIT-003`: devcontainer + CI config assert same PG image tag and role command strings

- [x] **Documentation + gate evidence** (AC: #3–#6)
  - [x] Update root `README.md`: `docker compose up -d`, `pricecomp migrate`, `pricecomp api`, port map
  - [x] Update `backend/README.md`: role commands, env vars (`DATABASE_URL` for app on **3021**), migrate vs runtime creds
  - [x] Tick GATE-01 compose + API-listen items; tick GATE-02 checklist items when tests pass

## Dev Notes

### Continuity from Story 1.1 (do not redo)

Story 1.1 **done** — structural seed committed (`ae142e5`, `1e29bd0`):

| Already on disk | Do not recreate |
|-----------------|-----------------|
| `backend/pyproject.toml` + `uv.lock` with NFR17 pins | Empty package tree under `src/pricecomp/` |
| `backend/migrations/` placeholder | Domain logic, repositories, commands |
| `backend/tests/domain/test_structural_seed.py` | Root `docker-compose.yml`, Dockerfile, CLI |
| GATE-01 relocation + seed ticks | Legacy path fixes |

**Primary work for 1.2:** operational shell — Compose, Dockerfile, CLI roles, bootstrap, devcontainer, CI, integration tests.

### Scope boundaries (hard)

**In scope:** root Compose (Postgres + Phoenix), backend image, `pricecomp {api,worker,migrate}`, GATE-02 init SQL, Alembic shell + vendor schema bootstrap, minimal health endpoints, devcontainer, CI skeleton, TECH-002 test harness, GATE-01/02 evidence.

**Out of scope (later stories):**
- **1.3:** advisory lock at worker startup (worker may start without lock enforcement this story)
- **1.4+:** domain tables, catalog import, repositories, Unit of Work
- **AD-5 full surface:** FastMCP mount, curated MCP tools, REST command handlers beyond health
- **GATE-03:** full PgQueuer completion-reliance proof (spike **after** 1.2 merges, before 1.4)
- **Domain packages:** no business logic in `catalog/`, `taxonomy/`, etc.
- **Legacy stack:** no services from `legacy/docker-compose.yml` in root compose
- **Redis, LangGraph Server/CLI, Pydantic V1**

### Architecture compliance

| Decision | Binding rule for this story |
|----------|------------------------------|
| **AD-16** | One image, separate `api` and `worker` roles; no Redis |
| **AD-23** | Alembic owns `public` schema; vendor schemas via migrate only |
| **AD-27** | CPython 3.14.6 + uv 0.12.1; Linux CI against PostgreSQL **18.4** is compatibility authority |
| **AD-29** | Role commands + bootstrap order; devcontainer/CI parity; volume at `/var/lib/postgresql` |
| **AD-31** | Integration tests against disposable PostgreSQL 18.4; PROC tests for role commands |
| **AD-32** | Local/internal only — no public deployment |
| **NFR14** | Phoenix 30-day retention, telemetry disabled |
| **NFR17** | Pin `postgres:18.4` and `arizephoenix/phoenix:version-19.11.1` — no floating tags |
| **NFR18** | Same role commands + PG image in devcontainer and CI |
| **NFR19** | Bootstrap order in `migrate` role |

### Target file layout (new/changed)

```text
docker-compose.yml                    # NEW — root stack only
docker/postgres/init/01-roles.sql     # NEW — GATE-02
backend/Dockerfile                    # NEW
backend/alembic.ini                   # NEW
backend/migrations/env.py             # NEW (was .gitkeep only)
backend/migrations/versions/          # NEW — minimal initial revision OK
backend/src/pricecomp/platform/
  cli.py                              # NEW — pricecomp entrypoint
  roles/
    api.py                            # NEW — uvicorn + /health on 3020
    worker.py                         # NEW — blocking stub
    migrate.py                        # NEW — NFR19 orchestrator
backend/tests/conftest.py             # NEW — disposable DB fixture
backend/tests/integration/            # bootstrap, privilege, compose tests
backend/tests/domain/test_compose_manifest.py  # NEW — 1.2-UNIT-001 static parse
.devcontainer/devcontainer.json       # NEW
.github/workflows/backend.yml         # NEW
```

Keep platform adapters under `pricecomp.platform` — domain packages stay import-clean (AD-10 / NFR2).

### Compose contract (exact)

```yaml
# postgres service (binding)
image: postgres:18.4
ports: ["3021:5432"]
volumes:
  - postgres_data:/var/lib/postgresql
  - ./docker/postgres/init:/docker-entrypoint-initdb.d:ro

# phoenix service (binding)
image: arizephoenix/phoenix:version-19.11.1
ports: ["3022:6006"]
environment:
  PHOENIX_SQL_DATABASE_URL: postgresql://pricecomp_phoenix:<secret>@postgres:5432/pricecomp_phoenix
  PHOENIX_DEFAULT_RETENTION_POLICY_DAYS: "30"
  PHOENIX_TELEMETRY_ENABLED: "false"
depends_on:
  postgres:
    condition: service_healthy
```

**Forbidden in root compose:** any path under `legacy/`, port `5532`, `pricecomp_db`, legacy init scripts, shared volumes with legacy stack.

### Role command contract

```bash
pricecomp migrate   # one-shot bootstrap → exit 0
pricecomp api       # uvicorn 0.0.0.0:3020 — /health + /ready
pricecomp worker    # long-running; blocks until SIGTERM
```

Runtime `DATABASE_URL` for api/worker (host dev example):

```text
postgresql://pricecomp_app:<password>@localhost:3021/pricecomp_app
```

Migrate uses elevated URL on compose network only (e.g. `postgresql://postgres:...@postgres:5432/pricecomp_app`) — **never** inject into api/worker service env.

### Bootstrap implementation guide (`migrate` role)

Execute sequentially; each step must tolerate re-run:

1. **DB/roles ready** — wait for Postgres healthy; verify `pricecomp_app` / `pricecomp_phoenix` exist (init scripts create them)
2. **Alembic** — `alembic upgrade head` on `public` (empty revision OK)
3. **PgQueuer** — install/upgrade `pgqueuer` schema via library API or CLI
4. **LangGraph checkpointer** — `AsyncPostgresSaver.from_conn_string(...).setup()` targeting `langgraph` schema
5. **Phoenix readiness** — ensure `pricecomp_phoenix` reachable; Phoenix container performs its own schema migration on startup
6. **Readiness** — optional sanity query against `alembic_version` + vendor schema existence

Use async Psycopg 3 + SQLAlchemy 2 patterns already pinned in lockfile.

### Phoenix settings

Per architecture review (`review-operations-cutover.md` / `review-technology-currency.md`):

| Env var | Value |
|---------|-------|
| `PHOENIX_DEFAULT_RETENTION_POLICY_DAYS` | `30` |
| `PHOENIX_TELEMETRY_ENABLED` | `false` |

AC #5 may be satisfied by compose env vars **and** verified via integration test after first startup.

### Test design mapping (Epic 1)

Hard blocker **TECH-002** must close before merge. P0 scenarios:

| ID | Level | Focus |
|----|-------|-------|
| 1.2-PROC-001/002/003 | PROC | Role independence |
| 1.2-INT-001/002 | INT | Bootstrap order + idempotence |
| 1.2-INT-003/004 | INT | GATE-02 negative privilege tests |
| 1.2-UNIT-001 | UNIT | Zero legacy references in compose |

Full matrix: `_bmad-output/test-artifacts/test-design-progress.md` § Story 1.2.

**Post-merge spike (not this story):** GATE-03 PgQueuer proof (`test_pgqueuer_reliance.py`) before Story 1.4.

### Dependency note (TC-R1)

Architecture pins `opentelemetry-exporter-otlp-proto-http==1.44.0` but Story 1.1 lockfile omitted it (deferred). **Optional for 1.2** unless implementing telemetry export — do not block bootstrap on OTel wiring.

### Anti-patterns to avoid

- Using `postgres:18-alpine` floating tag (legacy uses it; new stack must pin **18.4**)
- Putting legacy Postgres or `pricecomp_db` in root compose
- Sharing migrate/superuser credentials with api/worker
- Implementing domain import, queue handlers, or advisory lock (wrong story)
- Adding Redis, Celery, or LangGraph Server
- "Hello world" business endpoints — `/health` and `/ready` only
- Skipping idempotent re-run test (OPS-001 risk)
- Putting FastAPI/SQLAlchemy imports in domain packages (AD-10)

### Git intelligence

Recent commits to build on:

- `ae142e5` — Story 1.1 review patches + done
- `1e29bd0` — Python monolith seed + lockfile
- `a1c1463` — legacy relocation pattern for compose path references

Reuse Story 1.1 patterns: `uv 0.12.1`, `.python-version=3.14.6`, src layout, test dir boundaries.

### Project context

No `project-context.md` yet. Authoritative sources: this story + GATE-01 + GATE-02 + Architecture AD-29 + test-design Epic 1.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1 / Story 1.2]
- [Source: `_bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md`]
- [Source: `_bmad-output/implementation-artifacts/gates/GATE-02-db-privileges.md`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-pricecomp-2026-07-31/ARCHITECTURE-SPINE.md` — AD-16, AD-23, AD-27, AD-29, AD-31, Stack table]
- [Source: `_bmad-output/planning-artifacts/architecture/.../reviews/review-operations-cutover.md` — Postgres 18.4 volume path, Phoenix env vars]
- [Source: `_bmad-output/test-artifacts/test-design-epic-1.md` — TECH-002, Story 1.2 coverage]
- [Source: `_bmad-output/test-artifacts/test-design-progress.md` — 1.2-* scenario IDs]
- [Source: `_bmad-output/implementation-artifacts/1-1-relocate-legacy-typescript-and-seed-the-python-monolith.md` — predecessor learnings]
- [Source: `legacy/docker-compose.yml` — **anti-pattern reference only** (floating tag, legacy ports)]

## Dev Agent Record

### Agent Model Used

Composer

### Debug Log References

- PgQueuer CLI `--pg-dsn` is a global option (before subcommand); switched to Python API for idempotent install/upgrade.
- Init SQL `\c` meta-commands work under Docker `psql -f`; testcontainers use programmatic `bootstrap_gate02_roles()`.

### Completion Notes List

- Delivered root `docker-compose.yml` (Postgres 18.4 @ 3021, Phoenix 19.11.1 @ 3022, optional api/worker/migrate profiles).
- Added `pricecomp {api,worker,migrate}` CLI with NFR19 bootstrap order (Alembic → PgQueuer → LangGraph → Phoenix readiness).
- GATE-02 init SQL + post-migrate vendor schema grants; migrate creds isolated from api/worker.
- Closed TECH-002: testcontainers PostgreSQL 18.4 fixture, PROC harness, 23 passing tests.
- Updated READMEs, devcontainer, CI workflow; GATE-01/02 checklists ticked.

### File List

- `docker-compose.yml`
- `docker/postgres/init/01-roles.sql`
- `.devcontainer/devcontainer.json`
- `.github/workflows/backend.yml`
- `backend/Dockerfile`
- `backend/alembic.ini`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/README.md`
- `backend/migrations/env.py`
- `backend/migrations/versions/001_initial.py`
- `backend/src/pricecomp/platform/cli.py`
- `backend/src/pricecomp/platform/roles/__init__.py`
- `backend/src/pricecomp/platform/roles/api.py`
- `backend/src/pricecomp/platform/roles/worker.py`
- `backend/src/pricecomp/platform/roles/migrate.py`
- `backend/tests/conftest.py`
- `backend/tests/domain/test_compose_manifest.py`
- `backend/tests/domain/test_parity.py`
- `backend/tests/integration/test_bootstrap.py`
- `backend/tests/integration/test_compose_topology.py`
- `backend/tests/integration/test_privileges.py`
- `backend/tests/integration/test_role_commands.py`
- `README.md`
- `_bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md`
- `_bmad-output/implementation-artifacts/gates/GATE-02-db-privileges.md`

### Change Log

- 2026-08-01: Story 1.2 — operational shell (Compose, role commands, bootstrap, tests, CI, devcontainer).
