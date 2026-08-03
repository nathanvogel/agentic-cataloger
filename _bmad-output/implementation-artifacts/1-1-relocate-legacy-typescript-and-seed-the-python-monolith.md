---
baseline_commit: 3a8353dd047b37244fcae47d7319bd0618014fe5
---

# Story 1.1: Relocate Legacy TypeScript and Seed the Python Monolith

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As an operator,
I want the legacy TypeScript stack moved under `/legacy` and `/backend` reseeded as the Python monolith root,
so that Python implementation can begin against the architecture's structural seed without legacy code obstructing the active tree.

**Gate:** [`GATE-01-bootstrap.md`](gates/GATE-01-bootstrap.md)

## Acceptance Criteria

1. **Relocation manifest (GATE-01)**
   - **Given** the repository before / after relocation
   - **When** the relocation change is applied per GATE-01
   - **Then** these paths exist: `legacy/backend/`, `legacy/data-importer/`, `legacy/db/`, `legacy/.kiro/`, `legacy/docker-compose.yml`, `legacy/docs/decision_records/ADR001-llm-library-selection.md`
   - **And** `data/` and `frontend/` remain at the repo root
   - **And** `sync-ai-rules.sh` and `.cursor/rules/` are absent
   - **And** Husky `pre-commit` runs `cd frontend && yarn lint-staged` only

2. **Legacy is reference-only**
   - **Given** the relocation has been applied
   - **When** the change is reviewed
   - **Then** there is **no** requirement to pass legacy build or test from CI or this story
   - **And** active ports follow GATE-01: API **3020**, Postgres **3021**, Phoenix **3022**, frontend **3023**; legacy frozen at **3010** / **5532**

3. **Python structural seed (AD-28)**
   - **Given** the relocated repository
   - **When** `backend/` is seeded per AD-28
   - **Then** it contains `pyproject.toml`, `uv.lock`, and `src/agentic_cataloger/` with empty-but-present packages: `contracts/`, `catalog/`, `taxonomy/`, `enrichment/`, `review/`, `pipeline/`, `comparison/`, `evaluation/`, `platform/`
   - **And** `migrations/` and `tests/domain/`, `tests/integration/`, `tests/contract/`, `tests/evals/` exist
   - **And** no Python domain logic is included — structural seed only

4. **Docs + reversibility**
   - **Given** the relocation and seed change
   - **When** it is reviewed against GATE-01
   - **Then** root documentation references the new layout (`backend/` Python seed + `legacy/` reference stack)
   - **And** the relocation is demonstrably reversible by inverting the moves (git history / documented inverse moves)

5. **Pinned toolchain resolves**
   - **Given** the pinned toolchain
   - **When** `uv sync` runs on the committed lockfile (uv **0.12.1**)
   - **Then** it resolves against non-free-threaded CPython **3.14.6**
   - **And** LangGraph Server/CLI extras and Pydantic V1 models are absent from the resolved set

## Tasks / Subtasks

- [x] **Verify relocation already landed** (AC: #1, #2) — commit `a1c1463`
  - [x] Confirm all GATE-01 relocation paths exist under `legacy/`
  - [x] Confirm `data/` and `frontend/` at root; root `backend/` absent until seed
  - [x] Confirm `sync-ai-rules.sh` and `.cursor/rules/` are gone
  - [x] Confirm `.husky/pre-commit` is frontend lint-staged only
  - [x] Do **not** re-do the move; only fix remaining debt below

- [x] **Fix post-relocation path debt** (AC: #1, #4; AD-27 “fixes its paths/scripts”)
  - [x] Fix `legacy/data-importer` catalog data path so it resolves to repo-root `data/` (current `../../data` from `src/` points at `legacy/data`)
  - [x] Update `legacy/data-importer/README.md` compose invocation to `docker compose -f legacy/docker-compose.yml …` when run from repo root
  - [x] Update `.gitattributes` LFS globs from `db/**` → `legacy/db/**` (keep old globs only if still needed for history)
  - [x] Extend root `.gitignore` for Python (`.venv/`, `__pycache__/`, `.ruff_cache/`, `.pytest_cache/`, `*.egg-info/`, etc.)

- [x] **Seed `backend/` structural tree** (AC: #3)
  - [x] Create `backend/src/agentic_cataloger/` with the nine empty packages (each `__init__.py` only — no domain modules)
  - [x] Create `backend/migrations/` (empty Alembic home; minimal placeholder OK — **no** migration revisions or `env.py` domain wiring required beyond “folder exists”; full Alembic wire-up is Story 1.2+)
  - [x] Create `backend/tests/{domain,integration,contract,evals}/` (placeholders / `.gitkeep` / empty `__init__` as needed so dirs are tracked)
  - [x] **Do not** create a `retrieval/` package (AD-35 retired)
  - [x] **Do not** add FastAPI app, CLI entrypoints, worker loop, Dockerfile, or root `docker-compose.yml` (Story **1.2**)

- [x] **Commit `pyproject.toml` + `uv.lock`** (AC: #5; NFR17)
  - [x] Pin toolchain: `requires-python` targeting **3.14.6**; document/require **uv 0.12.1** for lock generation
  - [x] Prefer `.python-version` = `3.14.6` (or equivalent uv pin) so `uv sync` selects non-free-threaded CPython 3.14.6 — **not** `3.14t` / free-threaded
  - [x] Declare NFR17 runtime pins in dependencies (even if unused yet) so the lockfile is the compatibility authority from day one:
    - LangGraph 1.2.10, langgraph-checkpoint-postgres 3.1.1, PgQueuer 1.3.2
    - SQLAlchemy[asyncio] 2.0.51, Alembic 1.18.5, Psycopg[binary] 3.3.4, psycopg-pool 3.3.1
    - FastAPI 0.141.1, FastMCP 3.4.5, Uvicorn 0.52.0
    - langchain-core 1.5.3, langchain-openai 1.4.1, langchain-anthropic 1.5.3
    - Pydantic 2.13.4 (V2 only)
    - OTel API/SDK 1.44.0, OpenInference LangChain 0.1.68
  - [x] Exclude LangGraph **Server/CLI** extras from dependency specs
  - [x] Exclude any Pydantic V1 / `pydantic.v1` application model usage (none should appear)
  - [x] Run `uv sync` with uv 0.12.1 and commit the resulting `uv.lock`
  - [x] Package layout: src layout (`backend/src/agentic_cataloger`); project name / import package `agentic-cataloger`

- [x] **Update root documentation** (AC: #4)
  - [x] Update root `README.md` project structure: active `frontend/` + `data/`, new `backend/` Python seed, `legacy/` reference-only
  - [x] Document `cd backend && uv sync` (and Python/uv pins)
  - [x] Keep legacy compose instructions under an explicit “legacy reference” section (ports 5532 / 3010)
  - [x] Point at GATE-01 port map for the active stack (`3020+n`) — note that root Compose arrives in Story 1.2
  - [x] Optionally refresh `legacy/README.md` if path notes drift

- [x] **GATE-01 checklist evidence** (AC: #1–#5)
  - [x] Tick relocation + `backend/` structural seed items in `gates/GATE-01-bootstrap.md` when done
  - [x] Leave Compose / API-listen checklist items for Story 1.2 unless already true

## Dev Notes

### Current repo state (do not reinvent)

Relocation **already shipped** in `a1c1463` (*chore: move TypeScript stack to legacy/ and free /backend for Python*):

| Expected | On disk now |
|----------|-------------|
| `legacy/backend`, `data-importer`, `db`, `.kiro`, `docker-compose.yml`, ADR001 | Present |
| `data/`, `frontend/` at root | Present |
| `sync-ai-rules.sh`, `.cursor/rules/` removed | Absent |
| Husky → frontend lint-staged | Done |
| Root `backend/` Python seed | **Missing — primary remaining work** |
| Root `docker-compose.yml` | Missing — **Story 1.2**, not this story |

Treat this story as: **verify relocation + fix path debt + seed Python + docs + lockfile**.

### Scope boundaries (hard)

**In scope:** relocation verification, path/script fixes for legacy after move, AD-28 empty package tree, `pyproject.toml`/`uv.lock`, root docs, `.gitignore`/`.gitattributes`, GATE-01 ticks for relocation+seed.

**Out of scope (Story 1.2+):**
- Root `docker-compose.yml` (Postgres 3021 + Phoenix 3022)
- Backend Dockerfile / `api` | `worker` | `migrate` role commands
- FastAPI routes, FastMCP mount, CLI, worker, Alembic env against real DB
- GATE-02 DB privilege bootstrap, PgQueuer, LangGraph checkpointer
- Any domain logic, repositories, commands, or schema

**Never in this initiative’s groundwork:** `retrieval/` package / pgvector (AD-35 retired); kill-pile morphs (AD-33) — no scaffolding that implies full taxonomy dumps, blocking HITL, same-call assign+create, silent merge, etc.

### Architecture compliance

| Decision | Binding rule for this story |
|----------|------------------------------|
| **AD-1** | One Python monolith owns agent/REST/MCP/import; TS is not an active second backend |
| **AD-27** | CPython **3.14.6** (non-free-threaded) + uv **0.12.1**; committed `pyproject.toml` + `uv.lock`; Yarn only for frontend + legacy TS; relocate+fix paths+docs **before** Python implementation |
| **AD-28** | `/backend` = permanent Python root; TS under `/legacy`; no `backend-v2` / tech-suffixed permanent paths |
| **AD-23** | Alembic owns app migrations later — seed the `migrations/` folder now only |
| **AD-29** | Role commands / one image — **Story 1.2**; GATE-01 supersedes older “legacy API in root Compose” wording: root Compose is **new stack only** |
| **AD-31** | Seed test directory boundaries: `domain` / `integration` / `contract` / `evals` |
| **AD-35** | No `retrieval` package |

GATE-01 supersedes any older review asking for legacy build/test evidence after relocate — **reference-only until parity**.

### Structural seed (exact)

```text
backend/
  pyproject.toml
  uv.lock
  .python-version          # recommended: 3.14.6
  src/agentic_cataloger/
    __init__.py
    contracts/             # framework-free contracts (empty)
    catalog/
    taxonomy/
    enrichment/
    review/
    pipeline/
    comparison/
    evaluation/
    platform/              # future REST/MCP/CLI/persistence adapters — empty now
  migrations/              # Alembic home — empty / placeholder only
  tests/
    domain/
    integration/
    contract/
    evals/
```

Package comments in architecture are guidance for *future* ownership — do not implement behavior now.

### Tooling notes

- **uv** is the only Python package manager (AD-27). Do not introduce Poetry/pip-tools/Yarn wrappers for Python.
- **Ruff / basedpyright / pytest** are **not** named in GATE-01 / AD-27 / Story 1.1 ACs. Optional minimal tool config in `pyproject.toml` is fine if it helps; do not block the story on a full lint/type/test suite. Test **directories** must exist; passing domain tests are not required for empty seed.
- Generate the lockfile with **uv 0.12.1** so AC #5 is literally true. Prefer `uv python install 3.14.6` then `uv sync`.
- Avoid free-threaded interpreter selection (`3.14t` / `+freethreaded`); architecture binds non-free-threaded CPython 3.14.6.

### Port map (document; do not wire services yet)

| Port | Service |
|------|---------|
| 3020 | Python API (Story 1.2) |
| 3021 | New Postgres |
| 3022 | Phoenix |
| 3023 | Frontend Vite (already configured) |
| 3010 / 5532 | Legacy API / legacy Postgres (frozen) |

### Anti-patterns to avoid

- Recreating NestJS under root `backend/`
- Implementing “hello world” FastAPI just to feel productive — violates “no domain logic / structural seed only”
- Adding Redis, LangGraph Server, or a second package manager
- Putting NFR17 deps only in comments without locking them
- Leaving `legacy/data-importer` pointed at the wrong `data/` directory
- Creating root Compose “early” and mixing legacy DB env into it (GATE-01 forbids)

### Git intelligence

Recent relevant commits:
- `a1c1463` — relocation (primary predecessor)
- `5069b1d` — IR + GATE-01…04 bound
- `3a8353d` — sprint-status.yaml

Reuse patterns from `a1c1463` for any remaining path fixes; do not invent a second relocation scheme.

### Project context

No `project-context.md` exists yet. Prefer this story file + GATE-01 + Architecture §Structural Seed / AD-27 / AD-28.

### References

- [Source: `_bmad-output/planning-artifacts/epics.md` — Epic 1 / Story 1.1]
- [Source: `_bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md`]
- [Source: `_bmad-output/planning-artifacts/architecture/architecture-agentic-cataloger-2026-07-31/ARCHITECTURE-SPINE.md` — AD-27, AD-28, §Structural Seed, §Stack]
- [Source: `_bmad-output/planning-artifacts/epics.md` — NFR17]
- [Source: `_bmad-output/planning-artifacts/implementation-readiness-report-2026-08-01.md` — Epic 1 / GATE-01]
- [Source: commit `a1c1463`]

## Dev Agent Record

### Agent Model Used

Cursor Grok 4.5

### Debug Log References

- uv install: astral.sh installer 403'd; installed uv **0.12.1** from GitHub release tarball `uv-aarch64-apple-darwin.tar.gz`
- `uv python install 3.14.6` + `uv sync` resolved 100 packages in `uv.lock`; non-free-threaded interpreter confirmed (`abiflags` empty / GIL path)

### Implementation Plan

1. Verify relocation from `a1c1463` (no re-move).
2. Fix legacy path debt (data-importer default dir, compose docs, LFS globs, Python gitignore).
3. Seed AD-28 empty package tree + migrations/tests dirs.
4. Pin NFR17 deps in `pyproject.toml`, lock with uv 0.12.1.
5. Update root + legacy docs; tick GATE-01 relocation/seed checklist items.

### Completion Notes List

- Relocation already present; verified GATE-01 paths, husky, and absent sync-ai-rules / `.cursor/rules`.
- Fixed `legacy/data-importer` default `--data-dir` from `../../data` → `../../../data` (repo-root `data/`).
- Seeded `backend/` with nine empty packages (no `retrieval/`), `migrations/`, test dir boundaries, `pyproject.toml` + `uv.lock` + `.python-version=3.14.6`.
- `uv sync` with uv 0.12.1 selects CPython 3.14.6; no LangGraph Server/CLI packages; Pydantic 2.13.4 only.
- Structural seed smoke tests: `backend/tests/domain/test_structural_seed.py` (3 passed).
- GATE-01: relocation + structural seed ticked; Compose/API-listen left for Story 1.2.
- Root README documents active layout, `uv sync`, GATE-01 ports, and legacy reference section.

### File List

- `.gitattributes`
- `.gitignore`
- `README.md`
- `backend/.python-version`
- `backend/README.md`
- `backend/pyproject.toml`
- `backend/uv.lock`
- `backend/migrations/.gitkeep`
- `backend/src/agentic_cataloger/__init__.py`
- `backend/src/agentic_cataloger/catalog/__init__.py`
- `backend/src/agentic_cataloger/comparison/__init__.py`
- `backend/src/agentic_cataloger/contracts/__init__.py`
- `backend/src/agentic_cataloger/enrichment/__init__.py`
- `backend/src/agentic_cataloger/evaluation/__init__.py`
- `backend/src/agentic_cataloger/pipeline/__init__.py`
- `backend/src/agentic_cataloger/platform/__init__.py`
- `backend/src/agentic_cataloger/review/__init__.py`
- `backend/src/agentic_cataloger/taxonomy/__init__.py`
- `backend/tests/__init__.py`
- `backend/tests/contract/.gitkeep`
- `backend/tests/domain/test_structural_seed.py`
- `backend/tests/evals/.gitkeep`
- `backend/tests/integration/.gitkeep`
- `legacy/README.md`
- `legacy/data-importer/README.md`
- `legacy/data-importer/src/import.ts`
- `_bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/1-1-relocate-legacy-typescript-and-seed-the-python-monolith.md`

### Review Findings

- [x] [Review][Patch] `test-file-scanner.ts` still points at `../data` (legacy/data) [`legacy/data-importer/test-file-scanner.ts:6`]
- [x] [Review][Patch] GATE-01 frontend port 3023 checkbox unticked though `frontend/vite.config.ts` already binds 3023 [`_bmad-output/implementation-artifacts/gates/GATE-01-bootstrap.md:75`]
- [x] [Review][Patch] data-importer README `--data-dir ../../../data` example is cwd-sensitive [`legacy/data-importer/README.md:71`]
- [x] [Review][Patch] data-importer README default-path note says "from `src/`" but CLI resolves from compiled `dist/` [`legacy/data-importer/README.md:78`]
- [x] [Review][Patch] `legacy/README.md` reversibility note omits warning about overwriting Python `backend/` seed [`legacy/README.md:14`]
- [x] [Review][Patch] Root `.gitignore` duplicates `dist/` entry [`.gitignore:2,18`]
- [x] [Review][Patch] Root `README.md` omits `uv run pytest` / pointer to `backend/README.md` [`README.md:31-36`]
- [x] [Review][Patch] Completion notes say "128 packages" but lockfile resolves more [`1-1-relocate-legacy-typescript-and-seed-the-python-monolith.md:231`]
- [x] [Review][Patch] Add `venv/` alongside `.venv/` in Python gitignore block [`.gitignore:8`]
- [x] [Review][Patch] data-importer README should note `yarn build` after path changes (stale `dist/` footgun) [`legacy/data-importer/README.md:28-32`]

- [x] [Review][Defer] Legacy `.kiro/` and `README-TESTS.md` still use bare `docker-compose up` — deferred, pre-existing reference docs outside Story 1.1 scope
- [x] [Review][Defer] `langgraph-checkpoint` resolved transitively (4.1.1) without direct NFR17 pin — deferred, acceptable for structural seed; revisit when wiring checkpointer
- [x] [Review][Defer] Importer lacks explicit missing-data-dir guard — deferred, reference-stack hardening not required for this story
- [x] [Review][Defer] Structural tests omit `pyproject.toml` / `uv.lock` / module-file retrieval checks — deferred, optional hardening beyond AC
- [x] [Review][Defer] No CI gate for `uv run pytest` — deferred, story explicitly exempts full test-suite gating at this stage

### Change Log

- 2026-08-01: Story 1.1 implemented — verified relocation, fixed legacy path debt, seeded Python monolith + NFR17 lockfile, updated docs, GATE-01 relocation/seed evidence.
- 2026-08-01: Code review — ACCEPT with 10 patch items, 5 deferred, 8 dismissed.
- 2026-08-01: Code review patches applied — all 10 patch findings resolved.
