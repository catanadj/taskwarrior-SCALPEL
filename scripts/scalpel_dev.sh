#!/usr/bin/env bash
set -euo pipefail

# scalpel_dev.sh - single developer entrypoint for SCALPEL
#
# Goals:
#  - Standardize local workflows (contracts, ci-lite, smoke+validate).
#  - Provide --dry-run for deterministic contract assertions.
#
# Usage:
#   ./scripts/scalpel_dev.sh <command> [options] [-- <pass-through args>]
#
# Examples:
#   ./scripts/scalpel_dev.sh test
#   ./scripts/scalpel_dev.sh ci --out build/scalpel_smoke.html
#   ./scripts/scalpel_dev.sh smoke --out build/smoke.html --json build/payload.json -- --days 14 --pretty
#   ./scripts/scalpel_dev.sh validate --out build/smoke.html --json build/payload.json
#
# Environment:
#   PYTHON=python3                 (optional)
#   SCALPEL_DEV_OUT=...              (default output html)
#   SCALPEL_DEV_JSON=...             (default payload json)
#

usage() {
  cat <<'EOF'
scalpel_dev.sh - developer entrypoint for SCALPEL

Commands:
  test                 Run contract suite (fast, deterministic)
  ci                   Run CI-lite runner (clean -> doctor -> smoke(strict) -> validate(payload) -> check)
  smoke                Run smoke(strict) and validate(payload) (writes HTML + JSON)
  validate             Validate payload JSON and (optionally) cross-check against HTML
  clean                Run clean tool
  doctor               Run doctor tool
  check                Run check(strict) wrapper

Global options:
  --dry-run             Print the underlying commands that would run, then exit 0
  -h, --help            Show this help

Command options:
  smoke/validate:
    --out PATH          Output HTML path (default: $SCALPEL_DEV_OUT or build/scalpel_dev_smoke.html)
    --json PATH         Output JSON path (default: $SCALPEL_DEV_JSON or build/scalpel_dev_payload.json)

Pass-through:
  Any args after `--` are forwarded to the smoke(strict) build step.

Notes:
  - `ci` delegates to ./scripts/scalpel_ci_lite.sh (preferred).
  - `smoke` uses SCALPEL_SMOKE_OUT_JSON to request JSON sidecar output.
EOF
}

die() { echo "[scalpel-dev] ERROR: $*" >&2; exit 2; }

repo_root="$(
  cd "$(dirname "${BASH_SOURCE[0]}")/.." >/dev/null 2>&1
  pwd
)"
cd "$repo_root"

DRY_RUN=0
if [[ "${1:-}" == "-h" || "${1:-}" == "--help" || -z "${1:-}" ]]; then
  usage
  exit 0
fi

# Allow global flag before the command.
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=1
  shift
fi

cmd="${1:-}"
shift || true

# Common defaults (used by smoke/validate)
DEFAULT_OUT="${SCALPEL_DEV_OUT:-build/scalpel_dev_smoke.html}"
DEFAULT_JSON="${SCALPEL_DEV_JSON:-build/scalpel_dev_payload.json}"

_print_cmd() {
  # prints a command array in a stable, shell-ish form
  local -a a=("$@")
  printf "%s" "${a[0]}"
  local i
  for ((i=1; i<${#a[@]}; i++)); do
    printf " %q" "${a[$i]}"
  done
  printf "
"
}

_run() {
  local label="$1"; shift
  local -a a=("$@")
  if [[ "$DRY_RUN" -eq 1 ]]; then
    echo "[scalpel-dev] dry-run: $label"
    _print_cmd "${a[@]}"
    return 0
  fi
  "${a[@]}"
}

# Parse smoke/validate shared options.
parse_out_json_and_passthru() {
  OUT="$DEFAULT_OUT"
  JSON="$DEFAULT_JSON"
  PASSTHRU=()

  while [[ $# -gt 0 ]]; do
    case "$1" in
      --out)
        [[ $# -ge 2 ]] || die "--out requires a value"
        OUT="$2"
        shift 2
        ;;
      --json)
        [[ $# -ge 2 ]] || die "--json requires a value"
        JSON="$2"
        shift 2
        ;;
      --)
        shift
        PASSTHRU+=("$@")
        break
        ;;
      -h|--help)
        usage
        exit 0
        ;;
      *)
        die "Unknown argument for this command: $1"
        ;;
    esac
  done
}

case "$cmd" in
  test)
    if [[ -x "./scripts/scalpel_test_contract.sh" ]]; then
      _run "contracts" ./scripts/scalpel_test_contract.sh
    else
      PY="${PYTHON:-python3}"
      _run "contracts" "$PY" -m unittest discover -s tests -p "test_contract_*.py"
    fi
    ;;

  ci)
    [[ -x "./scripts/scalpel_ci_lite.sh" ]] || die "Missing ./scripts/scalpel_ci_lite.sh"
    _run "ci-lite" ./scripts/scalpel_ci_lite.sh "$@"
    ;;

  smoke)
    parse_out_json_and_passthru "$@"
    mkdir -p "$(dirname "$OUT")" "$(dirname "$JSON")"

    # Build smoke(strict) with JSON sidecar.
    if [[ -x "./scripts/scalpel_smoke_strict.sh" ]]; then
      _run "smoke(strict)" env SCALPEL_SKIP_DOCTOR=1 SCALPEL_SMOKE_OUT_JSON="$JSON" ./scripts/scalpel_smoke_strict.sh "$OUT" "${PASSTHRU[@]}"
    else
      PY="${PYTHON:-python3}"
      _run "smoke(strict)" "$PY" -m scalpel.tools.smoke_build --out "$OUT" --strict --out-json "$JSON" "${PASSTHRU[@]}"
    fi

    # Validate payload.
    if [[ -x "./scripts/scalpel_validate_payload.sh" ]]; then
      _run "validate(payload)" ./scripts/scalpel_validate_payload.sh --from-html "$OUT" --in "$JSON"
    else
      PY="${PYTHON:-python3}"
      _run "validate(payload)" "$PY" -m scalpel.tools.validate_payload --from-html "$OUT" --in "$JSON"
    fi
    ;;

  validate)
    parse_out_json_and_passthru "$@"
    [[ -f "$JSON" ]] || die "JSON not found: $JSON (use: smoke --json ...)"
    if [[ -x "./scripts/scalpel_validate_payload.sh" ]]; then
      if [[ -f "$OUT" ]]; then
        _run "validate(payload)" ./scripts/scalpel_validate_payload.sh --from-html "$OUT" --in "$JSON"
      else
        _run "validate(payload)" ./scripts/scalpel_validate_payload.sh --in "$JSON"
      fi
    else
      PY="${PYTHON:-python3}"
      if [[ -f "$OUT" ]]; then
        _run "validate(payload)" "$PY" -m scalpel.tools.validate_payload --from-html "$OUT" --in "$JSON"
      else
        _run "validate(payload)" "$PY" -m scalpel.tools.validate_payload --in "$JSON"
      fi
    fi
    ;;

  clean)
    if [[ -x "./scripts/scalpel_clean.sh" ]]; then
      _run "clean" ./scripts/scalpel_clean.sh
    elif command -v scalpel-clean >/dev/null 2>&1; then
      _run "clean" scalpel-clean
    else
      die "No clean tool found (expected ./scripts/scalpel_clean.sh or scalpel-clean on PATH)."
    fi
    ;;

  doctor)
    if [[ -x "./scripts/scalpel_doctor.sh" ]]; then
      _run "doctor" ./scripts/scalpel_doctor.sh
    elif command -v scalpel-doctor >/dev/null 2>&1; then
      _run "doctor" scalpel-doctor
    else
      die "No doctor tool found (expected ./scripts/scalpel_doctor.sh or scalpel-doctor on PATH)."
    fi
    ;;

  check)
    if [[ -x "./scripts/scalpel_check_strict.sh" ]]; then
      _run "check(strict)" ./scripts/scalpel_check_strict.sh "$@"
    elif command -v scalpel-check >/dev/null 2>&1; then
      _run "check" scalpel-check "$@"
    else
      die "No check tool found (expected ./scripts/scalpel_check_strict.sh or scalpel-check on PATH)."
    fi
    ;;

  -h|--help)
    usage
    exit 0
    ;;

  *)
    die "Unknown command: $cmd (use --help)"
    ;;
esac
