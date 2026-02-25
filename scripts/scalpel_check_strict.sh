#!/usr/bin/env bash
set -euo pipefail

: "${SCALPEL_SKIP_DOCTOR:=0}"
: "${SCALPEL_SKIP_SMOKE:=0}"



export SCALPEL_SKIP_DOCTOR SCALPEL_SKIP_SMOKE

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OUT="build/scalpel_smoke.html"

# Parse --out <path> (ignore other args; this runner is intentionally narrow)
while [[ $# -gt 0 ]]; do
  case "$1" in
    --out)
      OUT="${2:-$OUT}"
      shift 2
      ;;
    --skip-doctor) SCALPEL_SKIP_DOCTOR=1; shift ;;
    --skip-smoke)  SCALPEL_SKIP_SMOKE=1;  shift ;;
    *)
      shift
      ;;
  esac
done

if [[ "${SCALPEL_SKIP_DOCTOR:-0}" != "1" ]]; then
  "$SCRIPT_DIR/scalpel_doctor.sh"
fi
if [[ "${SCALPEL_SKIP_SMOKE:-0}" != "1" ]]; then
  "$SCRIPT_DIR/scalpel_smoke_strict.sh" "$OUT"
fi

# Run the normal check tool against the produced HTML
"$SCRIPT_DIR/scalpel_check.sh" --out "$OUT" --skip-doctor --skip-smoke

echo "[scalpel-check-strict] OK: $OUT"


