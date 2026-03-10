#!/usr/bin/env bash
set -euo pipefail

# scalpel_ci_hygiene.sh
# Run doctor against a tracked-file snapshot in a temp workspace so CI hygiene
# results are independent of local/untracked artifact churn.

die() { echo "[scalpel-ci-hygiene] ERROR: $*" >&2; exit 2; }

ROOT="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1
  pwd
)"

command -v git >/dev/null 2>&1 || die "git is required"
command -v tar >/dev/null 2>&1 || die "tar is required"
command -v python3 >/dev/null 2>&1 || die "python3 is required"
[[ -d "$ROOT/.git" ]] || die "expected git checkout at $ROOT"

SNAP_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/scalpel-hygiene.XXXXXX")"
SNAP_REPO="$SNAP_ROOT/repo"

cleanup() {
  rm -rf "$SNAP_ROOT"
}
trap cleanup EXIT

mkdir -p "$SNAP_REPO"
git -C "$ROOT" archive --format=tar HEAD | tar -xf - -C "$SNAP_REPO"

export PYTHONPATH="$SNAP_REPO"
export TZ=UTC
export SCALPEL_TZ=UTC
export SCALPEL_DISPLAY_TZ=local

echo "[scalpel-ci-hygiene] snapshot: $SNAP_REPO"
exec python3 -m scalpel.tools.doctor --root "$SNAP_REPO" --strict "$@"
