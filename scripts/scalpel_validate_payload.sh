#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

export PYTHONDONTWRITEBYTECODE="1"
export PYTHONPATH="${REPO_ROOT}"

PY="${PYTHON:-python3}"
exec "$PY" -m scalpel.tools.validate_payload "$@"
