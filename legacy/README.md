# Legacy (reference only)

TypeScript NestJS backend, data importer, database scripts, and Kiro steering docs from the pre–Python-monolith stack.

Kept for reference until the new Python backend reaches parity. Not maintained or required to build/run at the repo root.

- `backend/` — NestJS API and CLI
- `data-importer/` — CSV import to PostgreSQL
- `db/` — Docker init SQL and migrations
- `docker-compose.yml` — legacy Postgres service (`docker compose -f legacy/docker-compose.yml …` from repo root, or `docker compose …` from `legacy/`)
- `.kiro/` — former steering and specs
- `docs/decision_records/` — ADR001 and related

**Reversibility:** the relocation landed in commit `a1c1463`. Invert by moving the same paths back to the repo root (`legacy/backend` → `backend`, etc.) and restoring removed root helpers if needed; prefer `git revert` / checkout of that commit for an exact undo. **Warning:** root `backend/` now holds the Python monolith seed — back up or remove it before restoring legacy NestJS to `backend/`.
