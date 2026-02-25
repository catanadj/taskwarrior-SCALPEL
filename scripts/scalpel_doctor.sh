#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

export PYTHONDONTWRITEBYTECODE="1"
export PYTHONPATH="${ROOT}${PYTHONPATH+:$PYTHONPATH}"

"$PY" -c 'import sys; from scalpel.tools.doctor import main; sys.exit(main())' "$@"
