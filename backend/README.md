# pricecomp backend

Python monolith — operational shell (Story 1.2).

## Toolchain

- **CPython** (non-free-threaded, not `3.14t`)
- **uv** (required for lock generation / sync)
- **pytest** integration harness (testcontainers PostgreSQL 18.4)
- **Ruff** (format + lint) and **Pyright** (types), see [`docs/specs/code_style_python.md`](../docs/specs/code_style_python.md)

```bash
cd backend
uv sync
```

## Tests

Prefer the portable CI script from repo root when you want the full gate (unit → migrate twice → integration → live `/health` + `/ready`):

```bash
# Needs Postgres on localhost:3021 (compose or CI service)
./scripts/ci/backend-test.sh
```

Or run pytest directly from `backend/`:

```bash
cd backend
uv sync --group dev

# Domain / unit (static + import smoke — no Postgres required)
uv run pytest tests/domain -q   # -q = quiet (dots instead of each test name)

# Integration + PROC (needs Docker: testcontainers spins up Postgres 18.4)
uv run pytest tests/integration -q

# Everything under tests/
uv run pytest -q

# With coverage
uv run pytest tests/domain -q --cov=pricecomp --cov-report=term-missing
uv run pytest tests/integration -q --cov=pricecomp --cov-append --cov-report=term-missing
```

Pytest **markers** are labels on tests (`@pytest.mark.integration`, `@pytest.mark.proc`) so you can select subsets:

```bash
uv run pytest -m integration -q
uv run pytest -m proc -q
uv run pytest -m "not proc" -q
```

`integration` = needs Postgres. `proc` = spawns a real `pricecomp <role>` subprocess.

## Lint & typecheck

Config is in `pyproject.toml` (`[tool.ruff]`, `[tool.pyright]`). Prefer the portable script from repo root:

```bash
./scripts/ci/backend-lint.sh
```

Or run the tools directly from `backend/`:

```bash
cd backend
uv sync --group dev

uv run ruff format .          # rewrite formatting
uv run ruff format --check .  # CI-style: fail if rewrite needed
uv run ruff check .           # lint
uv run ruff check --fix .     # lint + apply safe autofixes
uv run pyright                # static types
```

### Pre-commit

Hooks live in the repo-root [`.pre-commit-config.yaml`](../.pre-commit-config.yaml) (Ruff format, Ruff check, Pyright). They call `uv run --directory backend …`, so sync the backend venv first.

```bash
# one-time (repo root)
uv run --directory backend pre-commit install

# run all hooks on the whole tree
uv run --directory backend pre-commit run --all-files
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
