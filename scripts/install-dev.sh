#!/usr/bin/env bash
set -euo pipefail

# cd to repo root
SCRIPT_PATH="${BASH_SOURCE:-$0}"
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
cd "$SCRIPT_DIR/.."

# Make uv install into the current interpreter (conda/venv)
export UV_PYTHON="$(python -c 'import sys; print(sys.executable)')"

OS="$(uname -s || echo unknown)"

case "$OS" in
  Linux*)
    # Linux needs explicit CPU wheels and the CPU index
    uv pip install \
      torch torchvision \
      --index-url https://download.pytorch.org/whl/cpu
    ;;

  Darwin*)
    # macOS PyPI wheels are CPU-only by default
    ;;

  MINGW*|MSYS*|CYGWIN*)
    # Windows (Git Bash/MSYS). PyPI wheels are CPU-only by default.
    ;;

  *)
    echo "Unsupported OS: $OS" >&2
    exit 1
    ;;
esac

pip install ".[dev]"

# Install frontend dependencies
if ! command -v npm >/dev/null 2>&1; then
    echo "Warning: npm not found – skipping frontend dependency installation." >&2
    echo "Install Node.js/npm to run the research frontend." >&2
elif [ -d "research/frontend" ] && [ -f "research/frontend/package.json" ]; then
    echo "Installing frontend dependencies …"
    (cd research/frontend && { if [ -f package-lock.json ]; then npm ci --no-audit --no-fund; else npm install --no-audit --no-fund; fi; })
else
    echo "Warning: research/frontend missing or no package.json – skipping frontend install." >&2
fi
