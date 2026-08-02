#!/usr/bin/env bash
# Portable backend lint/typecheck entrypoint. Prefer this over ad-hoc commands
# so local runs and CI stay in sync. Config lives in backend/pyproject.toml
# (see docs/specs/code_style_python.md).

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
BACKEND="${ROOT}/backend"

UV_VERSION="${UV_VERSION:-0.12.1}"
PYTHON_VERSION="${PYTHON_VERSION:-3.14.6}"

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

echo "backend lint OK"
