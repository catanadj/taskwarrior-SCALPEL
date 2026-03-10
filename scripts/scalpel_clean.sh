#!/usr/bin/env bash
set -euo pipefail

# scalpel_clean.sh
# Removes generated local artifacts produced by running tools locally.
# Safe to run repeatedly.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[scalpel-clean] root: $ROOT"

# Remove __pycache__ directories while leaving .git/.venv alone.
find "$ROOT" \
  \( -path "$ROOT/.git" -o -path "$ROOT/.venv" \) -prune -o \
  -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true

# Remove loose bytecode while leaving .git/.venv alone.
find "$ROOT" \
  \( -path "$ROOT/.git" -o -path "$ROOT/.venv" \) -prune -o \
  -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

# Remove common tool caches
rm -rf "$ROOT/.mypy_cache" "$ROOT/.pytest_cache" "$ROOT/.ruff_cache" 2>/dev/null || true

# Remove generated packaging artifacts
find "$ROOT" -maxdepth 1 -type d -name "*.egg-info" -prune -exec rm -rf {} + 2>/dev/null || true
rm -rf "$ROOT/dist" 2>/dev/null || true

# Remove ship-safe generated outputs
rm -rf "$ROOT/.ship-safe" "$ROOT/ship-safe-report.html" 2>/dev/null || true

echo "[scalpel-clean] OK"
