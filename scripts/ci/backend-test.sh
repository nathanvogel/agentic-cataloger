#!/usr/bin/env bash
# Portable backend test entrypoint. GitHub Actions (or any runner) should only
# provision the environment, then invoke this script — keep platform YAML thin.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="${ROOT}/backend"
ROLES_SQL="${ROOT}/docker/postgres/init/01-roles.sql"

UV_VERSION="${UV_VERSION:-0.12.1}"
PYTHON_VERSION="${PYTHON_VERSION:-3.14.6}"
PGHOST="${PGHOST:-localhost}"
PGPORT="${PGPORT:-3021}"
PGUSER="${PGUSER:-postgres}"
PGPASSWORD="${PGPASSWORD:-postgres}"
export PGPASSWORD

MIGRATE_DATABASE_URL="${MIGRATE_DATABASE_URL:-postgresql://${PGUSER}:${PGPASSWORD}@${PGHOST}:${PGPORT}/pricecomp_app}"
DATABASE_URL="${DATABASE_URL:-postgresql://pricecomp_app:pricecomp_app_dev@${PGHOST}:${PGPORT}/pricecomp_app}"
export MIGRATE_DATABASE_URL DATABASE_URL

cd "${BACKEND}"

if ! command -v uv >/dev/null 2>&1; then
  pip install "uv==${UV_VERSION}"
fi

uv python install "${PYTHON_VERSION}"
uv sync

psql -h "${PGHOST}" -p "${PGPORT}" -U "${PGUSER}" -f "${ROLES_SQL}"

uv run pytest tests/domain -q \
  --cov=pricecomp \
  --cov-report=term-missing \
  --cov-report=xml:coverage-unit.xml

uv run pricecomp migrate
uv run pricecomp migrate

uv run pytest tests/integration -q \
  --cov=pricecomp \
  --cov-append \
  --cov-report=term-missing \
  --cov-report=xml:coverage.xml

api_pid=""
cleanup() {
  if [[ -n "${api_pid}" ]] && kill -0 "${api_pid}" 2>/dev/null; then
    kill "${api_pid}" 2>/dev/null || true
    wait "${api_pid}" 2>/dev/null || true
  fi
}
trap cleanup EXIT

uv run pricecomp api &
api_pid=$!
sleep 3
curl -fsS http://127.0.0.1:3020/health
curl -fsS http://127.0.0.1:3020/ready
