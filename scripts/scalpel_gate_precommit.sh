#!/usr/bin/env bash
set -euo pipefail

# Pre-commit gate for SCALPEL (fast safety net).
#
# Bypass:
#   git commit --no-verify
#   SCALPEL_SKIP_PRECOMMIT=1 git commit
#
# Optional ultra-fast mode (skips contracts):
#   SCALPEL_PRECOMMIT_FAST=1 git commit

ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1
  pwd
)"
cd "$ROOT"

if [[ "${SCALPEL_PRECOMMIT_FAST:-0}" == "1" ]]; then
  echo "[precommit] FAST mode: python compile check..."
  # Compile all python files that are tracked (best-effort, fast)
  if command -v git >/dev/null 2>&1; then
    git ls-files '*.py' | xargs -r python3 -m py_compile
  else
    python3 -m py_compile $(find . -name '*.py' -type f)
  fi
  exit 0
fi

echo "[precommit] contracts..."
./scripts/scalpel_test_contract.sh
