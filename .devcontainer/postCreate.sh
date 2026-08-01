#!/usr/bin/env bash
# Modeled on tildou-track/.devcontainer/postCreate.sh — bootstrap tooling after the
# workspace is mounted so branch/lockfile changes apply without rebuilding the image.

set -euo pipefail

# Ubuntu ships fd as `fdfind`; create the standard `fd` alias for tooling/agents.
if ! command -v fd >/dev/null 2>&1 && command -v fdfind >/dev/null 2>&1; then
  if command -v sudo >/dev/null 2>&1; then
    sudo ln -sf "$(command -v fdfind)" /usr/local/bin/fd
  fi
fi

# Install the Claude CLI for in-container agent workflows (optional; skip if blocked).
if ! command -v claude >/dev/null 2>&1; then
  curl -fsSL https://claude.ai/install.sh | bash || true
fi

# Host ~/.claude is bind-mounted via devcontainer.json mounts (auth, settings, sessions).
if [ -d "${CLAUDE_CONFIG_DIR:-/root/.claude}" ]; then
  echo "Claude config synced from host: ${CLAUDE_CONFIG_DIR:-/root/.claude}"
fi

cd /workspaces/pricecomp/backend
uv sync

# One-shot bootstrap when postgres is already healthy (idempotent).
if [ -n "${MIGRATE_DATABASE_URL:-}" ]; then
  uv run pricecomp migrate || true
fi
