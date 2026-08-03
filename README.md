# agentic-cataloger

A multi-stage LLM agent that builds a product category tree and assigns SKUs to it. LangGraph, per-stage evals in Phoenix, and a defer-to-human queue. Running against a 30k-row dataset of Swiss grocery products (Migros, Lidl, Coop, Denner).

## Prerequisites

- Docker & Docker Compose
- **Python backend:** CPython **3.14.6** (non-free-threaded) + **uv 0.12.1**
- **Frontend / legacy TS:** Node.js v25+ (via nvm recommended) with Corepack (Yarn 4.11.0+)


## Active stack layout

| Path | Role |
|------|------|
| `backend/` | Python monolith (API, worker, migrate roles) |
| `frontend/` | UI (active; Vite on port **3023**) |
| `data/` | Catalog CSVs (active) |
| `legacy/` | Relocated TypeScript stack — **reference until parity** |

Active host ports follow GATE-01 (`3020 + n`):

| Port | Service |
|------|---------|
| **3020** | Python API (`agentic-cataloger api`) |
| **3021** | New Postgres |
| **3022** | Phoenix |
| **3023** | Frontend Vite |

Root `docker-compose.yml` provides Postgres **3021** + Phoenix **3022**. Bound gate checklists: [`_bmad-output/implementation-artifacts/gates/`](_bmad-output/implementation-artifacts/gates/).

## Quick start (new Python stack)

```bash
# Infrastructure
docker compose up -d postgres phoenix

# Bootstrap schemas (one-shot, idempotent)
cd backend
export MIGRATE_DATABASE_URL=postgresql://postgres:postgres@localhost:3021/agentic_cataloger_app
uv sync
uv run agentic-cataloger migrate

# API on port 3020
export DATABASE_URL=postgresql://agentic_cataloger_app:agentic_cataloger_app_dev@localhost:3021/agentic_cataloger_app
uv run agentic-cataloger api

# Catalog ingest (latest CSV per retailer under data/)
uv run agentic-cataloger ingest --retailer lidl
```

Compose profile alternative (`api` + `worker` built from `backend/Dockerfile`). On a **fresh volume**, bootstrap once before starting API:

```bash
docker compose --profile roles run --rm migrate
docker compose --profile api up -d
curl http://localhost:3020/health
```

## Frontend setup

```bash
npm install -g corepack
corepack enable
cd frontend
yarn install
```

## Python backend

See [`backend/README.md`](backend/README.md) for role commands, env vars, lint/typecheck, and tests.

```bash
cd backend
uv sync
uv run pytest

# format + lint + types (also via pre-commit)
./scripts/ci/backend-lint.sh
```

## Devcontainer customization

Open the repo with **Dev Containers** (`.devcontainer/`).

For personal shell (zsh, Spaceship, aliases), push a private dotfiles repo to GitHub and add VS Code / Cursor / <your-ide> **User** settings:

```json
{
  "dotfiles.repository": "<github-user>/dotfiles",
  "dotfiles.targetPath": "~/dotfiles",
  "dotfiles.installCommand": "install.sh"
}
```

## Legacy reference stack

The pre–Python NestJS backend, data importer, and DB scripts live under `legacy/`. They are **not** required to build or run for active development. Frozen ports: API **3010**, Postgres **5532**.

Start legacy Postgres (from repo root):

```bash
docker compose -f legacy/docker-compose.yml up -d
```

Wait for PostgreSQL (about 5–10 seconds):

```bash
docker compose -f legacy/docker-compose.yml logs -f postgres
```

Connect:

```bash
docker exec -it agentic-cataloger-db psql -U agentic_cataloger_user -d agentic_cataloger_db
```

Or any PostgreSQL client: `localhost:5532` / `agentic_cataloger_db` / `agentic_cataloger_user` / `abc`.

Stop:

```bash
docker compose -f legacy/docker-compose.yml down
```

See also [`legacy/README.md`](legacy/README.md).

## Project structure (steering)

Legacy Kiro notes (reference): [`legacy/.kiro/steering/structure.md`](legacy/.kiro/steering/structure.md)
