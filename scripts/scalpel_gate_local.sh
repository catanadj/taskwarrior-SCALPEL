#!/usr/bin/env bash
set -euo pipefail

# Local gate for SCALPEL.
#
# Default: run the one-command CI gate (UTC) which covers contracts via the unit suite.
#
# Bypass options:
#   git push --no-verify
#   SCALPEL_SKIP_PREPUSH=1 git push
#
# Fast mode (skip fixtures and doctor; run tests only):
#   SCALPEL_PREPUSH_FAST=1 git push

if [[ "${SCALPEL_SKIP_PREPUSH:-0}" == "1" ]]; then
  exit 0
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1 && pwd)"
cd "$ROOT"

if [[ "${SCALPEL_PREPUSH_FAST:-0}" == "1" ]]; then
  echo "[gate] FAST mode: tests only (skipping doctor, fixtures, lint)"
  ./scripts/scalpel_ci.sh --skip-doctor --skip-fixtures --skip-lint
  exit 0
fi

./scripts/scalpel_ci.sh
