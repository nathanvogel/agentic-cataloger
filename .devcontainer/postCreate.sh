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

# Install the Claude CLI for in-container agent workflows (optional; skip if blocked).
if ! command -v claude >/dev/null 2>&1; then
  echo "postCreate: installing Claude CLI (may take a moment)..."
  curl -fsSL https://claude.ai/install.sh | bash || true
else
  echo "postCreate: Claude CLI already installed"
fi

# Host ~/.claude is bind-mounted via devcontainer.json mounts (auth, settings, sessions).
if [ -d "${CLAUDE_CONFIG_DIR:-/root/.claude}" ]; then
  echo "postCreate: Claude config synced from host: ${CLAUDE_CONFIG_DIR:-/root/.claude}"
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
