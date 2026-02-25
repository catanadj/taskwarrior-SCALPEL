#!/usr/bin/env bash
set -euo pipefail

# One-command CI gate. Runs in UTC for deterministic output.

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

exec python3 -m scalpel.tools.ci "$@"
