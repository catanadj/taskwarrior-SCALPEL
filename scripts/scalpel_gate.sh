#!/usr/bin/env bash
set -euo pipefail

# scalpel_gate.sh
# High-level local gate. Intended for local enforcement (pre-push) and manual use.
#
# Default behavior:
#   - deterministic, UTC-run CI gate (doctor + compileall + tests + fixtures)
#   - optional ruff lint if installed
#
# Bypass:
#   SCALPEL_SKIP_GATE=1 ./scripts/scalpel_gate.sh
#   SCALPEL_SKIP_GATE=1 git push

if [[ "${SCALPEL_SKIP_GATE:-0}" == "1" ]]; then
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

echo "[gate] === scalpel-ci (UTC) ==="
./scripts/scalpel_ci.sh "$@"

echo
echo "[gate] OK"
