#!/usr/bin/env bash
# Portable backend lint/typecheck entrypoint. Prefer this over ad-hoc commands
# so local runs and CI stay in sync. Config lives in backend/pyproject.toml
# (see docs/specs/code_style_python.md). jscpd config: repo-root .jscpd.json.

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="${ROOT}/backend"

UV_VERSION="${UV_VERSION:-0.12.1}"
PYTHON_VERSION="${PYTHON_VERSION:-3.14.6}"
JSCPD_VERSION="${JSCPD_VERSION:-4.0.5}"

cd "${BACKEND}"

if ! command -v uv >/dev/null 2>&1; then
  pip install "uv==${UV_VERSION}"
fi

uv python install "${PYTHON_VERSION}"
uv sync --group dev

echo "==> ruff format (check)"
uv run ruff format --check .

echo "==> ruff check"
uv run ruff check .

echo "==> pyright"
uv run pyright

echo "==> jscpd (duplication)"
if ! command -v npx >/dev/null 2>&1; then
  echo "npx not found — install Node.js to run jscpd" >&2
  exit 1
fi
cd "${ROOT}"
npx --yes "jscpd@${JSCPD_VERSION}" backend/src --config .jscpd.json

echo "backend lint OK"
