#!/usr/bin/env bash
set -euo pipefail

# scalpel_clean.sh
# Removes Python bytecode caches produced by running tools locally.
# Safe to run repeatedly.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[scalpel-clean] root: $ROOT"

# Remove __pycache__ directories
find "$ROOT" -type d -name "__pycache__" -prune -exec rm -rf {} + 2>/dev/null || true

# Remove loose bytecode
find "$ROOT" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete 2>/dev/null || true

echo "[scalpel-clean] OK"
