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

echo "postCreate: syncing Python deps (uv sync)..."
cd /workspaces/pricecomp/backend
uv sync
# Install git hooks (Ruff + Pyright). Safe to re-run; no-op if already linked.
echo "postCreate: installing pre-commit hooks..."
uv run pre-commit install

# Frontend deps — vendored Yarn 4 in .yarn/releases.
echo "postCreate: installing frontend deps (yarn)..."
cd /workspaces/pricecomp/frontend
export COREPACK_ENABLE_DOWNLOAD_PROMPT=0
node .yarn/releases/yarn-4.11.0.cjs install

# One-shot bootstrap when postgres is already healthy.
# Migrate-only env vars — never injected into api/worker (GATE-02).
echo "postCreate: checking postgres for migrations..."
if docker compose ps --status running postgres 2>/dev/null | grep -q postgres; then
  echo "postCreate: running database migrations..."
  export MIGRATE_DATABASE_URL="postgresql://postgres:postgres@postgres:5432/pricecomp_app"
  export PHOENIX_DATABASE_URL="postgresql://pricecomp_phoenix:pricecomp_phoenix_dev@postgres:5432/pricecomp_phoenix"
  export PHOENIX_HOST=phoenix
  export PHOENIX_PORT=6006
  if ! uv run pricecomp migrate; then
    echo "migrate failed — if auth errors mention missing roles, reset the postgres volume:" >&2
    echo "  docker compose down && docker volume rm pricecomp_postgres18_data" >&2
    exit 1
  fi
else
  echo "postCreate: postgres not running yet — skipping migrations"
fi

echo "postCreate: done."
