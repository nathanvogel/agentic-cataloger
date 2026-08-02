# Deferred Work

## Deferred from: code review of 1-1-relocate-legacy-typescript-and-seed-the-python-monolith (2026-08-01)

- Legacy `.kiro/` and `README-TESTS.md` still use bare `docker-compose up` — reference docs outside Story 1.1 scope
- `langgraph-checkpoint` resolved transitively (4.1.1) without direct NFR17 pin — revisit when wiring checkpointer
- Importer lacks explicit missing-data-dir guard — reference-stack hardening not required for this story
- Structural tests omit `pyproject.toml` / `uv.lock` / module-file retrieval checks — optional hardening beyond AC
- No CI gate for `uv run pytest` — story explicitly exempts full test-suite gating at this stage

## Deferred from: code review of 1-2-run-the-stack-locally-with-role-commands (2026-08-01)

- Bootstrap order not asserted in tests — integration tests verify outcomes but not step sequencing
- No positive vendor-schema grant verification — INT-008 only tests DDL denial, not USE/EXECUTE grants
- GATE-02 init SQL duplicated in conftest vs `docker/postgres/init/01-roles.sql` — drift risk
- No `.dockerignore` for backend image — local artifacts may bloat builds
- Alembic subprocess has no timeout — migrate can hang indefinitely on lock
- No concurrent-migrate advisory lock — parallel bootstrap could corrupt schemas
- CI init SQL not idempotent on local re-run — `psql -f 01-roles.sql` fails if roles exist
- postCreate installs Claude via remote curl — supply-chain / silent-failure risk in dev bootstrap
- Phoenix service has no healthcheck — migrate only waits for `service_started`
- Parity test doesn't verify devcontainer role invocation — only image tags and CI script substrings

## Deferred from: code review of 1-2a-prove-pgqueuer-completion-reliance (2026-08-01)

- External Postgres bootstrap assumption — `ExternalPostgres` path yields without `_run_init_sql`; compose/CI Postgres assumed pre-provisioned
- P5 handler path limited resume proof — direct LangGraph test covers P5 intent; handler-path smoke test does not prove crash/restart resume on `pipeline_run_id`
- P4 redrive vs worker respawn — after SIGKILL, recovery uses `redrive_from_owner_row` + in-process drain rather than respawning the worker subprocess (AD-22 re-drive pattern)
- migrate privilege fix untested — `_grant_vendor_schema_privileges` SQL fix has no test asserting default-privilege grants apply
- backend-test.sh redundant suite run — full integration suite plus explicit `test_pgqueuer_reliance.py` re-run adds CI time without coverage append
