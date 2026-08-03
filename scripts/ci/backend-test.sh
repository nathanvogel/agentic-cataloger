#!/usr/bin/env bash
# Portable backend test entrypoint. GitHub Actions (or any runner) should only
# provision the environment, then invoke this script — keep platform YAML thin.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="${ROOT}/backend"
ROLES_SQL="${ROOT}/docker/postgres/init/01-roles.sql"

UV_VERSION="${UV_VERSION:-0.12.1}"
PYTHON_VERSION="${PYTHON_VERSION:-3.14.6}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
export PGPASSWORD

# Host machine / GHA: localhost:3021. Compose network (devcontainer): postgres:5432.
if [[ -z "${PGHOST:-}" ]]; then
  if getent hosts postgres >/dev/null 2>&1; then
    PGHOST=postgres
    PGPORT="${PGPORT:-5432}"
  else
    PGHOST=localhost
    PGPORT="${PGPORT:-3021}"
  fi
else
  PGPORT="${PGPORT:-3021}"
fi

MIGRATE_DATABASE_URL="${MIGRATE_DATABASE_URL:-postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/pricecomp_app}"
DATABASE_URL="${DATABASE_URL:-postgresql://pricecomp_app:pricecomp_app_dev@${PGHOST}:${PGPORT}/pricecomp_app}"
export MIGRATE_DATABASE_URL DATABASE_URL

cd "${BACKEND}"

if ! command -v uv >/dev/null 2>&1; then
  pip install "uv==${UV_VERSION}"
fi

if ! command -v psql >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo apt-get update -qq
    sudo apt-get install -y --no-install-recommends postgresql-client
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq
    apt-get install -y --no-install-recommends postgresql-client
  else
    echo "psql not found — install postgresql-client" >&2
    exit 1
  fi
fi

uv python install "${PYTHON_VERSION}"
uv sync

# Compose volumes already ran init SQL once; CI fresh Postgres still needs it.
if psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -d postgres -tAc \
  "SELECT 1 FROM pg_roles WHERE rolname = 'pricecomp_app'" | grep -q 1; then
  echo "GATE-02 roles already present — skipping ${ROLES_SQL}"
else
  psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -f "${ROLES_SQL}"
fi

uv run pytest tests/domain \
  --cov=pricecomp \
  --cov-report=term-missing \
  --cov-report=xml:coverage-unit.xml

uv run pricecomp migrate
uv run pricecomp migrate

uv run pytest tests/integration \
  --cov=pricecomp \
  --cov-append \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml
