# agentic-cataloger

A multi-stage LLM agent that builds a product category tree and assigns SKUs to it. LangGraph, per-stage evals in Phoenix, and a defer-to-human queue. Running against a 30k-row dataset of Swiss grocery products (Migros, Lidl, Coop, Denner).

## Prerequisites

- Docker & Docker Compose
- **Dev Containers** extension (VS Code / Cursor)
- **Python backend:** CPython **3.14.6** (non-free-threaded) via **uv 0.12.1** (installed in the devcontainer image)
- **Frontend / legacy TS:** Node.js v25+ with Corepack and Yarn 4.11.0+ (installed in the devcontainer image)


## Active stack layout

| Path | Role |
|------|------|
| `backend/` | Python monolith (API, worker, migrate roles) |
| `frontend/` | UI (active; Vite on port **3023**) |
| `data/` | Catalog CSVs (active) |
| `legacy/` | Relocated TypeScript stack — **reference until parity** |

| Port | Service |
|------|---------|
| **3020** | Python API (`agentic-cataloger api`) |
| **3021** | New Postgres |
| **3022** | Phoenix |
| **3023** | Frontend Vite |

Root `docker-compose.yml` backs the devcontainer (Postgres, Phoenix, API). Bound gate checklists: [`_bmad-output/implementation-artifacts/gates/`](_bmad-output/implementation-artifacts/gates/).

## Quick start

Open the repo with **Dev Containers** (`.devcontainer/`). Compose starts Postgres, Phoenix, and the API; `postCreate` runs `uv sync` and migrates the DB when Postgres is healthy.

```bash
cd backend

# Only needed if postCreate skipped migrate (postgres wasn't up yet)
export MIGRATE_DATABASE_URL=postgresql://postgres:postgres@postgres:5432/agentic_cataloger_app
uv run agentic-cataloger migrate

# Catalog ingest (latest CSV per retailer under data/)
uv run agentic-cataloger ingest

# API is already running on port 3020 (devcontainer api service)
curl http://localhost:3020/health
```

`DATABASE_URL` is preset in the API devcontainer (`@postgres:5432` on the docker compose network). `MIGRATE_DATABASE_URL` is not as the API service must not have superuser access. 

## Frontend setup

`postCreate` installs frontend deps. To refresh manually:

```bash
cd frontend
yarn install
```

## Python backend

See [`backend/README.md`](backend/README.md) for role commands, env vars, lint/typecheck, and tests.

```bash
cd backend
uv run pytest

# format + lint + types (also via pre-commit)
../scripts/ci/backend-lint.sh
```

## Devcontainer customization

For personal shell (zsh, Spaceship, aliases), push a private `dotfiles` repo to GitHub and add these VS Code / Cursor / <your-ide> **User** settings:

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
