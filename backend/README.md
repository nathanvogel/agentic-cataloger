# pricecomp backend

Python monolith — operational shell (Story 1.2).

## Toolchain

- **CPython** 3.14.6 (non-free-threaded — not `3.14t`)
- **uv** 0.12.1 (required for lock generation / sync)
- **pytest** 9.1.1 + integration harness (testcontainers PostgreSQL 18.4)

```bash
cd backend
uv sync
uv run pytest
```

## Role commands

Same entrypoints in local dev, Docker, devcontainer, and CI:

```bash
pricecomp migrate   # one-shot bootstrap (Alembic + PgQueuer + LangGraph schemas)
pricecomp api       # FastAPI on 0.0.0.0:3020 — /health and /ready
pricecomp worker    # long-running stub (advisory lock in Story 1.3)
```

### Environment variables

| Variable | Used by | Example |
|----------|---------|---------|
| `DATABASE_URL` | `api`, `worker` | `postgresql://pricecomp_app:pricecomp_app_dev@localhost:3021/pricecomp_app` |
| `MIGRATE_DATABASE_URL` | `migrate` only | `postgresql://postgres:postgres@localhost:3021/pricecomp_app` |
| `PHOENIX_DATABASE_URL` | `migrate` when Phoenix is running | `postgresql://pricecomp_phoenix:...@localhost:3021/pricecomp_phoenix` |
| `PHOENIX_HOST` | `migrate` when Phoenix is running | `phoenix` (compose network) or `localhost` |

Phoenix readiness steps in `migrate` run **only when `PHOENIX_HOST` is set** (root Compose `migrate` profile or devcontainer). CI runs migrate against Postgres alone and intentionally skips Phoenix waits.

**Never** inject `MIGRATE_DATABASE_URL` into `api` or `worker` — elevated credentials are migrate-only (GATE-02).

## Local stack (with root Compose)

From repo root:

```bash
docker compose up -d postgres phoenix
cd backend
export MIGRATE_DATABASE_URL=postgresql://postgres:postgres@localhost:3021/pricecomp_app
uv run pricecomp migrate
export DATABASE_URL=postgresql://pricecomp_app:pricecomp_app_dev@localhost:3021/pricecomp_app
uv run pricecomp api
```

Or build and run API via Compose profile (run migrate once on a fresh volume first):

```bash
docker compose --profile roles run --rm migrate
docker compose --profile api up -d
```

## Ports (GATE-01)

| Port | Service |
|------|---------|
| **3020** | Python API |
| **3021** | PostgreSQL 18.4 (`pricecomp_app`, `pricecomp_phoenix`) |
| **3022** | Phoenix UI |
