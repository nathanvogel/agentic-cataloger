#!/usr/bin/env bash
# Scan git history for leaked secrets. Fails closed on findings.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

GITLEAKS_VERSION="${GITLEAKS_VERSION:-8.30.1}"
GITLEAKS_BIN="${GITLEAKS_BIN:-}"

if [[ -z "$GITLEAKS_BIN" ]]; then
  if command -v gitleaks >/dev/null 2>&1; then
    GITLEAKS_BIN="$(command -v gitleaks)"
  else
  case "$(uname -m)" in
    x86_64|amd64) GITLEAKS_ARCH="x64" ;;
    aarch64|arm64) GITLEAKS_ARCH="arm64" ;;
    *)
      echo "Unsupported architecture for bundled gitleaks: $(uname -m)" >&2
      exit 1
      ;;
  esac
  cache_dir="${XDG_CACHE_HOME:-$HOME/.cache}/gitleaks"
  GITLEAKS_BIN="${cache_dir}/gitleaks_${GITLEAKS_VERSION}"
  if [[ ! -x "$GITLEAKS_BIN" ]]; then
    mkdir -p "$cache_dir"
    tmp="$(mktemp -d)"
    trap 'rm -rf "$tmp"' EXIT
    url="https://github.com/gitleaks/gitleaks/releases/download/v${GITLEAKS_VERSION}/gitleaks_${GITLEAKS_VERSION}_linux_${GITLEAKS_ARCH}.tar.gz"
    echo "Downloading gitleaks v${GITLEAKS_VERSION} (${GITLEAKS_ARCH})..."
    curl -sSfL "$url" -o "${tmp}/gitleaks.tar.gz"
    tar -xzf "${tmp}/gitleaks.tar.gz" -C "$tmp" gitleaks
    install -m 755 "${tmp}/gitleaks" "$GITLEAKS_BIN"
  fi
  fi
fi

"$GITLEAKS_BIN" version
"$GITLEAKS_BIN" detect \
  --source "$ROOT" \
  --config "$ROOT/.gitleaks.toml" \
  --verbose \
  --no-banner
