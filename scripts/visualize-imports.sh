#!/usr/bin/env bash
# Render a package-level import graph for backend/src/agentic_cataloger.
# Requires graphviz (`dot`) — installed in the devcontainer image (backend/Dockerfile dev stage).
#
# Usage (from repo root):
#   ./scripts/visualize-imports.sh
#   DEPTH=3 ./scripts/visualize-imports.sh
#   OUT=tmp/pipeline.svg DEPTH=3 ./scripts/visualize-imports.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="${ROOT}/backend"
OUT="${OUT:-${BACKEND}/package-dependency-map.svg}"
DEPTH="${DEPTH:-2}"
PYDEPS_VERSION="${PYDEPS_VERSION:-3.0.7}"

if ! command -v dot >/dev/null 2>&1; then
  echo "graphviz (dot) not found" >&2
  exit 1
fi

mkdir -p "$(dirname "${OUT}")"
cd "${BACKEND}"

echo "==> pydeps (max-module-depth=${DEPTH}) -> ${OUT}"
uv tool run --from "pydeps==${PYDEPS_VERSION}" pydeps src/agentic_cataloger \
  --max-module-depth "${DEPTH}" \
  --cluster \
  --rmprefix agentic_cataloger. \
  --noshow \
  -T svg \
  -o "${OUT}"

echo "import graph written to ${OUT}"
