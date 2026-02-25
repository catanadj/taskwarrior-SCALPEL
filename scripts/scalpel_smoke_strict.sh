#!/usr/bin/env bash
set -euo pipefail

: "${SCALPEL_SKIP_DOCTOR:=0}"


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OUT="${1:-build/scalpel_smoke.html}"
shift || true

mkdir -p "$(dirname "$OUT")"

# Delegate to the normal smoke script with --strict flag (and forward remaining args)
"$SCRIPT_DIR/scalpel_smoke.sh" "$OUT" --strict "$@"
