# Swiss Grocery Price Comparison

Compare prices across Swiss supermarkets: Migros, Lidl, Coop, and Denner.

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
| **3020** | Python API (`pricecomp api`) |
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
export MIGRATE_DATABASE_URL=postgresql://postgres:postgres@localhost:3021/pricecomp_app
uv sync
uv run pricecomp migrate

# API on port 3020
export DATABASE_URL=postgresql://pricecomp_app:pricecomp_app_dev@localhost:3021/pricecomp_app
uv run pricecomp api
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

For personal shell setup (zsh, aliases, etc.), use a private **`~/dotfiles`** repo and Cursor **User** settings:

```json
{
  "dotfiles.repository": "/Users/<you>/dotfiles",
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
docker exec -it pricecomp-db psql -U pricecomp_user -d pricecomp_db
```

Or any PostgreSQL client: `localhost:5532` / `pricecomp_db` / `pricecomp_user` / `abc`.

Stop:

```bash
docker compose -f legacy/docker-compose.yml down
```

See also [`legacy/README.md`](legacy/README.md).

## Project structure (steering)

Legacy Kiro notes (reference): [`legacy/.kiro/steering/structure.md`](legacy/.kiro/steering/structure.md)
