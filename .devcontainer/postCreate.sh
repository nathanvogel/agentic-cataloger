#!/usr/bin/env bash

set -euo pipefail

echo "postCreate: bootstrapping devcontainer..."

# Ubuntu ships fd as `fdfind`; create the standard `fd` alias for tooling/agents.
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
  echo "postCreate: linking fdfind -> fd..."
  if command -v sudo >/dev/null 2>&1; then
    sudo ln -sf "$(command -v fdfind)" /usr/local/bin/fd
  fi
fi

# Claude CLI is baked into the dev image (backend/Dockerfile dev stage).
# Auth + user settings persist in the named volume at CLAUDE_CONFIG_DIR (see devcontainer.json).
CLAUDE_DIR="${CLAUDE_CONFIG_DIR:-/root/.claude}"
if [ -f "${CLAUDE_DIR}/.credentials.json" ]; then
  echo "postCreate: Claude config volume present at ${CLAUDE_DIR}"
else
  echo "postCreate: run 'claude' once in the container to sign in (auth persists across rebuilds)"
fi

# RTK (https://github.com/rtk-ai/rtk) is baked into the dev image; hooks land in the Claude volume.
if command -v rtk >/dev/null 2>&1; then
  echo "postCreate: configuring rtk hooks for Claude Code..."
  rtk init -g --auto-patch

  # Cursor connects after postCreate, so ~/.cursor may not exist yet. RTK v0.44.2
  # writes hooks.json via atomic temp files and fails without the parent dir.
  echo "postCreate: configuring rtk hooks for Cursor..."
  mkdir -p "${HOME}/.cursor"
  if ! rtk init -g --agent cursor; then
    echo "postCreate: rtk cursor hook setup failed — retry after opening Cursor: rtk init -g --agent cursor" >&2
  fi
else
  echo "postCreate: rtk not found — rebuild the devcontainer image"
fi

# Image is built with `uv sync --frozen --no-dev`; dev tools (pre-commit, ruff, …) need the dev group.
BACKEND_DIR="/workspaces/agentic-cataloger/backend"
VENV_DIR="${BACKEND_DIR}/.venv"
if [ -d "${VENV_DIR}" ]; then
  # Console scripts bake the venv python path at install time; a bind-mounted .venv
  # from a renamed/moved workspace keeps dead shebangs (e.g. /workspaces/pricecomp/...).
  SAMPLE_SCRIPT="${VENV_DIR}/bin/pre-commit"
  if [ -f "${SAMPLE_SCRIPT}" ]; then
    INTERPRETER="$(head -1 "${SAMPLE_SCRIPT}" | sed 's/^#!//; s/ .*//')"
    if [ ! -x "${INTERPRETER}" ]; then
      echo "postCreate: removing stale backend .venv (missing interpreter: ${INTERPRETER})..."
      rm -rf "${VENV_DIR}"
    fi
  fi
fi
echo "postCreate: syncing Python deps (uv sync --group dev)..."
cd "${BACKEND_DIR}"
uv sync --group dev
# Install git hooks (Ruff + Pyright). Config is at repo root — see .pre-commit-config.yaml.
echo "postCreate: installing pre-commit hooks..."
cd /workspaces/agentic-cataloger
uv run --directory backend pre-commit install

# One-shot bootstrap when postgres is already healthy.
# Migrate-only env vars — never injected into api/worker (GATE-02).
echo "postCreate: checking postgres for migrations..."
if docker compose ps --status running postgres 2>/dev/null | grep -q postgres; then
  echo "postCreate: running database migrations..."
  export MIGRATE_DATABASE_URL="postgresql://postgres:postgres@postgres:5432/agentic_cataloger_app"
  export PHOENIX_DATABASE_URL="postgresql://agentic_cataloger_phoenix:agentic_cataloger_phoenix_dev@postgres:5432/agentic_cataloger_phoenix"
  export PHOENIX_HOST=phoenix
  export PHOENIX_PORT=6006
  if ! uv run agentic-cataloger migrate; then
    echo "migrate failed — if auth errors mention missing roles, reset the postgres volume:" >&2
    echo "  docker compose down && docker volume rm agentic_cataloger_postgres18_data" >&2
    exit 1
  fi
else
  echo "postCreate: postgres not running yet — skipping migrations"
fi

echo "postCreate: done."
