# GATE-01: Bootstrap acceptance

**Status:** bound (2026-08-01)  
**Blocks:** Story 1.1 (relocation + Python seed), Story 1.2 (compose + roles)  
**Evidence location:** Story PR + this checklist ticked at merge

## Port map (binding)

**Rule:** active stack host ports are **`3020 + n`** for sequential `n` starting at 0. Container internal ports stay conventional (5432, 6006, etc.).

| n | Port | Service | Notes |
|---|------|---------|-------|
| 0 | **3020** | Python API | `pricecomp api` |
| 1 | **3021** | PostgreSQL (new stack) | host → container `5432`; DBs `pricecomp_app`, `pricecomp_phoenix` |
| 2 | **3022** | Phoenix UI | host → container `6006` |
| 3 | **3023** | Frontend dev | `frontend/` Vite server |

`worker` and `migrate` process roles expose **no** host port.

**Legacy (reference only — not part of `3020+n`):**

| Port | Service |
|------|---------|
| 5532 | Postgres in `legacy/docker-compose.yml` (`pricecomp_db`) |
| 3010 | Legacy NestJS API (`legacy/backend`) — frozen reference port |

## Repository layout (binding)

| Path | Role |
|------|------|
| `backend/` | Python monolith root (Story 1.1 seeds; empty packages only) |
| `frontend/` | UI (active) |
| `data/` | Catalog CSVs (active) |
| `legacy/` | Relocated TypeScript stack — **reference until parity** |
| `docker-compose.yml` | **Repo root** — new stack Postgres + Phoenix only; **no legacy services or DB refs** (Story 1.2) |
| `legacy/docker-compose.yml` | Legacy Postgres only |

## Relocation manifest (binding)

Move under `legacy/`:

- `backend/` → `legacy/backend/`
- `data-importer/` → `legacy/data-importer/`
- `db/` → `legacy/db/`
- `.kiro/` → `legacy/.kiro/`
- `docs/decision_records/ADR001-llm-library-selection.md` → `legacy/docs/decision_records/`
- `docker-compose.yml` → `legacy/docker-compose.yml` (legacy Postgres)

Keep at repo root: `data/`, `frontend/`.

Remove: `sync-ai-rules.sh`, `.cursor/rules/`.

Husky `pre-commit` → `cd frontend && yarn lint-staged`.

**No requirement** to verify legacy build/test after relocation — reference-only until parity.

## Python structural seed (binding — Story 1.1 implements)

Per AD-28, `backend/` must contain:

- `pyproject.toml`, `uv.lock`
- `src/pricecomp/{contracts,catalog,taxonomy,enrichment,review,pipeline,comparison,evaluation,platform}/`
- `migrations/`, `tests/{domain,integration,contract,evals}/`
- No domain logic in the relocation/seed PR

Toolchain: CPython **3.14.6**, uv **0.12.1**; no LangGraph Server/CLI extras; no Pydantic V1.

## Story checklist (implementation fills these)

- [x] Relocation matches manifest above
- [x] `backend/` structural seed committed
- [ ] Root `docker-compose.yml` with Postgres (**3021**) + Phoenix (**3022**)
- [ ] API role listens on **3020** when wired (Story 1.2)
- [ ] Frontend dev server on **3023**
