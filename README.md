# Swiss Grocery Price Comparison

Compare prices across Swiss supermarkets: Migros, Lidl, Coop, and Denner.

## Prerequisites

- Docker & Docker Compose
- **Python backend:** CPython **3.14.6** (non-free-threaded) + **uv 0.12.1**
- **Frontend / legacy TS:** Node.js v25+ (via nvm recommended) with Corepack (Yarn 4.11.0+)

## Active stack layout

| Path | Role |
|------|------|
| `backend/` | Python monolith root (structural seed — Story 1.1) |
| `frontend/` | UI (active; Vite on port **3023**) |
| `data/` | Catalog CSVs (active) |
| `legacy/` | Relocated TypeScript stack — **reference until parity** |

Active host ports follow GATE-01 (`3020 + n`):

| Port | Service |
|------|---------|
| **3020** | Python API (wired in Story 1.2) |
| **3021** | New Postgres |
| **3022** | Phoenix |
| **3023** | Frontend Vite |

Root `docker-compose.yml` (Postgres **3021** + Phoenix **3022**) arrives in Story **1.2**. Bound gate checklists: [`_bmad-output/implementation-artifacts/gates/`](_bmad-output/implementation-artifacts/gates/).

## Python backend setup

```bash
cd backend
uv sync   # requires uv 0.12.1; selects CPython 3.14.6 via .python-version
```

## Frontend setup

```bash
npm install -g corepack
corepack enable
cd frontend
yarn install
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
