#!/usr/bin/env bash
set -euo pipefail

: "${SCALPEL_SKIP_DOCTOR:=0}"


SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONDONTWRITEBYTECODE="1"
export PYTHONPATH="${REPO_ROOT}"

OUT="${1:-build/scalpel_smoke.html}"
shift || true

mkdir -p "$(dirname "${OUT}")"

PY="${PYTHON:-python3}"
echo "[scalpel] smoke html: $OUT"
if [[ -n "${SCALPEL_SMOKE_OUT_JSON:-}" ]]; then
  "$PY" "${REPO_ROOT}/scalpel/tools/smoke_build.py" --out "$OUT" "$@" --out-json "$SCALPEL_SMOKE_OUT_JSON"
else
  "$PY" "${REPO_ROOT}/scalpel/tools/smoke_build.py" --out "$OUT" "$@"
fi
