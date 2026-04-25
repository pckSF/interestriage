#!/usr/bin/env bash
set -euo pipefail

cd /workspace

if [ -f package.json ]; then
  npm install
fi

if [ -f pyproject.toml ]; then
  if ! command -v uv >/dev/null 2>&1; then
    python3 -m pip install --user --break-system-packages uv
  fi

  "$HOME/.local/bin/uv" sync --extra dev
fi
