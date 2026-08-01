# Legacy (reference only)

TypeScript NestJS backend, data importer, database scripts, and Kiro steering docs from the pre–Python-monolith stack.

Kept for reference until the new Python backend reaches parity. Not maintained or required to build/run at the repo root.

- `backend/` — NestJS API and CLI
- `data-importer/` — CSV import to PostgreSQL
- `db/` — Docker init SQL and migrations
- `docker-compose.yml` — legacy Postgres service (`docker compose -f legacy/docker-compose.yml …` from repo root, or `docker compose …` from `legacy/`)
- `.kiro/` — former steering and specs
- `docs/decision_records/` — ADR001 and related
