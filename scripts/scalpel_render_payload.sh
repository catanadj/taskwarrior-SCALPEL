#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
PY="${PYTHON:-python3}"

# Usage:
#   ./scripts/scalpel_render_payload.sh --in payload.json --out page.html [--strict] [--pretty] [--no-validate]
exec "$PY" -m scalpel.tools.render_payload "$@"
