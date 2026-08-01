# Deferred Work

## Deferred from: code review of 1-1-relocate-legacy-typescript-and-seed-the-python-monolith (2026-08-01)

- Legacy `.kiro/` and `README-TESTS.md` still use bare `docker-compose up` — reference docs outside Story 1.1 scope
- `langgraph-checkpoint` resolved transitively (4.1.1) without direct NFR17 pin — revisit when wiring checkpointer
- Importer lacks explicit missing-data-dir guard — reference-stack hardening not required for this story
- Structural tests omit `pyproject.toml` / `uv.lock` / module-file retrieval checks — optional hardening beyond AC
- No CI gate for `uv run pytest` — story explicitly exempts full test-suite gating at this stage
