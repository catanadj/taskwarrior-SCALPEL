#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

export PYTHONDONTWRITEBYTECODE="1"
export PYTHONPATH="${ROOT}${PYTHONPATH+:$PYTHONPATH}"

cd "$ROOT"
"$PY" -m unittest discover -s tests -p "test_*.py" -v
