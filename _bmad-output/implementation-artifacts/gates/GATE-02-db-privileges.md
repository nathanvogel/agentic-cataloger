# GATE-02: Database role and privilege manifest

**Status:** bound (2026-08-01)  
**Blocks:** Story 1.2 (Compose bootstrap)  
**Evidence location:** `docker/postgres/init/*.sql` + integration test proving `pricecomp_app` cannot `CREATE DATABASE`

## Two independent Postgres stacks (binding)

| Stack | Compose file | Host port | Databases | References legacy? |
|-------|--------------|-----------|-----------|-------------------|
| **New (Python)** | root `docker-compose.yml` | **3021** (`3020+1`) | `pricecomp_app`, `pricecomp_phoenix` | **No** |
| **Legacy (reference)** | `legacy/docker-compose.yml` | **5532** (frozen) | `pricecomp_db` | self-contained |

The new stack **must not** reference legacy in any form: no shared volume, no `depends_on`, no connection strings, no init scripts pointing at `legacy/db/`, no legacy database on the new Postgres instance. Legacy stays entirely in `legacy/docker-compose.yml`.

## New-stack databases and runtime roles (binding)

| Database | Runtime role | Used by |
|----------|--------------|---------|
| `pricecomp_app` | `pricecomp_app` | `api` and `worker` process roles (runtime) |
| `pricecomp_phoenix` | `pricecomp_phoenix` | Phoenix container only |

## What is the `migrate` process role?

**Not a database.** `migrate` is the third **CLI entrypoint** on the same backend image as `api` and `worker` (see AD-29):

```bash
pricecomp migrate   # one-shot: schema setup, then exit
pricecomp api       # long-running HTTP/MCP server (port 3020)
pricecomp worker    # long-running job consumer
```

`migrate` runs at bootstrap or deploy time to:

1. Apply Alembic migrations (`public` schema)
2. Install/upgrade PgQueuer (`pgqueuer` schema)
3. Set up LangGraph checkpointer tables (`langgraph` schema)

It may use elevated credentials (container `postgres` superuser or a dedicated bootstrap role). Those credentials **must not** be in `api` or `worker` environment — only in the migrate invocation.

Connection string for app runtime uses host port **3021** (e.g. `postgresql://pricecomp_app:…@localhost:3021/pricecomp_app`).

## Schemas in `pricecomp_app` (binding)

| Schema | Created by | `pricecomp_app` role may |
|--------|------------|--------------------------|
| `public` | Alembic via `migrate` | CRUD on app tables |
| `pgqueuer` | `pgq install` via `migrate` | USE + execute; not DDL |
| `langgraph` | checkpointer setup via `migrate` | USE + execute; not DDL |

Phoenix uses **`pricecomp_phoenix`** only — separate database, no cross-DB access from the app.

## Story checklist (implementation fills these)

- [x] Root compose: Postgres **3021** + Phoenix **3022**; zero legacy references
- [x] Init script at `docker/postgres/init/` creates `pricecomp_app` + `pricecomp_phoenix` only
- [x] `PHOENIX_SQL_DATABASE_URL` → `pricecomp_phoenix` (via internal `postgres:5432` in compose network)
- [x] App `DATABASE_URL` → `pricecomp_app` on host port **3021** (api/worker only)
- [x] `pricecomp migrate` documented as one-shot schema role
- [x] Test: `pricecomp_app` cannot `CREATE DATABASE`
- [x] Test: `pricecomp_app` cannot write to `pricecomp_phoenix`
