#!/usr/bin/env bash
set -euo pipefail

: "${SCALPEL_SKIP_DOCTOR:=0}"
: "${SCALPEL_SKIP_SMOKE:=0}"



export SCALPEL_SKIP_DOCTOR SCALPEL_SKIP_SMOKE

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

export PYTHONDONTWRITEBYTECODE="1"
export PYTHONPATH="${ROOT}${PYTHONPATH+:$PYTHONPATH}"

"$PY" -c 'import sys; from scalpel.tools.check import main; sys.exit(main())' "$@"
